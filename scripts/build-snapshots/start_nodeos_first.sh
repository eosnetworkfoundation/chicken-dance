#!/usr/bin/env bash

cd /home/enf-replay/replay-test || exit

# install nodeos
/home/enf-replay/replay-test/replay-client/install-nodeos.sh 1.0.1

# create directories
/home/enf-replay/replay-test/replay-client/create-nodeos-dir-struct.sh /home/enf-replay/replay-test/config/

# setup path
PATH=/home/enf-replay/nodeos/usr/bin/:${PATH}
export PATH
CONFIG_DIR=/home/enf-replay/replay-test/config
NODEOS_DIR=/data/nodeos

# get snapshots and end blocks by running full_run.py --instructions --file NA
# Genesis END_NUM=0
#SNAP=NA; START_NUM=0; END_NUM=75999999
#SNAP=snapshot-2024-08-08-02-eos-v6-387721720.bin.zst ; START_NUM=387721720; END_NUM=900000000


# start with a snapshot and run in background
if [ $START_NUM == 0 ]; then
  aws s3 cp s3://chicken-dance/mainnet/mainnet-genesis.json /data/nodeos/genesis.json

  nohup nodeos \
    --genesis-json "${NODEOS_DIR}"/genesis.json \
    --data-dir "${NODEOS_DIR}"/data/ \
    --config "${CONFIG_DIR}"/sync-config.ini \
    --terminate-at-block ${END_NUM} > "${NODEOS_DIR}"/log/nodeos.log &
else
  aws s3 cp s3://chicken-dance/mainnet/snapshots/${SNAP} /data/nodeos/snapshot
  zstd -d /data/nodeos/snapshot/${SNAP}

  nohup nodeos --snapshot /data/nodeos/snapshot/${SNAP%.*} \
    --data-dir "${NODEOS_DIR}"/data/ \
    --config "${CONFIG_DIR}"/sync-config.ini \
    --terminate-at-block ${END_NUM} > "${NODEOS_DIR}"/log/nodeos.log &
fi
