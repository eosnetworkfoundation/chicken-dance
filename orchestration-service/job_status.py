"""Module provides job status"""
import json
from datetime import datetime
from enum import Enum
import re

# pylint: disable=too-few-public-methods
class JobStatusEnum(Enum):
    """Job Lifecyle as Enum"""
    WAITING_4_WORKER = "waiting_4_worker"
    STARTED = "started"
    LOADING_SNAPSHOT = "loading_snapshot"
    WORKING = "working"
    ERROR = "error"
    TIMEOUT = "timeout"
    HASH_MISMATCH = "hash_mismatch"
    COMPLETE = "complete"

    @staticmethod
    def lookup_by_name(name):
        """return correct value give a str repr of Enum"""
        # default value
        job_status_enum = JobStatusEnum.ERROR

        if name == "WAITING_4_WORKER":
            job_status_enum = JobStatusEnum.WAITING_4_WORKER
        if name == "STARTED":
            job_status_enum = JobStatusEnum.STARTED
        if name == "LOADING_SNAPSHOT":
            job_status_enum = JobStatusEnum.LOADING_SNAPSHOT
        if name == "WORKING":
            job_status_enum = JobStatusEnum.WORKING
        if name == "ERROR":
            job_status_enum = JobStatusEnum.ERROR
        if name == "TIMEOUT":
            job_status_enum = JobStatusEnum.TIMEOUT
        if name == "HASH_MISMATCH":
            job_status_enum = JobStatusEnum.HASH_MISMATCH
        if name == "COMPLETE":
            job_status_enum = JobStatusEnum.COMPLETE

        return job_status_enum

class JobStatus:
    """
    JobsManager a dictionary that holds JobStatus
    primary key is an integer `job_id`
    has the following properties
    `replay_slice_id` integer FK linked to `BlockManger.replay_slice_id`
    `status` enum of waiting_4_worker, started, working, complete, error, timeout
        initialized to waiting_4_worker
    `last_block_processed` block id of last block processed
        initialized to 0
    `start_time` date time job started
        initialized to now
    `end_time` date time job completed
        initialized None
    `actual_integrity_hash` hash once last block has been reached
        initialized to None
    The class in inialized from an array, whose elements have a property `replay_slice_id`
    """
    def __init__(self, config):
        self.job_id = id(self)  # Using memory address as a simple unique identifier
        self.slice_config = config
        self.status = JobStatusEnum.WAITING_4_WORKER
        self.last_block_processed = 0
        self.start_time = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        self.end_time = None
        self.actual_integrity_hash = None

    def __repr__(self):
        return (f"JobStatus(job_id={self.job_id}, "
                f"replay_slice_id={self.slice_config.replay_slice_id}, "
                f"snapshot_path={self.slice_config.snapshot_path}, "
                f"storage_type={self.slice_config.storage_type}, "
                f"leap_version={self.slice_config.leap_version}, "
                f"start_block_num={self.slice_config.start_block_id}, "
                f"end_block_num={self.slice_config.end_block_id}, "
                f"status={self.status.name}, "
                f"last_block_processed={self.last_block_processed}, "
                f"start_time={self.start_time}, end_time={self.end_time}, "
                f"expected_integrity_hash={self.slice_config.expected_integrity_hash}, "
                f"actual_integrity_hash={self.actual_integrity_hash})")

    def __str__(self):
        """converts job object to string"""
        return (f"job_id={self.job_id}, "
                f"replay_slice_id={self.slice_config.replay_slice_id}, "
                f"snapshot_path={self.slice_config.snapshot_path}, "
                f"storage_type={self.slice_config.storage_type}, "
                f"leap_version={self.slice_config.leap_version}, "
                f"start_block_num={self.slice_config.start_block_id}, "
                f"end_block_num={self.slice_config.end_block_id}, "
                f"status={self.status.name}, "
                f"last_block_processed={self.last_block_processed}, "
                f"start_time={self.start_time}, end_time={self.end_time}, "
                f"expected_integrity_hash={self.slice_config.expected_integrity_hash}, "
                f"actual_integrity_hash={self.actual_integrity_hash}")

    def as_dict(self):
        """converts job object to a dictionary"""
        this_dict = {}
        this_dict['job_id'] = self.job_id
        this_dict['replay_slice_id'] = self.slice_config.replay_slice_id
        this_dict['snapshot_path'] = self.slice_config.snapshot_path
        this_dict['storage_type'] = self.slice_config.storage_type
        this_dict['leap_version'] = self.slice_config.leap_version
        this_dict['start_block_num'] = self.slice_config.start_block_id
        this_dict['end_block_num'] = self.slice_config.end_block_id
        this_dict['status'] = self.status.name
        this_dict['last_block_processed'] = self.last_block_processed
        this_dict['start_time'] = self.start_time
        this_dict['end_time'] = self.end_time
        this_dict['expected_integrity_hash'] = self.slice_config.expected_integrity_hash
        this_dict['actual_integrity_hash'] = self.actual_integrity_hash
        return this_dict


class JobManager:
    """Holds Jobs and manages persistance"""

    def __init__(self, replay_configs):
        self.jobs = {}
        for slice_config in replay_configs:
            job = JobStatus(slice_config)
            self.jobs[job.job_id] = job

    def get_job(self, job_id):
        """Return job by id, return dict or on error return None"""
        if not str(job_id).isnumeric():
            return None
        job_id = int(job_id)
        if job_id in self.jobs:
            return self.jobs[job_id]
        return None

    def get_all(self):
        """Return all jobs"""
        return self.jobs

    # needed my own integer check function
    # `isinstance` was too strict
    # pylint prefered `isinstance` over `type` check
    def is_integer(self, string):
        """custom check if is int"""
        if string is None:
            return False

        if isinstance(string, int):
            return True

        print (f"STRING {string}\n")
        # Define a regex pattern for a positive integer
        pattern = r'^\d+$'
        match = re.match(pattern, string)

        return match is not None

    def set_job(self, data):
        """update job records, from dictionary, return bool success"""

        # not a success
        if not 'job_id' in data or data['job_id'] is None:
            return False
        if not 'status' in data or data['status'] is None:
            return False

        # job id
        jobid = data['job_id']

        if 'status' in data:
            self.jobs[jobid].status = JobStatusEnum.lookup_by_name(data['status'])
        if 'last_block_processed' in data and self.is_integer(data['last_block_processed']):
            self.jobs[jobid].last_block_processed = int(data['last_block_processed'])
        if 'end_time' in data:
            self.jobs[jobid].end_time = data['end_time']
        if 'start_time' in data and 'status' in data and data['status'] == "STARTED":
            self.jobs[jobid].start_time = data['start_time']
        if 'actual_integrity_hash' in data:
            self.jobs[jobid].actual_integrity_hash = data['actual_integrity_hash']

        # success
        return True


    def set_job_from_json(self, status_as_json, jobid):
        """sets jobs data from json, calls set_job(), return bool for success"""
        data = json.loads(status_as_json)
        data['job_id'] = jobid
        return self.set_job(data)

    def get_next_job(self):
        """get a job that needs a worker"""
        for job in self.jobs.values():
            if job.status == JobStatusEnum.WAITING_4_WORKER:
                return job
        return None

    def get_by_position(self, position):
        """returns an entry by position in interator"""
        # type check
        if str(position).isnumeric():
            position = int(position)
        else:
            return None

        # iterate over dictionary and return value
        pos_i = 0
        for this_slice in self.jobs.items():
            pos_i += 1
            if pos_i == position:
                return this_slice[1]

        # check if not set and results empty
        return None
