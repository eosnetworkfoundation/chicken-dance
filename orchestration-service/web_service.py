"""modules needed for web application"""
import argparse
import json
import logging
import sys
import re
from datetime import datetime, timedelta
from werkzeug.wrappers import Request, Response
from werkzeug.serving import run_simple
from werkzeug.http import generate_etag
from werkzeug.utils import redirect
from report_templates import ReportTemplate
from replay_configuration import ReplayConfigManager
from html_page import HtmlPage
from job_status import JobManager
from job_summary import JobSummary
from env_store import EnvStore
from github_oauth import GitHubOauth

@Request.application
# pylint: disable=too-many-return-statements disable=too-many-branches
# pylint: disable=too-many-statements disable=used-before-assignment
def application(request):
    """
    using werkzeug and python create a web application that supports
    /job
    /status
    /healthcheck
    /process /control /grid
    /login /logout
    /oauthback
    """

    # /job GET request
    # two params nextjob with no values or jobid with a value
    # when no params redirect to /job?nextjob
    #
    # nextjob get the next job ready for work, idle replay node would pick this up
    # jobid get the configuration for a job
    #
    # how the results are reported depends on content-type passed in
    # results could come page as text or json
    print (f"""\nSTART:
    Request URL {request.base_url}
    Request Path {request.path}
    Method {request.method}
    Params {request.args.keys()}
    Content Type {request.headers.get('Content-Type')}
    Accept  {request.headers.get('Accept')}
    ETag {request.headers.get('ETag')}""")

    # auth check /progress /grid /control /detail are HTML pages
    # /healthcheck does not require acess control
    # /oauthback is called before access control is avalible
    # API calls can only go to port 4000 and are secured by a firewall.
    #    We allow all calls going to port 4000 as those made it past firewalls
    #    Pattern matches IPv4 addresses only
    pattern = r'^http[s]*://\d+\.\d+\.\d+\.\d+:(\d+)/[a-zA-Z0-9_-]+'
    auth_match = re.match(pattern, request.base_url)

    if request.path not in ['/progress', '/grid', '/control', '/detail', '/healthcheck', '/oauthback'] and \
        not (auth_match and auth_match.group(1) == "4000") and \
        not (ALWAYS_ALLOW or GitHubOauth.is_authorized(request.cookies,
            request.headers.get('Authorization'),
            env_name_values.get('user_info_url'),
            env_name_values.get('team'))):
        return Response("Not Authorized", status=403)

    if request.path == '/job':
        # Work through GET Requests first
        if request.method == 'GET':

            # Handle URL Parameters
            if request.args.get('jobid') is not None:
                result = jobs.get_job(request.args.get('jobid')) # pylint: disable=used-before-assignment
            elif 'nextjob' in request.args.keys():
                result = jobs.get_next_job()
            else:
                return Response("", status=301, headers={"Location": "/job?nextjob"})

            # Check we have a legit value
            if result is None:
                return Response("Could not find job", status=404)

            etag_value = generate_etag(str(result.as_dict()).encode("utf-8"))

            # Format based on content type
            # content type is None when no content-type passed in
            # redirect strips content type
            # DEFAULT and PLAIN TEXT
            if ('text/plain; charset=utf-8' in request.headers.get('Accept') or
                'text/plain' in request.headers.get('Accept') or
                '*/*' in request.headers.get('Accept') or
                request.headers.get('Accept') is None):
                response = Response(str(result), content_type='text/plain; charset=utf-8')
                response.headers['ETag'] = etag_value
                return response
            # JSON
            if 'application/json' in request.headers.get('Accept'):
                response = Response(json.dumps(result.as_dict()), content_type='application/json')
                response.headers['ETag'] = etag_value
                return response

        # Work through POST Requests
        elif request.method == 'POST':
            request_etag = request.headers.get('ETag')

            # must have jobid parameter
            if not request.args.get('jobid'):
                return Response('jobid parameter is missing', status=404)
            # validate etags to avoid race conditions
            job_as_str = str(
                jobs.get_job(request.args.get('jobid')).as_dict()
                ).encode("utf-8")
            expected_etag = generate_etag(job_as_str)
            if expected_etag != request_etag:
                return Response("Invalid ETag", status=400)

            data = request.get_json()
            if not data:
                return Response("Invalid JSON data", status=400)

            # expects id to exist
            if not 'job_id' in data:
                data['job_id'] = request.args.get('jobid')

            # log timings for completed jobs
            if data['status'] == 'COMPLETE':
                # pylint: disable=used-before-assignment
                logger.info("Completed Job, starttime: %s, endtime: %s,\
 jobid: %s, config: %s, snapshot: %s",
                    data['start_time'], data['end_time'],
                    data['job_id'], data['replay_slice_id'], data['snapshot_path'])
            # check bool success for set_job to ensure valid data
            if jobs.set_job(data):
                stringified = str(
                    jobs.get_job(request.args.get('jobid')).as_dict()
                    ).encode("utf-8")
                etag_value = generate_etag(stringified)
                response = Response(
                    json.dumps({"status": "updated"}),
                    content_type='application/json')
                response.headers['ETag'] = etag_value
                return response
            return Response("Invalid job JSON data", status=400)

    elif request.path == '/status':
        replay_slice = request.args.get('sliceid')
        results = []

        # Handle URL Parameters
        if request.method == 'GET':
            # if id push one element into an array
            # else return the entire array
            if replay_slice:
                this_slice = jobs.get_by_position(replay_slice)

                # check if not set and results empty
                if this_slice is None:
                    return Response("Not found", status=404)
                # set the slice
                results.append(this_slice)

            else:
                for this_slice in jobs.get_all().items():
                    results.append(this_slice[1])

            # Format based on content type
            # content type is None when no content-type passed in
            # redirect strips content type
            # HTML
            if 'text/html' in request.headers.get('Accept'):
                # Converting to simple HTML representation (adjust as needed)
                content = ReportTemplate.status_html_report(results)
                return Response(content, content_type='text/html')
            # JSON
            if 'application/json' in request.headers.get('Accept'):
                # Converting from object to dictionarys to dump json
                results_as_dict = [obj.as_dict() for obj in results]
                return Response(json.dumps(results_as_dict),content_type='application/json')
            # DEFAULT and PLAIN TEXT
            if ('text/plain; charset=utf-8' in request.headers.get('Accept') or
                'text/plain' in request.headers.get('Accept') or
                '*/*' in request.headers.get('Accept') or
                request.headers.get('Accept') is None):
                # Converting to simple Text format
                content = ReportTemplate.status_html_report(results)
                return Response(content,content_type='text/plain; charset=uft-8')

    elif request.path == '/config':
        slice_id = request.args.get('sliceid')
        this_config = replay_config_manager.get(slice_id) # pylint: disable=used-before-assignment

        # only GET with param
        if request.method == 'GET' and slice_id is not None:
            # Format based on content type
            # content type is None when no content-type passed in
            # redirect strips content type
            # HTML
            if 'text/html' in request.headers.get('Accept'):
                # Converting to simple HTML representation (adjust as needed)
                content = ReportTemplate.config_html_report(this_config)
                return Response(content, content_type='text/html')
            # JSON
            if ('application/json' in request.headers.get('Accept') or
                '*/*' in request.headers.get('Accept') or
                request.headers.get('Accept') is None):
                # Converting from object to dictionarys to dump json
                results_as_dict = this_config.as_dict()
                return Response(json.dumps(results_as_dict),content_type='application/json')

        elif request.method == 'POST':
            # posted json body end_block_id and integrity_hash
            # return sliceid and message
            data = request.get_json()
            if not data:
                return Response("Invalid JSON data", status=400)

            block = replay_config_manager.return_record_by_end_block_id(int(data['end_block_num']))
            if block is None:
                return Response(f"Config Record with {data['end_block_num']} Not found", status=404)
            block.expected_integrity_hash = data['integrity_hash']
            replay_config_manager.set(block)
            replay_config_manager.persist()

            response_message = {
                'sliceid': block.replay_slice_id,
                'message': 'updated integrity hash'
            }

            return Response(json.dumps(response_message),content_type='application/json')

    elif request.path == '/healthcheck':
        return Response("OK",content_type='text/plain; charset=uft-8')

    elif request.path == '/summary':
        report_obj = JobSummary.create(jobs)
        # Format based on content type
        # content type is None when no content-type passed in
        # HTML
        if 'text/html' in request.headers.get('Accept'):
            # Converting to simple HTML representation (adjust as needed)
            return Response(ReportTemplate.summary_html_report(report_obj), \
                content_type='text/html')
        # JSON
        if 'application/json' in request.headers.get('Accept'):
            return Response(json.dumps(report_obj),content_type='application/json')
        # DEFAULT and PLAIN TEXT
        if ('text/plain; charset=utf-8' in request.headers.get('Accept') or
            'text/plain' in request.headers.get('Accept') or
            '*/*' in request.headers.get('Accept') or
            request.headers.get('Accept') is None):
            # Converting to simple Text format
            return Response(ReportTemplate.summary_text_report(report_obj), \
                content_type='text/plain; charset=uft-8')

    elif request.path == '/logout':
        response = redirect('/progress')
        response.delete_cookie('replay_auth')
        return response

    elif request.path in ['/progress', '/grid', '/control', '/detail']:
        # save the referer passed back in /oauthback
        # quote url encodes string
        referring_url = request.path

        if ALWAYS_ALLOW or \
            GitHubOauth.is_authorized(request.cookies,
            request.headers.get('Authorization'),
            env_name_values.get('user_info_url'),
            env_name_values.get('team')):
            # Retrieve the auth cookie
            cookie_value = request.cookies.get('replay_auth')
            login, avatar_url = GitHubOauth.str_to_public_profile(cookie_value)
            html_content = html_factory.contents('header.html') \
            + html_factory.profile_top_bar_html(login, avatar_url) \
            + html_factory.contents('navbar.html') \
            + html_factory.contents(request.path) \
            + html_factory.contents('footer.html')
        else:
            html_content = html_factory.contents('header.html') \
            + html_factory.default_top_bar_html(\
                GitHubOauth.assemble_oauth_url(referring_url, env_name_values)\
            ) \
            + html_factory.not_authorized() \
            + html_factory.contents('footer.html')

        return Response(html_content, content_type='text/html')

    elif request.path == '/oauthback':
        # this is where we do the login
        # state passed from the user, just the path to return to
        referral_path = request.args.get('state')

        # build request to get access token from code
        code = request.args.get('code')

        # hold token for very short time
        bearer_token = GitHubOauth.get_oauth_access_token(code, env_name_values)
        if bearer_token:
            profile_data = GitHubOauth.create_auth_string(bearer_token, env_name_values.get('user_info_url'))
            login, avatar_url = GitHubOauth.str_to_public_profile(profile_data)
            is_authorized_member = GitHubOauth.check_membership(bearer_token,
                login,
                env_name_values.get('team'))
            # wipe out token after getting profile data, and checking authorization
            bearer_token = None
            if is_authorized_member:
                # Calculate the expiration time, 1 week (7 days) from now
                expires = datetime.utcnow() + timedelta(days=7)

                html_content = html_factory.contents('header.html') \
                + html_factory.profile_top_bar_html(login, avatar_url) \
                + html_factory.contents('navbar.html') \
                + html_factory.contents(referral_path) \
                + html_factory.contents('footer.html')

                response = Response(html_content, content_type='text/html')

                # Build an html page using the referal path
                # Set an HTTP cookie with the expiration time, with highest security
                # Return response
                response.set_cookie('replay_auth',
                    profile_data,
                    expires=expires,
                    secure=True,
                    httponly=True,
                    samesite='Strict')
                return response

        # failed to get access token
        no_token_html = html_factory.contents('header.html') \
        + html_factory.default_top_bar_html(GitHubOauth.assemble_oauth_url(referral_path, env_name_values)) \
        + html_factory.not_authorized("Auth Failed Could Not Retreive Access Token: Try Again") \
        + html_factory.contents('footer.html')
        return Response(no_token_html, status=403, content_type='text/html')

    return Response("Not found", status=404)

