#!/usr/bin/env bash

[ ! -d /data/nodeos/data/snapshots/archive ] && mkdir -p /data/nodeos/data/snapshots/archive
for i in /data/nodeos/data/snapshots/snapshot-*.bin.zst
do
   echo $i
   aws s3 cp $i s3://chicken-dance/mainnet/snapshots_v8/
   if [ $? -eq 0 ]; then
      mv $i /data/nodeos/data/snapshots/archive
   fi
done
