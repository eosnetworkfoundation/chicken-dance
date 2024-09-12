#!/usr/bin/env bash
set -x
for i in /data/nodeos/data/blocks/retained/blocks-*.log
do
block_f=${i##*/}
block_i=${block_f%.*}.index
if [ ! -f /data/nodeos/data/blocks/archive/${block_f}.zst ]; then
	echo "working on ${block_f} and ${block_i}"
	cp /data/nodeos/data/blocks/retained/${block_f} /data/nodeos/data/blocks/archive/
	cp /data/nodeos/data/blocks/retained/${block_i} /data/nodeos/data/blocks/archive/
	a_check=$(md5sum /data/nodeos/data/blocks/retained/${block_f} | cut -d' ' -f1)
	b_check=$(md5sum /data/nodeos/data/blocks/archive/${block_f} | cut -d' ' -f1)
	if [ $a_check == $b_check ]; then
		zstd /data/nodeos/data/blocks/archive/${block_i}
		zstd /data/nodeos/data/blocks/archive/${block_f}
		aws s3 cp /data/nodeos/data/blocks/archive/${block_i}.zst s3://chicken-dance/mainnet/aggregated_blocks_compressed/
		aws s3 cp /data/nodeos/data/blocks/archive/${block_f}.zst s3://chicken-dance/mainnet/aggregated_blocks_compressed/
		if [ $? -eq 0 ]; then
			rm /data/nodeos/data/blocks/archive/${block_i} /data/nodeos/data/blocks/archive/${block_f}
		fi
	fi
fi
done
