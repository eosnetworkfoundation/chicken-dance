#!/usr/bin/env bash

# runs in the background and updates the status of the snapshot loading and sync run
# POSTS back to orchestration service updating status and last block processed

ORCH_IP=$1
ORCH_PORT=${2}
JOBID=$3
NODEOS_DIR=${4:-/data/nodeos}
REPLAY_CLIENT_DIR=${5:-/home/enf-replay/replay-test/replay-client}
STATUS="LOADING_SNAPSHOT"

loop_count=0
# clean up old integrity hash if it exists
if [ -f "$NODEOS_DIR"/log/start_integrity_hash.txt ]; then
  rm "$NODEOS_DIR"/log/start_integrity_hash.txt
fi

while [ $loop_count -lt 200 ]
do
  let "loop_count++"
  sleep 180
  # check for snapshot load complete
  if [ "$STATUS" == "LOADING_SNAPSHOT" ]; then
    # look for starting integrity hashes
    HASH=$("${REPLAY_CLIENT_DIR}"/get_integrity_hash_from_log.sh "started" "$NODEOS_DIR")
    HASH_SIZE=$(echo $HASH | wc -c)
    # update status
    if [ $HASH_SIZE -gt 63 ]; then
      STATUS="WORKING"
      python3 "${REPLAY_CLIENT_DIR}"/job_operations.py --host ${ORCH_IP} --port ${ORCH_PORT} --operation update-status --status "${STATUS}" --job-id ${JOBID}
      # write hash to file
      echo $HASH > "$NODEOS_DIR"/log/start_integrity_hash.txt
    fi
  else
    BLOCK_NUM=$("${REPLAY_CLIENT_DIR}"/head_block_num_from_log.sh "$NODEOS_DIR")
    python3 "${REPLAY_CLIENT_DIR}"/job_operations.py --host ${ORCH_IP} --port ${ORCH_PORT} --operation update-progress --block-processed "$BLOCK_NUM" --job-id ${JOBID}
  fi
done
