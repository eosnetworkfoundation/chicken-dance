"""Module tests web service"""
import requests
import pytest
import json
import shutil

@pytest.fixture(scope="module")
def setup_module():
    """setting some constants to avoid mis-spellings"""
    setup = {}
    setup['base_url']='http://127.0.0.1:4000'

    setup['plain_text_headers'] = {
        'Accept': 'text/plain; charset=utf-8',
        'Content-Type': 'text/plain; charset=utf-8',
    }

    setup['json_headers'] = {
        'Accept': 'application/json',
        'Content-Type': 'application/json; charset=utf-8',
    }

    setup['html_headers'] = {
        'Accept': 'text/html, application/xhtml+xml',
        'Content-Type': 'text/html; charset=utf-8',
    }

    session = requests.Session()
    session.cookies.set('replay_auth', 'ghb_12334dfjkhaf:foobar:https://example.com/myavatar.gif')

    return setup, session

def test_service_reset(setup_module):
    """Load a new config"""
    cntx, session = setup_module

    # loop three times
    for i in range(3):
        params = { 'nextjob': 1 }
        job_response = session.get(cntx['base_url'] + '/job', params=params, headers=cntx['json_headers'])
        etag_value = job_response.headers['ETag']

        # we are going to change status
        # validate status before change
        job_request = json.loads(job_response.content.decode('utf-8'))

        # update status to COMPLETE with all blocks processed
        params = { 'jobid': job_request['job_id'] }
        job_request['status'] = 'COMPLETE'
        job_request['last_block_processed'] = job_request['end_block_num']

        # serialized dict to JSON when passing in
        # Add ETag Header
        cntx['json_headers']['ETag'] = etag_value
        updated_job = session.post(cntx['base_url'] + '/job',
            params=params,
            headers=cntx['json_headers'],
            data=json.dumps(job_request))

    # validate we exhausted all the jobs
    params = { 'nextjob': 1 }
    exhausted_job_response = session.get(cntx['base_url'] + '/job', params=params, headers=cntx['json_headers'])
    assert exhausted_job_response.status_code == 404

    # copy over new config preserve the original
    shutil.copy("../../meta-data/test-simple-jobs.json", "../../meta-data/test-modify-jobs.json")
    # post to restart service with config
    restart_job = session.post(cntx['base_url'] + '/restart',
        headers=cntx['json_headers'],
        data="config_file_path=../../meta-data/test-modify-jobs.json\n",
        timeout=5)
    assert restart_job.status_code == 200

    # validate jobs
    params = { 'nextjob': 1 }
    still_job_response = session.get(cntx['base_url'] + '/job', params=params, headers=cntx['json_headers'])
    assert still_job_response.status_code == 200
    validate_job = json.loads(still_job_response.content.decode('utf-8'))
    assert validate_job['status'] == 'WAITING_4_WORKER'

def test_force_service_reset(setup_module):
    """Load a new config"""
    cntx, session = setup_module

    # post to restart service with config
    # assert error as jobs still working
    restart_job = session.post(cntx['base_url'] + '/restart',
        headers=cntx['json_headers'],
        data="config_file_path=../../meta-data/test-modify-jobs.json\n",
        timeout=5)
    assert restart_job.status_code != 200

    # now force it
    force_data = "config_file_path=../../meta-data/test-modify-jobs.json\n"
    force_data += "forced=Yes\n"
    restart_job = session.post(cntx['base_url'] + '/restart',
        headers=cntx['json_headers'],
        data=force_data,
        timeout=5)
    assert restart_job.status_code == 200

    # validate jobs
    params = { 'nextjob': 1 }
    still_job_response = session.get(cntx['base_url'] + '/job', params=params, headers=cntx['json_headers'])
    assert still_job_response.status_code == 200
    validate_job = json.loads(still_job_response.content.decode('utf-8'))
    assert validate_job['status'] == 'WAITING_4_WORKER'
