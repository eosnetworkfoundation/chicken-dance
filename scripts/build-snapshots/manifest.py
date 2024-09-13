"""processes manifest for to create optimized replay slices"""
import logging
import numpy
from s3Interface import S3Interface

class Manifest:
    """opens manifest file with three columns
    start, end, span
    parses and expands manifest if start and end range contain spans"""
    def __init__(self, file):
        self.manifest = self.parse(file)
        self.manifest = self.expand()
        self.length = len(self.manifest)
        self.slice_instructions = self.ten_slices()

    def parse(self,file):
        """open file , parse and sort"""
        unordered_manifest = {}
        with open(file, 'r', encoding='utf-8') as manifest_file:
            for line in manifest_file:
                clean = line.strip()
                start = int(clean.split('\t')[0])
                end = int(clean.split('\t')[1])
                span = int(clean.split('\t')[2])
                unordered_manifest[start] = {'start_num': start, 'end_num':end, 'span': span }
        return unordered_manifest

    def expand(self):
        """some start and end ranges need to be broken up into smaller chunks to optimize loading"""
        buffer_multiple = 1.1
        new_entries = {}
        for outer_record in self.manifest.values():
            # start + (span * 1.1) is less then end, we need to break up this record
            # otherwise the record is fine and we leave it alone
            if outer_record['start_num']\
                + (outer_record['span'] * buffer_multiple) < outer_record['end_num']:
                inner_start = int(outer_record['start_num'])
                span = outer_record['span']
                # loop until the range is small enough
                while inner_start < outer_record['end_num']:
                    inner_end = inner_start + span
                    # explicit set end when it exceeds the outer record end
                    if inner_start + (span * buffer_multiple) > outer_record['end_num']:
                        inner_end = outer_record['end_num']
                    # create or update a new record
                    logging.debug("creating new record start %s end %s span %s",
                        inner_start, inner_end, span)
                    new_entries[inner_start]\
                        = {'start_num': inner_start, 'end_num':inner_end, 'span': span }
                    # start a new inner range
                    inner_start = int(inner_end)
        # loop over new entries and either add new records,
        # OR overwrite existing records
        # everything else is left the same
        if new_entries:
            for key, new_rec in new_entries.items():
                self.manifest[key] = new_rec
        # sort becuase new entries not added in key order
        return {k: self.manifest[k] for k in sorted(self.manifest)}

    def ten_slices(self):
        """divide into ten slices, for parallized run,
        overlapping block ranges to ensure continuity"""
        total_records = len(self.manifest)
        slice_size = numpy.floor_divide(total_records, 10)

        counter = slice_size
        slice_num = 1
        block_num_start = 0
        block_num_end = 0
        last_key = 0
        instructions = []

        for key in self.manifest.keys():
            last_key = key
            counter -= 1
            # last loop may have a few more rows
            # so we exclude the last slice and handle it
            # after the loop finishes
            if counter <= 0 and slice_num < 10:
                counter = slice_size
                logging.debug("ten_slices starting slice %s", slice_num)
                # end at next 2mil block span with overlap
                block_num_end = round(key/2000000)*2000000
                # start is actually the termination of prep step
                # so we want to start one block early to capture the desired
                # block num in our blocks log
                if block_num_start > 0:
                    block_num_start -= 1
                instructions.append({
                    'slice': slice_num,
                    'block_start': block_num_start,
                    'block_end': block_num_end,
                    'manifest_largest_start_num': key
                })
                # build the next slice
                slice_num += 1
                # start next at 2mil block span with overlap
                block_num_start = numpy.floor_divide(key,2000000)*2000000
        # do slice #10
        block_num_end = round(last_key/2000000)*2000000
        instructions.append({
            'slice': slice_num,
            'block_start': block_num_start-1,
            'block_end': block_num_end,
            'manifest_largest_start_num': last_key
        })
        return instructions

    def print_instructions(self, store, store_type):
        """Print out what snapshots to load to prep the slices,
        and what block number to terminate the slice"""
        logging.debug("instructions has %s entries", len(self.slice_instructions))

        # name only s3 listing
        snapshot_list = S3Interface.list(store, store_type + "/snapshots/", True)
        snapshot_dict = {}
        # create a sorted dictionary of the snapshots
        for file in snapshot_list:
            block_num = int(file.split('-')[7].split('.')[0])
            snapshot_dict[block_num] = file
        snapshot_dict = {k: snapshot_dict[k] for k in sorted(snapshot_dict)}


        for record in self.slice_instructions:

            # find right snapshot from our list
            preceding_block_num = 0
            snapshot = "NA"
            for block_num in snapshot_dict.keys():
                if block_num >= record['block_start']:
                    break
                preceding_block_num = block_num

            if preceding_block_num == 0:
                snapshot = "genesis"
            else:
                snapshot = snapshot_dict[preceding_block_num]

            print(f"""
            ------ Slice {record['slice']} ------
            Load Snapshot {snapshot}
            Before Run Sync Until {record['block_start']}
            Terminate Sync at block {record['block_end']} 
            """)

    def is_valid(self):
        """one more pass through to validate"""
        max_block_key = 0
        for key in self.manifest.keys():
            if key > max_block_key:
                max_block_key = key
        max_block_height = self.manifest[max_block_key]['end_num']
        for record in self.manifest.values():
            # except for very last block make sure every entry is contiguous
            # continguous every end block is linked to another start block
            if record['end_num'] != max_block_height and record['end_num'] not in self.manifest:
                logging.error("failed to find record matching %s", record['end_num'])
                return False
        return True

    def len(self):
        """return num of entries"""
        return self.length

    def __str__(self):
        return_str = ""
        sep=","
        for record in self.manifest.values():
            return_str += f"{record['start_num']}{sep}{record['end_num']}{sep}{record['span']}\n"
        return return_str
