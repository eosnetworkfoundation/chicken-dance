#!/usr/bin/env bash

# grep patters to find head block number currently processed
# accounts for replay node sync and block log sync

NODEOS_DIR=${1:-/data/nodeos}

# leap v5  log
OLD_BLOCK_NUM_FROM_LOG=$(tail -500 "${NODEOS_DIR}"/log/nodeos.log | grep controller.cpp \
    | grep replay | grep "of" \
    | cut -d']' -f2 | cut -d' ' -f2 | tail -1)
# spring v1.1 log
NEW_BLOCK_NUM_FROM_LOG=$(tail -500 "${NODEOS_DIR}"/log/nodeos.log \
    | grep controller.cpp | grep "Received block" \
    | cut -d'#' -f2 | cut -d" " -f1 | tail -1)

# set to new format
if [ -n "$NEW_BLOCK_NUM_FROM_LOG" ] ; then
  BLOCK_NUM_FROM_LOG="$NEW_BLOCK_NUM_FROM_LOG"
else
  if [ -n "$OLD_BLOCK_NUM_FROM_LOG" ] ; then
    BLOCK_NUM_FROM_LOG="$OLD_BLOCK_NUM_FROM_LOG"
  fi
fi

# replay via peer
BLOCK_NUM_FROM_REPLAY=$(tail -500 "${NODEOS_DIR}"/log/nodeos.log | grep 'net_plugin.cpp:' | \
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