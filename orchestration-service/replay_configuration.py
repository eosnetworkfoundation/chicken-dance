"""Module provides loading of config file in json format
   Print system errors.
   Module provides os file name and base path.
"""
import json
import sys

class BlockConfigManager:
    """
    holds all the configuration data for the replays
    `start_block_id` first block to process
    `end_block_id` last block to process
    `snapshot_path` path to snapshot file
    `storage_type` enum s3, file
    `expected_integrity_hash` at end of block
    `nodeos_version` Maj.Min.Patch-rcN or Maj.Min.Patch-commithash
    `replay_slice_id` unique id for this replay config
    """
    def __init__(self, block_record, primary_key):
        self.start_block_id = int(block_record['start_block_id'])
        self.end_block_id = int(block_record['end_block_id'])
        self.snapshot_path = block_record['snapshot_path']
        self.storage_type = block_record['storage_type']
        self.expected_integrity_hash = block_record['expected_integrity_hash']
        self.spring_version = block_record['spring_version']
        self.replay_slice_id = primary_key

    def get_snapshot_path(self):
        """return snapshot path on replay node"""
        if not self._is_supported_storage_type():
            raise ValueError("Error BM001: storage type {self.storage_type} not supported")
        return self.snapshot_path

    def _is_supported_storage_type(self):
        """private function to validate storage types"""
        return self.storage_type in ["s3","filesystem","fs"]

    def validate_integrity_hash(self, computed_integrity_hash):
        """returns bool compared hash in config (expected) to computed_integrity_hash (actual)"""
        return computed_integrity_hash == self.expected_integrity_hash

    def as_dict(self, suppress_replay=False):
        """converts job object to a dictionary"""
        this_dict = {}
        # if supress_replay then pass else assign
        # default is to print
        if not suppress_replay:
            this_dict['replay_slice_id'] = self.replay_slice_id
        this_dict['start_block_id'] = self.start_block_id
        this_dict['end_block_id'] = self.end_block_id
        this_dict['snapshot_path'] = self.snapshot_path
        this_dict['storage_type'] = self.storage_type
        this_dict['expected_integrity_hash'] = self.expected_integrity_hash
        this_dict['spring_version'] = self.spring_version
        return this_dict

class ReplayConfigManager:
    """
    Read only class to access configuration records for a replay
    Loads the json configuration
    Creates the primary key for blocks
    provides accessor methods
    single member `records` array of BlockConfig
    """
    def __init__(self, json_file_path):
        with open(json_file_path, 'r', encoding='utf-8') as jobs_config_file:
            records = json.load(jobs_config_file)
        self.records = []
        self.current = 0
        # preserve path to dump after changes
        self.config_path = json_file_path
        if len(records) < 1:
            print("Error RM001 tried to load empty jobs file ", file=sys.stderr)
        # init the pk
        generated_id = 1
        for block in records:
            self.records.append(BlockConfigManager(block, generated_id))
            generated_id += 1

    def __iter__(self):
        return self

    def __next__(self):
        if self.current >= len(self.records):
            self.current = 0
            raise StopIteration
        self.current += 1
        return self.records[self.current-1]

    def persist(self):
        """persist records back to config file, overwriting exiting"""
        with open(self.config_path, 'w',  encoding='utf-8') as file:
            file.write(self.to_json_str())

    def get(self, primary_key):
        """get a record by id, pk is unique returns only one"""
        if not str(primary_key).isnumeric():
            return None
        primary_key = int(primary_key)
        for record in self.records:
            if record.replay_slice_id == primary_key:
                return record
        return None

    def set(self, block_config):
        """update the block configuration, return if match found"""
        primary_key = block_config.replay_slice_id
        # make the update
        for index, record in enumerate(self.records):
            if record.replay_slice_id == primary_key:
                self.records[index] = block_config
                return True
        return False

    def return_record_by_start_block_id(self, start_block_id):
        """get FIRST record by start block num"""
        for record in self.records:
            if record.start_block_id == start_block_id:
                return record
        return None

    def return_record_by_end_block_id(self, end_block_id):
        """get FIRST records by end block num"""
        for record in self.records:
            if record.end_block_id == end_block_id:
                return record
        return None

    def to_json_str(self):
        """convert to json"""
        # convert to array of dictionary
        # remove the replay slice, internal to ReplayConfigManager
        suppress_replay=True
        dictionary_repr = [obj.as_dict(suppress_replay) for obj in self.records]
        # dump json
        return json.dumps(dictionary_repr, indent=4)
