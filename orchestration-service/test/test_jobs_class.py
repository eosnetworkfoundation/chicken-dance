"""Module provides testing."""
import pytest
"""Module provides loading and dumping of config and status."""
import json
"""Module provides marshling replay records."""
from replay_configuration import ReplayConfigManager
"""Module provides building config for replay node from json meta-data."""
from replay_configuration import BlockConfigManager
"""Module provides job manager class."""
from job_status import JobManager
"""Module provides job status class."""
from job_status import JobStatus
"""Module provides job statuses as enum."""
from job_status import JobStatusEnum

# initialize replay configs once and use in many tests
@pytest.fixture(scope="module")
def setup_module():
    # Your setup code here
    print("Setting up Test Jobs...")
    return ReplayConfigManager('../../meta-data/test-simple-jobs.json')

# build a manager and get a job
def test_initialize_job_manager(setup_module):
    manager = JobManager(setup_module)
    assert manager is not None

# replay_configs has only 3 items
# only 3 jobs, after getting them 3 times, the 4th job request should be None
def test_exhaust_jobs(setup_module):
    manager = JobManager(setup_module)
    for _ in range(3):
        job = manager.get_next_job()
        assert job.status == JobStatusEnum.WAITING_4_WORKER
        job.status = JobStatusEnum.STARTED
        manager.set_job(job.as_dict())
        assert job is not None
    job = manager.get_next_job()
    assert job is None

# test formatting
def test_jobs_formats(setup_module):
    manager = JobManager(setup_module)
    job = manager.get_next_job()
    assert str(job) == f"job_id={job.job_id}, replay_slice_id={job.slice_config.replay_slice_id}, snapshot_path={job.slice_config.snapshot_path}, \
storage_type={job.slice_config.storage_type}, leap_version={job.slice_config.leap_version}, start_block_num={job.slice_config.start_block_id}, \
end_block_num={job.slice_config.end_block_id}, status={job.status.name}, last_block_processed={job.last_block_processed}, \
start_time={job.start_time}, end_time={job.end_time}, \
expected_integrity_hash={job.slice_config.expected_integrity_hash}, actual_integrity_hash={job.actual_integrity_hash}, error_message=None"
    job_as_dict = job.as_dict()
    assert job_as_dict['job_id'] == job.job_id
    assert job_as_dict['status'] == job.status.name
    assert job_as_dict['start_time']  == job.start_time

def test_update_job(setup_module):
    manager = JobManager(setup_module)
    job = manager.get_next_job()
    job_as_dict = job.as_dict()
    job_as_dict['status'] = "WORKING"
    job_as_json = json.dumps(job_as_dict)

    assert job.status != JobStatusEnum.WORKING
    manager.set_job_from_json(job_as_json, job.job_id)
    assert job.status == JobStatusEnum.WORKING
