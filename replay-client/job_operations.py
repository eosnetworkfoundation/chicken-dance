"""Module fetches a job and reserves the status."""
import re
import os
import json
from datetime import datetime
import argparse
import sys
import time
import requests


#
# Examples
# python3 ../job_operations.py --operation pop
# python3 ../job_operations.py --operation update-status --status WORKING
# python3 ../job_operations.py --operation update-status --status WORKING --job-id 4523686544
# python3 ../job_operations.py --operation update-progress --block-processed 20 --job-id 4523686544
#

def proccess_job_update(base_url, max_tries, job_id, fields):
    """Fetches Job, Updates Job Values, and Sets the Job Status"""

    # initialize params
    get_headers = {
        'Accept': 'application/json',
    }
    params = {}
    # no job_id means we get next job from queue that needs a worker
    if job_id is None:
        params = { 'nextjob': 1 }
    else:
        params = { 'jobid': job_id }

    # data stucture we get from update_job
    process_job_message = { 'status_code': None,
            'jobid': None,
            'json': None }

    # 500 milisecs double every loop
    backoff = 0.5
    update_complete = False
    # will increate by 1 each loop
    current_try = 0

    update_job_object = {}

    # loop getting and setting until success
    # etag is checksum to ensure content has not been updated by another process
    while not update_complete and current_try <= max_tries:
        # first update counter and backoff
        current_try = current_try + 1
        backoff = backoff * 2
        # get open job
        job_response = requests.get(base_url + '/job',
            params=params,
            headers=get_headers,
            timeout=3)

        # try again if error on get next job
        # this is rare so we report errror
        if job_response.status_code != 200:
            print(f"Warning: request for next job failed with code {job_response.status_code}",
                file=sys.stderr)
            time.sleep(backoff)
            continue

        # parse json, update status to claim job, grab the etag
        update_job_object = json.loads(job_response.content.decode('utf-8'))
        # loop over the passed in dictionary and update job object
        for key in fields.keys():
            update_job_object[key] = fields[key]
        response_etag = job_response.headers.get('ETag')
        # make a POST to update job
        process_job_message = update_job(base_url, response_etag, update_job_object)

        if process_job_message['status_code'] == 200:
            update_complete = True

    # outside while loop
    # if job_id is None, this is get next job, return full json
    if not job_id:
        update_job_object['status_code'] = process_job_message['status_code']
        return update_job_object
    return process_job_message

def update_job(base_url, etag, job):
    """Update job with provided job object"""

    post_headers = {
        'Content-Type': 'application/json',
    }
    # data stucture we will be returning
    update_job_message = { 'status_code': None,
            'jobid': None,
            'json': None }

    # 500 milisecs doubles every loop
    backoff = 0.5
    update_complete = False
    max_tries = 10
    # will increate by 1 each loop
    current_try = 0

    # need to specify job id and new status
    params = { 'jobid': job['job_id'] }
    # ETag from previous request prevents race conditions
    post_headers['ETag'] = etag

    # loop getting and setting until success
    # etag is checksum to ensure content has not been updated by another process
    while not update_complete and current_try <= max_tries:
        # first update counters and backoff
        current_try = current_try + 1
        backoff = backoff * 2

        # make POST call; json passed in as string
        update_job_response = requests.post(base_url + '/job',
            params=params,
            headers=post_headers,
            timeout=3,
            data=json.dumps(job))

        # populate data structure
        update_job_message['status_code'] = update_job_response.status_code
        update_job_message['jobid'] = job['job_id']
        if update_job_response.content is not None:
            update_job_message['json'] = update_job_response.content.decode('utf-8')

        # good job
        if update_job_response.status_code == 200:
            update_complete = True
        # 4xx error means client issue, no retries will fix that, abort
        elif update_job_response.status_code > 399 \
            and update_job_response.status_code < 500:
            print(f"Warning: update job failed with code {update_job_response.status_code}",
                file=sys.stderr)
            break
        # rest and try again, assume this is service side error
        else:
            # we try again pause to avoid collisions
            time.sleep(backoff)

    # outside while loop
    return update_job_message

def upload_error_log(base_url, job_id, log_type, log_path):
    """upload error logs to orchestration service, no retries"""
    upload_logpath = f"/errorlog/{log_type}{job_id}"

    # data stucture we will be returning
    update_job_message = { 'status_code': None,
        'jobid': job_id,
        'json': None }
    if not os.path.exists(log_path):
        update_job_message['status_code'] = 404
        update_job_message['json'] = f'{{message:"{log_path} file does not exist"}}'
        return update_job_message
    # read last 4,000 chars the limit for our log file
    with open(log_path, 'r', encoding='utf-8') as file:
        # Move the file pointer to 4000 characters before the end of the file
        file.seek(0, 2)  # Move to the end of the file
        file_size = file.tell()  # Get the total size of the file

        # Calculate start position
        start_pos = max(file_size - 8000, 0)
        file.seek(start_pos)
        contents = file.read()

    job_response = requests.post(base_url + upload_logpath,
        data=contents.encode('utf-8'),
        timeout=10)
    update_job_message['status_code'] = job_response.status_code
    update_job_message['json'] = f'{{message:"process complete for {log_path}"}}'
    return update_job_message


