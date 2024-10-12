#!/usr/bin/env bash

# Pulls block log file from cloud storage or saves block log to cloud storage
# Params
#
# NODEOS_DIR - local host top level directory
# START_BLOCK_NUM - starting block to lable blocks log
# END_BLOCK_NUM - ending block to lable blocks log
# SNAPSHOT_PATH - used to figure out cloud directory and bucket
#


NODEOS_DIR=${1:-/data/nodeos}
START_BLOCK_NUM=$2
END_BLOCK_NUM=$3
SNAPSHOT_PATH=${4:-s3://chicken-dance/default/snapshots/snapshot.bin.zst}
UTIL="spring-util"
# need to handle older versions of nodeos
if [[ "$(nodeos -v | grep -ic v[45])" == '1' ]]; then
  UTIL="leap-util"
fi

# validate params
if [ -z "$START_BLOCK_NUM" ] || [ -z "$END_BLOCK_NUM" ]; then
  echo "Must provider operation, start block num and end block num to manage_block_log.sh"
  exit 127
fi


# Figure out S3 Blocks log dir from provided snapshot path
# Remove the last directory using dirname
S3_DIR="$(dirname "$SNAPSHOT_PATH")"
# Strip off the file and last directory
S3_DIR="${S3_DIR%/*}"/blocks
# figure out s3 bucket
S3_BUCKET=$(echo "${S3_DIR}" | sed 's#s3://##' | cut -d'/' -f1)
# figure out s3 path
S3_PATH=$(echo "${S3_DIR}" | sed 's#s3://##' | cut -d'/' -f2-)
# figure out file name
if [ ${START_BLOCK_NUM} -lt 1 ]; then
  START_BLOCK_NUM=1
fi
# find the bound for blocks
# blocks logs increments of 2,000,000
STRIDE=2000000
LOWER_BOUND=$( echo "${START_BLOCK_NUM}/${STRIDE}*${STRIDE}" | bc)
UPPER_BOUND=$( echo "${END_BLOCK_NUM}/${STRIDE}*${STRIDE}" | bc)
if [ ${END_BLOCK_NUM} -gt ${UPPER_BOUND} ]; then
  UPPER_BOUND=$( echo "${UPPER_BOUND}+${STRIDE}" | bc)
fi
# construct two files because the start/end might cross a block log stride
LOWER_BOUND_END=$(echo "${LOWER_BOUND}+${STRIDE}" | bc)
UPPER_BOUND_START=$(echo "${UPPER_BOUND}-${STRIDE}" | bc)
let "BLOCK_START=LOWER_BOUND+1"
S3_BLOCKS_LOWER=blocks-${BLOCK_START}-${LOWER_BOUND_END}.log.zst
let "BLOCK_START=UPPER_BOUND_START+1"
S3_BLOCKS_UPPER=blocks-${BLOCK_START}-${UPPER_BOUND}.log.zst

# copy down files
# leap-util/spring-util merge-blocks running out of space, just copy one blocks log for now
#for S3_BLOCKS in $S3_BLOCKS_LOWER $S3_BLOCKS_UPPER
for S3_BLOCKS in $S3_BLOCKS_LOWER
do
  aws s3api head-object --bucket "$S3_BUCKET" --key "$S3_PATH"/"$S3_BLOCKS" > /dev/null 2>&1 || NOT_EXIST=true

  if [ $NOT_EXIST ]; then
    echo "${S3_DIR}/${S3_FILE} does not exist skipping blocks log restore step"
  else
    # skip if local file already exists
    if [ ! -s "$NODEOS_DIR"/data/blocks"${S3_FILE}"/"${S3_BLOCKS}" ]; then
      aws s3 cp "${S3_DIR}"/"$S3_FILE""$S3_BLOCKS" "$NODEOS_DIR"/data/blocks/ > /dev/null 2>&1
      aws s3 cp "${S3_DIR}"/"$S3_FILE""${S3_BLOCKS%%.*}.index.zst" "$NODEOS_DIR"/data/blocks/ > /dev/null 2>&1
      for f in "$NODEOS_DIR"/data/blocks/blocks-*.zst
      do
        zstd -d $f > /dev/null 2>&1
        if [ $? -eq 0 ]; then
          rm $f
        fi
      done
    fi
  fi
done

# now we have our files
CNT=$(ls -1 "$NODEOS_DIR"/data/blocks/blocks-*.log | wc -l)
# several blocks logs to merge
if [ $CNT -gt 1 ]; then
  [ ! -d "$NODEOS_DIR"/source-blocks/ ] && mkdir "$NODEOS_DIR"/source-blocks/
  # move blocks out of the way before merge
  mv "$NODEOS_DIR"/data/blocks/blocks-*.log "$NODEOS_DIR"/source-blocks/
  mv "$NODEOS_DIR"/data/blocks/blocks-*.index "$NODEOS_DIR"/source-blocks/
  $UTIL block-log merge-blocks \
      --blocks-dir "$NODEOS_DIR"/source-blocks/ \
      --output-dir "$NODEOS_DIR"/data/blocks/ > /dev/null 2>&1 || FAILED_MERGE=true
  if [ $FAILED_MERGE ]; then
    echo "Failed to merge blocks logs from ${NODEOS_DIR}/source-blocks/ into ${NODEOS_DIR}/data/blocks/"
    exit 127
  fi
# just one blocks log rename
else
  for f in "$NODEOS_DIR"/data/blocks/blocks-*.log
  do
    mv $f "$NODEOS_DIR"/data/blocks/blocks.log
    mv "${f%%.*}.index" "$NODEOS_DIR"/data/blocks/blocks.index
  done
fi

$UTIL block-log --blocks-dir "$NODEOS_DIR"/data/blocks/ smoke-test > /dev/null 2>&1 || FAILED_SMOKE_TEST=true
# try an obvious repair
if [ $FAILED_SMOKE_TEST ]; then
  echo "${UTIL} generating block.index"
  $UTIL block-log --blocks-dir "$NODEOS_DIR"/data/blocks/ make-index >> "$NODEOS_DIR"/log/"$UTIL".log 2>&1
  unset FAILED_SMOKE_TEST
  # retest
  $UTIL block-log --blocks-dir "$NODEOS_DIR"/data/blocks/ smoke-test > /dev/null 2>&1 || FAILED_SMOKE_TEST=true
  if [ $FAILED_SMOKE_TEST ]; then
    echo "Smoke test for Blocks log ${NODEOS_DIR}/data/blocks/ failed exiting"
    exit 127
  fi
fi
