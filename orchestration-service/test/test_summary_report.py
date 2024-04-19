"""
Module provides testing for summary report function
This function is found in web_service.py
"""
import pytest
import json
from pathlib import Path
import copy
from datetime import datetime
from replay_configuration import ReplayConfigManager
from job_status import JobStatusEnum, JobStatus, JobManager
from job_summary import JobSummary

def test_summary_report():
    replay_config_manager = ReplayConfigManager('../../meta-data/test-simple-jobs.json')
    jobs = JobManager(replay_config_manager)
    report = JobSummary.create(jobs)
    assert report['total_jobs'] == 3
    assert report['blocks_processed'] == 0

def test_repair_hashmismatch():
    replay_config_manager = ReplayConfigManager('../../meta-data/test-simple-jobs.json')
    # get expected integrity hash from first slice
    config = replay_config_manager.get(1)
    expected_integrity_hash = copy.deepcopy(config.expected_integrity_hash)
    # update expected integrity hash to None, simulate late arriving hash
    config.expected_integrity_hash = None
    job_manager = JobManager(replay_config_manager)
    # update corrisponding job to COMPLETE with actual integrity hash from above
    for this_job_obj in job_manager.get_all().items():
        # jobid = this_job_obj[0]
        job = this_job_obj[1]
        if job.slice_config.expected_integrity_hash is None:
            job.status = JobStatusEnum.COMPLETE
            job.actual_integrity_hash = expected_integrity_hash
            job.last_block_processed = job.slice_config.end_block_id
            job.end_time = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    # run report, should have 1 failure with HASH_MISMATCH status
    report = JobSummary.create(job_manager)
    assert report['total_jobs'] == 3
    assert report['blocks_processed'] > 0
    assert report['jobs_failed'] == 1
    assert report['jobs_succeeded'] == 0
    assert report['failed_jobs'][0]['status'] == JobStatusEnum.HASH_MISMATCH.name
    # go back and update expected integrity hash to match actual
    for this_job_obj in job_manager.get_all().items():
        # jobid = this_job_obj[0]
        job = this_job_obj[1]
        if job.slice_config.expected_integrity_hash is None:
            job.slice_config.expected_integrity_hash = expected_integrity_hash
    # re-run report, and now 1 job success with status COMPLETE, 0 jobs failed
    report = JobSummary.create(job_manager)
    assert report['total_jobs'] == 3
    assert report['blocks_processed'] > 0
    assert report['jobs_failed'] == 0
    assert report['jobs_succeeded'] == 1
    assert len(report['failed_jobs']) == 0
