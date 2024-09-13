"""text visuallization of blocks and snapshots in cloud store"""
import argparse
import numpy
from s3Interface import S3Interface

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='look at objects in s3 and create a summary')
    parser.add_argument('--bucket', type=str, default="chicken-dance",
        help='s3 bucket')
    parser.add_argument('--block-dir', type=str, help='directory to blocks')
    parser.add_argument('--snap-dir', type=str, help='directory to snapshots')

    args = parser.parse_args()
    if args.block_dir[-1] != "/":
        args.block_dir = args.block_dir + "/"
    if args.snap_dir[-1] != "/":
        args.snap_dir = args.snap_dir + "/"

    blocks_list = S3Interface.list(args.bucket, args.block_dir, True)
    snaps_list  = S3Interface.list(args.bucket, args.snap_dir , True)

    MAX_BLOCK_HEIGHT=399000001

    complete_block_list = {}
    for i in range(1, MAX_BLOCK_HEIGHT, 2000000):
        complete_block_list[int(i)] = {}

    snapshot_dict = {}
    # create a dictionary of the snapshots
    for file in snaps_list:
        block_num = int(file.split('-')[7].split('.')[0])
        # round down to nearest 2mill block
        start_block_range = numpy.floor_divide(block_num, 2000000) * 2000000 + 1

        key = int(start_block_range)
        snap_count = 1

        if key in snapshot_dict \
            and "snap_count" in snapshot_dict[key] \
            and snapshot_dict[key]["snap_count"] > 0 :
            snap_count = snapshot_dict[key]["snap_count"] + 1

        snapshot_dict[key] = {
            'snapshot': file,
            'block_num': block_num,
            'has_snap': True,
            'snap_count': snap_count
        }

    for file in blocks_list:
        file_no_ext = file.split('.')[0]
        start_block_range = file_no_ext.split('-')[1]
        key = int(start_block_range)
        end_block_range = file_no_ext.split('-')[2]

        has_snap = False
        if key in snapshot_dict and "has_snap" in snapshot_dict[key] \
            and snapshot_dict[key]["has_snap"]:
            has_snap = True

        snap_count = 0
        if key in snapshot_dict and "snap_count" in snapshot_dict[key] \
            and snapshot_dict[key]["snap_count"] > 0:
            snap_count = snapshot_dict[key]["snap_count"]

        complete_block_list[key] = {
            'blocks':True,
            'has_snap': has_snap,
            'snap_count': snap_count
        }

    max_line_size=100
    blocks_line = ""
    count_line = ""
    snapshot_line = ""
    suppress = 0

    for range in complete_block_list.keys():
        if "blocks" in complete_block_list[range] \
            and complete_block_list[range]['blocks']:
            blocks_line += "+"
        else:
            blocks_line += " "

        if "snap_count" in complete_block_list[range] \
            and complete_block_list[range]['snap_count'] > 0:
            if complete_block_list[range]['snap_count'] > 9:
                snapshot_line += "*"
            else:
                snapshot_line += str(complete_block_list[range]['snap_count'])
        else:
            snapshot_line += " "

        if (range-1) % 40000000 == 0:
            key_as_str = str(range)
            if len(key_as_str) > 8:
                # replace last 2 char
                count_line = count_line[:-2] + key_as_str[0] + key_as_str[1] + "0M"
                if len(count_line) < 5:
                    suppress = 3
                else:
                    suppress = 1
            else:
                if key_as_str == "1":
                    count_line = count_line[:-1] + key_as_str
                else:
                    count_line = count_line[:-1] + key_as_str[0] + "0M"
                    if len(count_line) < 4:
                        suppress = 2
                    else:
                        suppress = 1
        else:

            if suppress == 0:
                count_line += "."
            else:
                suppress -= 1

        max_line_size = max_line_size - 1
        if max_line_size < 1:
            print("blocks: " + blocks_line + "E")
            print(" snaps: " + snapshot_line + "E")

            count_line = count_line[:-4] + str(range)[0:3] + "M"
            print(" count: " + count_line + "E")
            blocks_line=""
            count_line=""
            snapshot_line=""
            max_line_size=100

    if len(blocks_line) > 2:
        print("blocks: " + blocks_line + "E")
        print(" snaps: " + snapshot_line + "E")
        print(" count: " + count_line+"E")