if __name__ == '__main__':
    # env is only intended to hold oauth client, secret, and urls
    env_name_values = EnvStore('env')

    parser = argparse.ArgumentParser(
        description='Orchestration Service to manage tests to replay on the antelope blockchain'
    )
    parser.add_argument('--config', '-c', type=str, help='Path to config json')
    parser.add_argument('--port', type=int, default=4000, help='Port for web service')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Listening service name or ip')
    parser.add_argument('--html-dir', type=str, default='/var/www/html/',
        help='path to static html files')
    parser.add_argument('--log', type=str, default="orchestration.log",
        help="log file for service")
    parser.add_argument('--disable-auth', action='store_true',
        help="when set disables access control, used for testing")

    args = parser.parse_args()
    ALWAYS_ALLOW = args.disable_auth

    # setup logging
    logging.basicConfig(filename=args.log,
            encoding='utf-8',
            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
            datefmt='%H:%M:%S',
            level=logging.DEBUG)
    logging.info("Orchestration Web Service Starting Up")
    logger = logging.getLogger('OrchWebSrv')

    html_factory = HtmlPage(args.html_dir)

    # remove this if Local config works
    if args.config is None:
        sys.exit("Must provide config with --config option")
    replay_config_manager = ReplayConfigManager(args.config)
    jobs = JobManager(replay_config_manager)
    run_simple(args.host, args.port, application)
