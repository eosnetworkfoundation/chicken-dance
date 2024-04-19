"""Module tests web service"""
import requests
import pytest
import re
import json

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

def test_job_redirect(setup_module):
    """Equivalent results request a job using the redirect, and request with 'nextjob' param"""
    cntx, session = setup_module

    # request a job test that /job follows redirect to /job?nextjob
    # both /job and /job?nextjob should result in the same response
    follow_redir_response = session.get(cntx['base_url'] + '/job', headers=cntx['plain_text_headers'])
    assert follow_redir_response.status_code == 200
    assert len(follow_redir_response.headers['ETag']) > 30


    params = { 'nextjob': 1 }
    direct_response = session.get(cntx['base_url'] + '/job',
        params=params,
        headers=cntx['plain_text_headers'])

    #print (f"headers {direct_response.headers} content {direct_response.content}")
    assert direct_response.status_code == 200
    assert follow_redir_response.content == direct_response.content
    assert follow_redir_response.headers['ETag'] == direct_response.headers['ETag']

def test_get_nextjob(setup_module):
    """Validate the data returned differs by Content Type"""
    cntx, session = setup_module

    # test plain text
    params = { 'nextjob': 1 }
    response_plain = session.get(cntx['base_url'] + '/job', params=params, headers=cntx['plain_text_headers'])

    assert response_plain.status_code == 200
    print(response_plain.content.decode('utf-8'))
    plain_text_match = re.search(r"job_id=[0-9]+, replay_slice_id=1, snapshot_path=[a-z-A-Z0-9\\.\\/\\-\\:]+, storage_type=s3, leap_version=[rcdev0-9\\.\\-]+, start_block_num=[0-9]+, end_block_num=[0-9]+, status=WAITING_4_WORKER, last_block_processed=0, start_time=\d+-\d+-\d+T\d+:\d+:\d+, end_time=None, expected_integrity_hash=[A-Za-z0-9]+, actual_integrity_hash=None",
        response_plain.content.decode('utf-8'))
    assert plain_text_match

    # test json
    params = { 'nextjob': 1 }
    response_json = session.get(cntx['base_url'] + '/job', params=params, headers=cntx['json_headers'])

    assert response_json.status_code == 200
    # print (response_json.content.decode('utf-8'))
    json_match = re.search(r"\{\"job_id\": [0-9]+, \"replay_slice_id\": 1, \"snapshot_path\": \"[a-z-A-Z0-9\\.\\/\\-\\:]+\", \"storage_type\": \"s3\", \"leap_version\": \"[rcdev0-9\\.\\-]+\", \"start_block_num\": [0-9]+, \"end_block_num\": [0-9]+, \"status\": \"WAITING_4_WORKER\", \"last_block_processed\": 0, \"start_time\": \"\d+-\d+-\d+T\d+:\d+:\d+\", \"end_time\": null, \"expected_integrity_hash\": \"[A-Za-z0-9]+\", \"actual_integrity_hash\": null\}",
        response_json.content.decode('utf-8'))
    assert json_match