def pop_job(base_url, max_tries, instance_id):
    """Fetch a job (GET) that needs a worker; update status to STARTED"""
    fields_to_update = {
        'status': 'STARTED',
        'start_time': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
        'instance_id': instance_id
    }
    return proccess_job_update(base_url, max_tries, None, fields_to_update)

def update_job_status(base_url, max_tries, job_id, status):
    """Fetch a job (GET) by id; update status to provided value"""
    return proccess_job_update(base_url, max_tries, job_id, {"status":status})

def update_error_message(base_url, max_tries, job_id, error_message):
    """Fetch a job (GET) by id; set status to error and set error message"""
    status = "ERROR"
    error_object = {
        'status':status,
        'error_message': error_message
    }
    return proccess_job_update(base_url, max_tries, job_id, error_object)

def update_job_progress(base_url, max_tries, job_id, block_processed):
    """Fetch a job (GET) by id; update status to provided value"""
    fields_to_update = {
            'status': 'WORKING',
            'last_block_processed': block_processed
    }
    return proccess_job_update(base_url, max_tries, job_id, fields_to_update)

#pylint: disable=too-many-arguments
def set_job_completed(base_url, max_tries, job_id, last_block_processed, end_time, integrity_hash):
    """Fetch a job (GET) by id; update job with completed details"""
    fields_to_update = {
        'status': 'COMPLETE',
        'last_block_processed': last_block_processed,
        'end_time': end_time,
        'actual_integrity_hash': integrity_hash
    }
    return proccess_job_update(base_url, max_tries, job_id, fields_to_update)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='supports 3 operations pop, update-status, update-progress, and complete'
    )
    parser.add_argument('--port',
        type=int, default=4000,
        help='Port for web service, default 4000')
    parser.add_argument('--host',
        type=str, default='127.0.0.1',
        help='Listening service name or ip, default 127.0.0.1')
    parser.add_argument('--max-tries',
        type=int, default=10,
        help='Number of attemps when HTTP call fails, default 10')
    parser.add_argument('--operation',
        type=str,
        help='call to make pop, update-status, update-progress, complete')
    parser.add_argument('--job-id',
        type=int,
        help='id of job to update')
    parser.add_argument('--status',
        type=str,
        help='status to set job')
    parser.add_argument('--instance-id',
        type=str,
        help='aws instance id of host')
    parser.add_argument('--error-message',
        type=str,
        help='error message')
    parser.add_argument('--block-processed',
        type=str,
        help='last block processed')
    parser.add_argument('--end-time',
        type=str,
        help='when job stopped processing')
    parser.add_argument('--integrity-hash',
        type=str,
        help='integrity hash reported after processing completed')
    parser.add_argument('--log',
        type=str,
        help='path to log file to upload')

    args = parser.parse_args()

    # validate argument values
    if args.operation in ['update-status', 'update-error', 'update-progress', 'complete'] and args.job_id is None:
        sys.exit(f"Error job_id must be specifid for operation {args.operation}")
    if args.max_tries < 1:
        sys.exit("Error max-tries must be greater then zero")
    if args.operation == 'complete':
        valid_time = re.search(r"\d+-\d+-\d+T\d+:\d+:\d+",args.end_time)
        if not valid_time:
            sys.exit("Error bad time format, good example 2023-10-13T19:46:45")

    url = f"http://{args.host}:{args.port}"
    # data stucture we will be returning
    job_message = { 'status_code': None,
            'jobid': None,
            'json': None }

    # which operation
    if args.operation == "pop":
        job_message = pop_job(url, args.max_tries, instance_id)
    elif args.operation == "update-status":
        job_message = update_job_status(url,
            args.max_tries,
            args.job_id,
            args.status)
    elif args.operation == "update-error":
        job_message = update_error_message(url,
            args.max_tries,
            args.job_id,
            args.error_message)
    elif args.operation == "update-progress":
        job_message = update_job_progress(url,
            args.max_tries,
            args.job_id,
            args.block_processed)
    elif args.operation == "complete":
        job_message = set_job_completed(url,
            args.max_tries,
            args.job_id,
            args.block_processed,
            args.end_time,
            args.integrity_hash)
    elif args.operation == "wrapper-error-log":
        job_message = upload_error_log(url,
            args.job_id,
            "wrapper",
            args.log)
    elif args.operation == "nodeos-error-log":
        job_message = upload_error_log(url,
            args.job_id,
            "nodeos",
            args.log)
    else:
        sys.exit(f"Error operation {args.operation} not supported see help")

    print (json.dumps(job_message))
