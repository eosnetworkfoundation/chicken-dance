"""Update Configuration by sending POST HTTP Request."""
import json
import argparse
import sys
import time
import requests


def update_by_end_block(base_url, max_tries, end_block_num, integrity_hash, nodeos_version):
    """Update Config Object, only updates by end_block_id"""
    # initialize params
    post_headers = {
        'Content-Type': 'application/json',
    }

    # 100 milisecs double every loop
    backoff = 0.1
    update_complete = False
    # will increate by 1 each loop
    current_try = 0

    # loop getting and setting until success
    # etag is checksum to ensure content has not been updated by another process
    while not update_complete and current_try <= max_tries:
        # first update counter and backoff
        current_try = current_try + 1
        backoff = backoff * 2

        # data stucture we will be returning
        update_job_message = { 'status_code': None,
            'sliceid': None,
            'message': None }

        config = {
            "end_block_num": end_block_num,
            "integrity_hash": integrity_hash,
            "spring_version": nodeos_version
        }

        contents = json.dumps(config)

        # make POST call; json passed in as string
        update_config_response = requests.post(base_url + '/config',
            headers=post_headers,
            timeout=3,
            data=contents.encode('utf-8'))

        # populate data structure
        update_job_message['status_code'] = update_config_response.status_code

        # good job
        if update_config_response.status_code == 200:
            if update_config_response.content is not None:
                config_obj = json.loads(update_config_response.content.decode('utf-8'))
            update_job_message['sliceid'] = config_obj['sliceid']
            update_job_message['message'] = config_obj['message']
            update_complete = True
        # 4xx error means client issue, no retries will fix that, abort
        elif update_config_response.status_code > 399 \
            and update_config_response.status_code < 500:
            print(f"Warning: update job failed with code {update_config_response.status_code}",
                file=sys.stderr)
            break
        # rest and try again, assume this is service side error
        else:
            # we try again pause to avoid collisions
            time.sleep(backoff)

    return update_job_message

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='supports 1 operations update'
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
        type=str, default="update",
        help='command to execute')
    parser.add_argument('--end-block-num',
        type=str,
        help='last block processed')
    parser.add_argument('--integrity-hash',
        type=str,
        help='integrity hash reported after processing completed')
    parser.add_argument('--spring-version',
        type=str,
        help='software version to update')

    args = parser.parse_args()

    # validate argument values
    if args.operation != 'update':
        sys.exit(f"Error invalid operation: {args.operation}")
    if args.operation == 'update' and \
        (args.integrity_hash is None or args.end_block_num is None):
        sys.exit("Must specifify integrity hash and end block num with update operation")
    if args.max_tries < 1:
        sys.exit("Error max-tries must be greater then zero")

    url = f"http://{args.host}:{args.port}"

    # data stucture we will be returning
    job_message = { 'status_code': None,
        'sliceid': None,
        'message': None }

    # updates config using end block as a key
    # spring version is needed to Disambiguate when multiple version 
    #    are used with the same block ranges
    job_message = update_by_end_block(url,
        args.max_tries,
        args.end_block_num,
        args.integrity_hash,
        args.spring_version)

    # nicer print messages
    if job_message['status_code'] == 200:
        print (f"Config Operation {args.operation} Succeeded")
    if job_message['status_code'] > 200 and job_message['status_code'] < 300:
        print (f"Config {args.operation} Succeed. Unexpected status, {job_message['status_code']}")
    if job_message['status_code'] >= 300 and job_message['status_code'] < 400:
        print (f"Config {args.operation} Failed. Unexpected redirection, {job_message['status_code']}, not handled")
    if job_message['status_code'] >= 400:
        if job_message['status_code'] == 404:
            print (
            f"""Config {args.operation} Failed with {job_message['status_code']}, configuration not found.
            Did you try to reference a config that does not exist?"""
            )
        else:
            print (f"Config {args.operation} Failed with {job_message['status_code']}")
