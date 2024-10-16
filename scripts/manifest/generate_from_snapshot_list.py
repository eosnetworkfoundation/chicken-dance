import sys
import json

#    {
#        "start_block_id": 0,
#        "end_block_id": 15819,
#        "snapshot_path": "s3://chicken-dance/mainnet/snapshots/snapshot-2018-06-10-01-eos-v6-0000000000.bin.zst",
#        "storage_type": "s3",
#        "expected_integrity_hash": "",
#        "leap_version": "1.0.0-rc2"
#    },

if __name__ == '__main__':
    manifest = []

    start_block_num = 0
    snapshot_file_name = "snapshot-2018-06-10-01-eos-v8-0000000000.bin.zst"


    with open('snapshots.txt', 'r') as file:
        lines = file.readlines()
        for line in lines:
            next_snapshot_file_name = line.strip()
            #snapshot-2024-08-12-00-eos-v6-388397365.bin.zst
            parts = next_snapshot_file_name.split("-")
            if parts[0] != "snapshot" or parts[5] != "eos" or parts[6] != "v8":
                print(f"error parsing {snapshot}")
                sys.exit
            end_block_num = int(parts[7].split(".")[0])
            record = {
                "start_block_id": start_block_num,
                "end_block_id": end_block_num,
                "snapshot_path": "s3://chicken-dance/mainnet/snapshots_v8/"+snapshot_file_name,
                "storage_type": "s3",
                "expected_integrity_hash": "",
                "leap_version": "1.0.2"
                }
            manifest.append(record)
            start_block_num = end_block_num
            snapshot_file_name = next_snapshot_file_name

    # Close the file
    file.close()
    # print manifest as json
    print(json.dumps(manifest, indent=4))