def test_update_job(setup_module):
    """Get a job update the status and validate the change is in place"""
    cntx, session = setup_module

    # test plain text
    params = { 'nextjob': 1 }
    response_first = session.get(cntx['base_url'] + '/job', params=params, headers=cntx['json_headers'])
    assert response_first.status_code == 200
    etag_value = response_first.headers['ETag']

    # we are going to change status
    # validate status before change
    job_first_request = json.loads(response_first.content.decode('utf-8'))
    assert job_first_request['status'] != 'STARTED'

    # update status to STARTED
    params = { 'jobid': job_first_request['job_id'] }
    job_first_request['status'] = 'STARTED'

    # serialized dict to JSON when passing in
    # Add ETag Header
    cntx['json_headers']['ETag'] = etag_value
    updated_first = session.post(cntx['base_url'] + '/job',
        params=params,
        headers=cntx['json_headers'],
        data=json.dumps(job_first_request))
    assert updated_first.status_code == 200
    etag_value = updated_first.headers['ETag']

    # fetch again to validate update
    # validate status after change
    params = { 'jobid': job_first_request['job_id'] }
    validate_job_request = session.get(cntx['base_url'] + '/job', params=params, headers=cntx['json_headers'])
    validate_job = json.loads(validate_job_request.content.decode('utf-8'))
    assert validate_job['status'] == 'STARTED'

    # restore job to enable reruns of tests
    validate_job['status'] = 'WAITING_4_WORKER'
    jobparams = { 'jobid': validate_job['job_id'] }
    # add ETag Header
    cntx['json_headers']['ETag'] = etag_value
    updated = session.post(cntx['base_url'] + '/job',
        params=jobparams,
        headers=cntx['json_headers'],
        data=json.dumps(validate_job))
    # clear out value
    cntx['json_headers']['ETag'] = ""
    # this should always update
    assert updated.status_code == 200

    # double updates no possible
    # prevents race conditions and old updates coming through
    jobparams = { 'jobid': validate_job['job_id'] }
    # add previous older and bad ETag Header
    cntx['json_headers']['ETag'] = etag_value
    updated = session.post(cntx['base_url'] + '/job',
        params=jobparams,
        headers=cntx['json_headers'],
        data=json.dumps(validate_job))
    # clear out value
    cntx['json_headers']['ETag'] = ""
    # fails on ETag Mismatch
    assert updated.status_code == 400

def test_no_more_jobs(setup_module):
    """Using nextjob loop over the jobs updating status; eventually no more jobs and None is returned"""
    cntx, session = setup_module

    params = { 'nextjob': 1 }

    _ok = True
    counter = 0
    # array of jobs to restore
    # restore jobs to allow repeat test runs
    restore_jobs = []
    # need this dict to hold etag to restore jobs state
    etag_db = {}

    while _ok:
        nextjobparams = { 'nextjob': 1 }
        response = session.get(cntx['base_url'] + '/job', params=nextjobparams, headers=cntx['json_headers'])
        # end on not found 404
        if response.status_code == 404:
            _ok = False
        # track how many good results
        # only 200 OK have ETag
        if response.status_code == 200:
            counter += 1
            etag_value = response.headers['ETag']
        result = response.content
        # no infinite loops
        if counter > 10:
            break
        # update status to remove job from 'nextjob' queue
        if _ok:
            job = json.loads(result.decode('utf-8'))
            # save for later
            restore_jobs.append(job)
            # update status
            job['status'] = 'STARTED'
            jobparams = { 'jobid': job['job_id'] }
            # add ETag to Request
            cntx['json_headers']['ETag'] = etag_value
            updated = session.post(cntx['base_url'] + '/job',
                params=jobparams,
                headers=cntx['json_headers'],
                data=json.dumps(job))
            # this should always update
            assert updated.status_code == 200
            # clear out old header and store lookup for future use
            cntx['json_headers']['ETag'] = ""
            # post returns new ETag matching modified content
            etag_db[job['job_id']] = updated.headers['ETag']
    # count differs depending on order of test execution
    assert counter > 1

    # restore job status otherwise reruns cause test failure
    for job in restore_jobs:
        # pass by reference not deep copy reset status
        job['status'] = 'WAITING_4_WORKER'
        jobparams = { 'jobid': job['job_id'] }
        # Add ETag
        cntx['json_headers']['ETag'] = etag_db[job['job_id']]
        updated = session.post(cntx['base_url'] + '/job',
            params=jobparams,
            headers=cntx['json_headers'],
            data=json.dumps(job))
        # this should always update
        assert updated.status_code == 200

def test_status_reports(setup_module):
    """Request full status and check results"""
    cntx, session = setup_module

    response = session.get(cntx['base_url'] + '/status', headers=cntx['json_headers'])
    assert response.status_code == 200
    assert len(response.content) > 500
    response = session.get(cntx['base_url'] + '/status', headers=cntx['plain_text_headers'])
    assert response.status_code == 200
    assert len(response.content) > 500
    response = session.get(cntx['base_url'] + '/status', headers=cntx['html_headers'])
    assert response.status_code == 200
    assert len(response.content) > 500
    # check position arg
    params = { 'sliceid': 1 }
    response = session.get(cntx['base_url'] + '/status',
        params=params,
        headers=cntx['json_headers'])
    assert response.status_code == 200
    assert len(response.content) > 50
    response = session.get(cntx['base_url'] + '/status',
        params=params,
        headers=cntx['plain_text_headers'])
    assert response.status_code == 200
    assert len(response.content) > 50
    response = session.get(cntx['base_url'] + '/status',
        params=params,
        headers=cntx['html_headers'])
    assert response.status_code == 200
    assert len(response.content) > 50

