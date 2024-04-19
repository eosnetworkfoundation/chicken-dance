"""Module provides job summary function"""
from job_status import JobStatusEnum

# pylint: disable=too-few-public-methods
class JobSummary:
    """Class provides job summary function"""

    @staticmethod
    def create(job_manager):
        """Creates report object for summary report"""
        report = {
            'total_blocks': 0,
            'blocks_processed': 0,
            'total_jobs': 0,
            'jobs_succeeded': 0,
            'jobs_failed': 0,
            'failed_jobs': []
        }
        for this_job_obj in job_manager.get_all().items():
            # jobid = this_job_obj[0]
            job = this_job_obj[1]
            # caculate progress
            if job.slice_config.end_block_id > job.slice_config.start_block_id \
            and job.slice_config.start_block_id > 0:
                report['total_blocks'] += job.slice_config.end_block_id \
                    - job.slice_config.start_block_id
            if job.last_block_processed > 0:
                report['blocks_processed'] += job.last_block_processed \
                    - job.slice_config.start_block_id

            # try to fix errors, where expected integrity hash was populated after job finish
            # this race condition leaves job incorrectly marked as HASH_MISMATCH, and we can fix
            if job.status == JobStatusEnum.HASH_MISMATCH:
                if job.slice_config.expected_integrity_hash == job.actual_integrity_hash:
                    job.status = JobStatusEnum.COMPLETE
            # look for COMPLETE jobs witch hash mistmatch, mark status
            if job.status == JobStatusEnum.COMPLETE \
                and job.slice_config.expected_integrity_hash != job.actual_integrity_hash:
                job.status = JobStatusEnum.HASH_MISMATCH
            # look for ERROR state both hashes are None/Empty
            if job.status == JobStatusEnum.COMPLETE \
                and not job.slice_config.expected_integrity_hash \
                and not job.actual_integrity_hash:
                job.status = JobStatusEnum.ERROR
            # process succceed jobs
            report['total_jobs'] += 1
            if job.status == JobStatusEnum.COMPLETE \
                and job.slice_config.expected_integrity_hash == job.actual_integrity_hash:
                report['jobs_succeeded'] += 1
            # process failed jobs
            if job.status in (JobStatusEnum.ERROR, JobStatusEnum.TIMEOUT, JobStatusEnum.HASH_MISMATCH):
                report['jobs_failed'] += 1
                report['failed_jobs'].append(
                {
                    'status': job.status.name,
                    'jobid': job.job_id ,
                    'configid': job.slice_config.replay_slice_id
                    })
        return report
