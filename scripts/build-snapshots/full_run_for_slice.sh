#!/usr/bin/env bash

# install python lib
pip install tomli numpy
cd /home/enf-replay/replay-test || exit
PYTHONPATH=/home/enf-replay/replay-test/scripts/manifest
python3 /home/enf-replay/replay-test/scripts/build-snapshots/generate_full_run_data.py \
  --file /home/enf-replay/replay-test/meta-data/optimized_block_spacing.tsv > /home/enf-replay/optimized-blocks.csv

# setup path
PATH=/home/enf-replay/nodeos/usr/bin/:${PATH}
export PATH
NODEOS_DIR=/data/nodeos
SCRIPT_DIR=/home/enf-replay/replay-test/replay-client

do_snapshot() {
  provided_snap_block_num=$1
  curl http://127.0.0.1:8888/v1/producer/create_snapshot > /data/nodeos/snapshot/snap-out-${provided_snap_block_num}.json
  sleep 1
  SNAP_PATH=$(cat /data/nodeos/snapshot/snap-out-${provided_snap_block_num}.json | python3 "${SCRIPT_DIR}"/parse_json.py snapshot_name)
  VERSION=$(cat /data/nodeos/snapshot/snap-out-${provided_snap_block_num}.json | python3 "${SCRIPT_DIR}"/parse_json.py version)
  SNAP_HEAD_BLOCK=$(cat /data/nodeos/snapshot/snap-out-${provided_snap_block_num}.json | python3 "${SCRIPT_DIR}"/parse_json.py head_block_num)
  HEAD_BLOCK_TIME=$(cat /data/nodeos/snapshot/snap-out-${provided_snap_block_num}.json | python3 "${SCRIPT_DIR}"/parse_json.py head_block_time)
  DATE=${HEAD_BLOCK_TIME%T*}
  TIME=${HEAD_BLOCK_TIME#*T}
  HOUR=${TIME%%:*}
  DATE="${DATE}-${HOUR}"
  # rename to our format snapshot-2019-08-11-16-eos-v6-0073487941.bin.zst
  NEW_PATH="${SNAP_PATH%/*}/snapshot-${DATE}-eos-v${VERSION}-${SNAP_HEAD_BLOCK}.bin"
  mv "$SNAP_PATH" "$NEW_PATH"
  zstd "$NEW_PATH"
  if [ $? -eq 0 ]; then
    rm $NEW_PATH
  fi
}

# get snapshots and end blocks by running full_run.py --instructions --file NA
# Genesis END_NUM=0
#SNAP=NA; START_NUM=0; END_NUM=75999999
SNAP=snapshot-2024-08-08-02-eos-v6-387721720.bin.zst ; START_NUM=387721720; END_NUM=900000000

set -x

sleep 480
# first snapshot wait until nodeos is printing blocks
loop_count=0

while [ $loop_count -lt 200 ]
do
  let "loop_count++"
  sleep 30
  CURRENT_BLOCK_NUM=$("${SCRIPT_DIR}"/head_block_num_from_log.sh "$NODEOS_DIR")
  if [ "$CURRENT_BLOCK_NUM" != "NA-ERROR" ]; then
    do_snapshot $CURRENT_BLOCK_NUM
    # exit loop
    loop_count=99999
    break
  fi
done
set +x

# ok now we are syncing in background
# take snapshots at current interval
# first for loop filters out blocks relevant for this slice
# while loop interates checking logs for head_block
#    when head_block exceeds end of segment snapshot
for i in $(cat /home/enf-replay/optimized-blocks.csv)
do
  start_range=$(echo $i | cut -d',' -f1); end_range=$(echo $i | cut -d',' -f2);
  if [ $start_range -gt $START_NUM ] && [ $end_range -lt $END_NUM ]; then
      CURRENT_BLOCK_NUM=$("${SCRIPT_DIR}"/head_block_num_from_log.sh "$NODEOS_DIR")
      set -x
      while [ $CURRENT_BLOCK_NUM -lt $end_range ]
      do
        sleep 120
        CURRENT_BLOCK_NUM=$("${SCRIPT_DIR}"/head_block_num_from_log.sh "$NODEOS_DIR")
        # start snapshot early and don't get hung up if just short of end_range
        let CURRENT_BLOCK_NUM=CURRENT_BLOCK_NUM+500
      done
      set +x
      do_snapshot $end_range
  fi
done
