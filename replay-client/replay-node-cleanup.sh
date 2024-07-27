#!/usr/bin/env bash

# cleans up data files and kills nodes enable replay to run again

USER=${1:-"enf-replay"}

# aggressivley terminate nodeos
# start nicely then get mean
for signal in 15 9
do
    PID=$(ps -u "${USER:?}" | grep nodeos | sed -e 's/^[[:space:]]*//' | cut -d" " -f1)
    if [ -n "$PID" ]; then
        kill -"${signal}" $PID
        sleep 5
    fi
done

# remove data
rm -rf /data/nodeos
rm /tmp/job.conf.json

# remove package
rm /home/${USER:?}/*.deb