def test_config_reports(setup_module):
    """Request full status and check results"""
    cntx, session = setup_module

    params = { 'sliceid': 1 }
    response = session.get(cntx['base_url'] + '/config',
        params=params,
        headers=cntx['json_headers'])
    assert response.status_code == 200
    assert len(response.content) > 200

    params = { 'sliceid': 1 }
    response = session.get(cntx['base_url'] + '/config',
        params=params,
        headers=cntx['html_headers'])
    assert response.status_code == 200
    assert len(response.content) > 200

def test_post_config(setup_module):
    """Update Config"""
    cntx, session = setup_module

    config = {
        "end_block_num": 324302525,
        "integrity_hash": "NANANANANAN",
    }

    params = { 'sliceid': 3 }
    responseBefore = session.get(cntx['base_url'] + '/config',
        params=params,
        headers=cntx['json_headers'])
    assert responseBefore.status_code == 200
    configBefore = json.loads(responseBefore.content.decode('utf-8'))
    assert configBefore['expected_integrity_hash'] != config['integrity_hash']

    # make POST call; json passed in as string
    update_config_response = session.post(cntx['base_url'] + '/config',
        headers=cntx['json_headers'],
        timeout=3,
        data=json.dumps(config))
    assert update_config_response.status_code == 200

    params = { 'sliceid': 3 }
    responseAfter = session.get(cntx['base_url'] + '/config',
        params=params,
        headers=cntx['json_headers'])
    assert responseAfter.status_code == 200
    configAfter = json.loads(responseAfter.content.decode('utf-8'))

    # all references should have the same value
    assert configAfter['expected_integrity_hash'] != configBefore['expected_integrity_hash']

def test_healthcheck(setup_module):
    """Test Healthcheck"""
    cntx, session = setup_module

    html_response = requests.get(cntx['base_url'] + '/healthcheck',headers=cntx['html_headers'])

    assert html_response.status_code == 200
    content = html_response.content.decode('utf-8')
    assert content == "OK"

def test_summary(setup_module):
    """Test Summary Report Page"""
    cntx, session = setup_module

    text_response = session.get(cntx['base_url'] + '/summary',headers=cntx['plain_text_headers'])
    json_response = session.get(cntx['base_url'] + '/summary',headers=cntx['json_headers'])

    assert text_response.status_code == 200
    assert json_response.status_code == 200
    text_content = text_response.content.decode('utf-8')
    json_content = json_response.content.decode('utf-8')
    assert len(text_content) > 10
    assert len(json_content) > 10

    assert text_content != json_response

def test_detail(setup_module):
    """Test the Detail Job Page"""
    cntx, session = setup_module

    response = session.get(cntx['base_url'] + '/detail', headers=cntx['html_headers'])

    assert response.status_code == 200
    html_content = response.content.decode('utf-8')
    assert len(html_content) > 10

def test_dynamic_html(setup_module):
    """Test progress , grid and controll"""
    cntx, session = setup_module

    progress_response = session.get(cntx['base_url'] + '/progress',headers=cntx['html_headers'])
    grid_response = session.get(cntx['base_url'] + '/grid',headers=cntx['html_headers'])
    control_response = session.get(cntx['base_url'] + '/control',headers=cntx['html_headers'])

    assert progress_response.status_code == 200
    assert grid_response.status_code == 200
    assert control_response.status_code == 200

    progress_html = progress_response.content.decode('utf-8')
    grid_html = grid_response.content.decode('utf-8')
    control_html = control_response.content.decode('utf-8')

    assert len(progress_html) > 1065
    assert len(grid_html) > 1065
    assert len(control_html) > 1065

    assert progress_html != grid_html
    assert progress_html != control_html
    assert grid_html != control_html
