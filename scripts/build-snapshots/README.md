# Building Assets For Optimized Run

This is rather complicated. Some periods take longer to process blocks compared to other periods. In one period you may only be able to process 250,000 blocks in 3 hours, while during another period you can process 750,000 blocks in an hour. Before even starting you need statistics on the avg processing time per block. With these statistics in place you may assemble the meta-data file needed to build out a list of optimized intervals.

## Python Libs
Update `PYTHONPATH` to include `replay-test/scripts/manifest`. This is needed to pick up the `s3Interface.py` file.

Run `pip install tomli` and `pip install numpy`

## Optimized Spacing
The file [optimized_block_spacing.tsv](../../meta-data/optimized_block_spacing.tsv) is a tab seperated file with three columns. A start range, an end range, and the number of blocks that can be processed in 3 hours. You need a file like this with the basic data to create a list of start and end ranges that may be completed in a reasonable amount of time. For example you could have the following line in the file:
`100000000    120000000   250000`
This means that between blocks `100000000` and `120000000` a reasonable number of blocks to process is `250000`. Doing the same across the entire range of blocks yields fairly even slices for a replay tests. Even slices create a better distribution of work, and better utilization of reasources.   

The blocks range must be contiguous. If a block is skipped between and end block and the next start block it is not possible to build the manifest. This condition is a safety check to ensure a good manifest is created.

Once you have created you list of start, end, and block spaces you may run `python3 generate_full_run_data.py --file meta-data/optimized_block_spacing.tsv > ~/home/enf-replay/optimized-blocks.csv` to create an expanded list which contains every start, end period. Generating the full run creates one start, end entry for every block space. For example from our example above the following lines would be produced:

```
100000000,100250000,250000
100250000,100500000,250000
100500000,100750000,250000
100750000,101000000,250000
...
119000000,119250000,250000
119250000,119500000,250000
119750000,120000000,250000
```

## Assets Generated
The purpose of having the manifest with the optimized spacing is to generate snapshots at the start of each period, and generated block.logs in even strides.

### Blocks Logs
The proper nodeos configuration will created blocks.logs with strides. This configuration is used when starting nodeos for a replay from peers. With the following configuration blocks logs in strides of 2,000,000 will be created in the directory named `retained`
```
# blocks logs managment
blocks-log-stride = 2000000
max-retained-block-files = 512
blocks-retained-dir = retained
```

### Snapshots
As the replay is progressing a background script checks to see if the node has reached a block height between the start/end blocks for an optimized range. When this happened the background script will create a snapshot. The result is snapshots created for every optimized block spacing interval.

## Parallel Run
A full run takes time. To speed up the calendar time it takes the manifest will generate instructions for breaking the work into 10 even slices. To see these instructions run `python3 scripts/foundational-run-asset-generation/generate_full_run_data.py --file meta-data/optimized_block_spacing.tsv --instructions`. These instructions will provide the snapshot or genesis file to start the slice, and the range of blocks to run. Simple update the scripts `start_nodeos_first.sh` and `full_run_for_slice.sh` with the snapshot, start, end for the relevant slice.

## Requirements
A fairly beefy machine with 8 cores and 8Tb of attached storage mounted at /data

## Order of Operations
Run `start_nodeos_first.sh` followed by `full_run_for_slice.sh`. Specifically this is the process
- IMPORTANT, review both scripts to make sure the start, end, and snapshot are consistent and match the expected interval
- copy and past the first 29 lines from `start_nodeos_first.sh` into the terminal, and check for errors
- now copy and paste the remaining portion of the `start_nodeos_first.sh`
- quickly `tail /data/nodeos/log/nodeos.log` and check that nodeos is loading the snapshot or processing blocks
- You checked the interval for start, end in step 1 right?
- Now run `nohup full_run_for_slice.sh > /data/nodeos/log/run.log &`
- `tail -f /data/nodeos/log/run.log` and watch to see the script create the first snapshot

### Moving Assets to the Cloud
You need to upload assets to cloud storage. There are some example scripts `p_snaps.sh` to upload snapshots and `p_blocks.sh` to upload blocks.
