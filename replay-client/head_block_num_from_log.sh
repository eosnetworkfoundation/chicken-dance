#!/usr/bin/env bash

# grep patters to find head block number currently processed
# accounts for replay node sync and block log sync

NODEOS_DIR=${1:-/data/nodeos}

# blocks log
BLOCK_NUM_FROM_LOG=$(grep controller.cpp "${NODEOS_DIR}"/log/nodeos.log | \
    grep replay | grep "of" \
    | cut -d']' -f2 | cut -d' ' -f2 | tail -1)

# replay via peer
BLOCK_NUM_FROM_REPLAY=$(grep 'net_plugin.cpp:' "${NODEOS_DIR}"/log/nodeos.log | \
    grep recv_handshake | \
    cut -d']' -f3 | \
    cut -d',' -f4 | \
    sed 's/ [f]*head //' | tail -1)

# nothing from Block Log or Relay Log Num is Greater
if [ -z $BLOCK_NUM_FROM_LOG ] || [ ${BLOCK_NUM_FROM_REPLAY:--1} -gt $BLOCK_NUM_FROM_LOG ]; then
  echo "$BLOCK_NUM_FROM_REPLAY"
else
  echo "$BLOCK_NUM_FROM_LOG"
fi

# detect error
if [ -z $BLOCK_NUM_FROM_LOG ] && [ -z $BLOCK_NUM_FROM_REPLAY ]; then
  echo "NA-ERROR"
fi
