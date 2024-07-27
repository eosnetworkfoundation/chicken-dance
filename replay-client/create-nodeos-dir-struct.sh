#!/usr/bin/env bash

# Create directory structure for replay 

CONFIG_DIR="${1}"
TUID=$(id -ur)

# must not be root to run
if [ "$TUID" -eq 0 ]; then
    echo "Trying to run as root user exiting"
    exit
fi

echo "Creating nodeos directories"
[ ! -d /data/nodeos ] && mkdir /data/nodeos
[ ! -d /data/nodeos/config ] && mkdir /data/nodeos/config
[ ! -d /data/nodeos/data ] && mkdir /data/nodeos/data
[ ! -d /data/nodeos/snapshot ] && mkdir /data/nodeos/snapshot
[ ! -d /data/nodeos/log ] && mkdir /data/nodeos/log

cp "${CONFIG_DIR}"/*.* /data/nodeos/config
