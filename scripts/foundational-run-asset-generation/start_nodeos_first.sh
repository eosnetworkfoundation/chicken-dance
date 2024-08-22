#!/usr/bin/env bash

cd /home/enf-replay/replay-test || exit

# install nodeos
/home/enf-replay/replay-test/replay-client/install-nodeos.sh 5.0.2

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
#SNAP=snapshot-2019-08-11-16-eos-v6-0073487941.bin.zst ; START_NUM=73999999; END_NUM=107999999
#SNAP=snapshot-2020-02-16-16-eos-v6-0105491080.bin.zst; START_NUM=105999999; END_NUM=120000000
#SNAP=snapshot-2020-05-10-16-eos-v6-0119970792.bin.zst; START_NUM=119999999; END_NUM=130000000
#SNAP=snapshot-2020-06-24-16-eos-v6-0127744602.bin.zst; START_NUM=127999999; END_NUM=140000000
#SNAP=snapshot-2020-08-19-16-eos-v6-0137418534.bin.zst; START_NUM=137999999; END_NUM=152000000
#SNAP=snapshot-2020-11-11-16-eos-v6-0151927809.bin.zst; START_NUM=151999999; END_NUM=164000000
# SNAP=snapshot-2021-01-17-16-eos-v6-0163499038.bin.zst ; START_NUM=163999999; END_NUM=194000000
# SNAP=snapshot-2021-07-11-16-eos-v6-0193719865.bin.zst ; START_NUM=193999999; END_NUM=272000000
# SNAP=snapshot-2022-10-05-16-eos-v6-0271620354.bin.zst ; START_NUM=271999999; END_NUM=344000000
SNAP=snapshot-2023-12-30-06-eos-v6-349448297.bin.zst; START_NUM=343900000; END_NUM=390280020

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
