#!/usr/bin/env bash

# install python lib
pip install tomli

# install nodeos
replay-client/install-nodeos.sh 5.0.0-rc3

# create directories
replay-client/create-nodeos-dir-struct.sh ./config/

# setup path
PATH=/home/enf-replay/nodeos/usr/bin/:${PATH}
export PATH

# get snapshots and end blocks by running full_run.py --instructions
# Genesis END_NUM=0
# SNAP=snapshot-2019-08-11-16-eos-v6-0073487941.bin.zst; END_NUM=73999999
# SNAP=snapshot-2020-02-16-16-eos-v6-0105491080.bin.zst ; END_NUM=105999999
# SNAP=snapshot-2020-05-10-16-eos-v6-0119970792.bin.zst; END_NUM=119999999
# SNAP=snapshot-2020-06-24-16-eos-v6-0127744602.bin.zst; END_NUM=127999999
# SNAP=snapshot-2020-08-19-16-eos-v6-0137418534.bin.zst; END_NUM=137999999
# SNAP=snapshot-2020-11-11-16-eos-v6-0151927809.bin.zst; END_NUM=151999999
# SNAP=snapshot-2021-01-17-16-eos-v6-0163499038.bin.zst; END_NUM=163999999
# SNAP=snapshot-2021-07-11-16-eos-v6-0193719865.bin.zst ; END_NUM=193999999
# SNAP=snapshot-2022-10-05-16-eos-v6-0271620354.bin.zst ; END_NUM=271999999

aws s3 cp s3://chicken-dance/mainnet/snapshots/${SNAP} /data/nodeos/snapshot
zstd -d /data/nodeos/snapshot/*.zst

# start with a snapshot
nodeos --snapshot /data/nodeos/snapshot/${SNAP%.*} \
  --data-dir "${NODEOS_DIR}"/data/ \
  --config "${CONFIG_DIR}"/sync-config.ini \
  --terminate-at-block ${END_NUM}

# ok now we are ready to run