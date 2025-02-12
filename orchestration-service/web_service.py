"""modules needed for web application"""
import argparse
import json
import logging
import sys
import re
import os
import subprocess
from datetime import datetime, timedelta
from urllib.parse import unquote, urlencode
from werkzeug.wrappers import Request, Response
from werkzeug.serving import run_simple
from werkzeug.http import generate_etag
from werkzeug.utils import redirect
from report_templates import ReportTemplate
from replay_configuration import ReplayConfigManager
from replay_configuration import UserConfig
from html_page import HtmlPage
from job_status import JobManager
from job_summary import JobSummary
from env_store import EnvStore
from github_oauth import GitHubOauth
from control_config import ControlConfig
from host_runner import Hosts
from get_artifact_url import ArtifactURL

class WebService:
    """class managing all the web service actions to run jobs
    for the chicken-dance aka replay-test"""
    def __init__(self, jobs_config, datacenter_config):
        """initialize the context for the webservice"""
        self.jobs_config = jobs_config
        # load the configuration
        self.replay_config_manager = ReplayConfigManager(jobs_config)
        # build the JobSummary
        self.jobs = JobManager(self.replay_config_manager)
        # track hosts running jobs
        self.hosts = Hosts(datacenter_config)

    def reset(self,jobs_config, datacenter_config):
        """reset jobs and replay config manager"""
        self.__init__(jobs_config,datacenter_config)

    @Request.application
    # pylint: disable=too-many-return-statements disable=too-many-branches
    # pylint: disable=too-many-statements disable=used-before-assignment
    def application(self, request):
        """
        using werkzeug and python create a web application that supports
        /job
        /status
        /healthcheck
        /process /control /grid
        /login /logout
        /oauthback
        /showlog
        /restart
        /config /userconfig 
        /start
        /stop
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
        #  /oauthback is called before access control is avalible
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
                    result = self.jobs.get_job(request.args.get('jobid')) # pylint: disable=used-before-assignment
                elif 'nextjob' in request.args.keys():
                    result = self.jobs.get_next_job()
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
                    self.jobs.get_job(request.args.get('jobid')).as_dict()).encode("utf-8")
                expected_etag = generate_etag(job_as_str)
                if expected_etag != request_etag:
                    return Response("Invalid ETag", status=400)

                data = request.get_json()
                if not data:
                    return Response("Invalid JSON data", status=400)

                # expects id to exist
                if not 'job_id' in data:
                    data['job_id'] = request.args.get('jobid')

                # log timings for completed jobs if data['status'] == 'COMPLETE':

                # check bool success for set_job to ensure valid data
                if self.jobs.set_job(data):
                    stringified = str(
                        self.jobs.get_job(request.args.get('jobid')).as_dict()
                        ).encode("utf-8")
                    etag_value = generate_etag(stringified)
                    response = Response(
                        json.dumps({"status": "updated"}),
                        content_type='application/json')
                    response.headers['ETag'] = etag_value
                    return response
                return Response("Invalid job JSON data", status=400)

        elif request.path == '/status':
            # update the jobs status
            report_obj = JobSummary.create(self.jobs)
            self.jobs.update_running_status(report_obj['is_running'])
            replay_slice = request.args.get('sliceid')
            results = []

            # Handle URL Parameters
            if request.method == 'GET':
                # if id push one element into an array
                # else return the entire array
                if replay_slice:
                    this_slice = self.jobs.get_by_position(replay_slice)

                    # check if not set and results empty
                    if this_slice is None:
                        return Response("Not found", status=404)
                    # set the slice
                    results.append(this_slice)

                else:
                    for this_slice in self.jobs.get_all().items():
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
                    content = ReportTemplate.status_text_report(results)
                    return Response(content,content_type='text/plain; charset=uft-8')

        elif request.path == '/config':
            slice_id = request.args.get('sliceid')
            this_config = self.replay_config_manager.get(slice_id) # pylint: disable=used-before-assignment

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

                # search for block by end_block_num and by spring_version
                block = self.replay_config_manager.return_record_by_end_block_id(int(data['end_block_num']),data['spring_version'])
                if block is None:
                    return Response(f"Config Record with {data['end_block_num']} Not found", status=404)
                block.expected_integrity_hash = data['integrity_hash']
                self.replay_config_manager.set(block)
                self.replay_config_manager.persist()

                response_message = {
                    'sliceid': block.replay_slice_id,
                    'message': 'updated integrity hash'
                }

                return Response(json.dumps(response_message),content_type='application/json')

        elif request.path == '/userconfig':
            if request.method == 'POST':
                form_data = json.loads(request.get_data())
                logger.debug("in /userconfig with form data %s",form_data['userconfigtxt'])
                user_config = UserConfig(form_data['userconfigtxt'],logger)
                logger.debug("Post User Config")
                user_config_status = user_config.check_status()
                if user_config_status['isok']:
                    return Response('{"status":"OK"}',content_type='application/json')

                if user_config_status['badword'] != '':
                    return Response(
                        f'{{"status":"Denied","badword":"{user_config_status["badword"]}"}}',
                        content_type='application/json',
                        status=400)
            return Response('{"status":"Error","message":"unknown error"}',
                content_type='application/json',
                status=400)

        elif request.path == '/clean':
            if request.method == 'POST':
                user_config = UserConfig('',logger)
                user_config.clean()
                return Response('{"status":"OK"}',content_type='application/json')
            return Response('{"status":"Error","message":"unknown error"}',
                content_type='application/json',
                status=400)

        elif request.path == '/healthcheck':
            return Response('OK',content_type='text/plain; charset=utf-8')

        # pylint: disable=too-many-nested-blocks
        elif request.path == '/restart':
            # form submissions only allow POST
            if request.method in ['POST', 'PUT']:
                body = request.get_data(as_text=True)
                # split by & or new line
                # forms will post as one line sep by &
                # sometimes browsers will post as mutiple lines
                lines = re.split(r'[\n&]', body)
                # parse body to get parameters
                body_parameters = {}
                for line in lines:
                    if '=' in line:
                        key, value = line.split('=', 1)  # Split only at the first '='
                        body_parameters[key.strip()] = value.strip()
                    else:
                        pass  # Handle lines without '='

                # unescape string if it looks like it is escaped
                if 'config_file_path' in body_parameters:
                    # normalize path if URL encoded
                    if '%' in body_parameters['config_file_path']:
                        body_parameters['config_file_path'] = unquote(body_parameters['config_file_path'])
                    # abort if config file does not exist
                    if not os.path.exists(body_parameters['config_file_path']):
                        params = urlencode({"error": f"Configuration file {body_parameters['config_file_path']} does not exist"})
                        if 'application/json' in request.headers.get('Accept'):
                            return Response(params, status=404)
                        return redirect(f"/control?{params}")

                    # update configuration file with new version
                    # either official version number or branch name
                    if 'target_version' in body_parameters:
                        ControlConfig.set_version(body_parameters['target_version'],
                            body_parameters['config_file_path'])
                    if 'target_branch' in body_parameters and 'target_version' not in body_parameters:
                        # check to see if the branch is ok to use
                        # can we find a CI/CD build
                        env_name_values.get('config_dir')
                        [owner,repo] = env_name_values.get('repo').split('/')
                        artifact_dict_response = ArtifactURL.deb_url_by_branch(
                            owner,
                            repo,
                            body_parameters['target_branch'],
                            env_name_values.get('artifact'),
                            env_name_values.get('github_read_token'))
                        if not artifact_dict_response['success']:
                            params = urlencode({
                                "error": "Bad branch, unable to find valid build from CI/CD\n"
                            })
                            if 'application/json' in request.headers.get('Accept'):
                                return Response(params, status=400)
                            return redirect(f"/control?{params}")
                        ControlConfig.set_version(body_parameters['target_branch'],
                            body_parameters['config_file_path'])

                    forced = False
                    if 'forced' in body_parameters \
                        and body_parameters['forced'].lower() in ['true','yes']:
                        forced = True


                    report_obj = JobSummary.create(self.jobs)  # check for job in progress
                    self.jobs.update_running_status(report_obj['is_running'])
                    if report_obj['is_running'] and not forced:
                        params = urlencode({
                            "error": "Jobs not complete requires `force` option"
                        })
                        if 'application/json' in request.headers.get('Accept'):
                            return Response(params, status=400)
                        return redirect(f"/control?{params}")

                    # reset the state using the provided config
                    self.reset(body_parameters['config_file_path'],env_name_values.get('datacenter_config'))
                    # successfully reload configs
                    params = urlencode({
                        "success": "Sucessfully loaded new configuration"
                    })
                    if 'application/json' in request.headers.get('Accept'):
                        return Response(params, status=200)
                    return redirect(f"/control?{params}")

                # no configuration file
                params = urlencode({
                    "error": "Requires config_file_path value in body of post"
                })
                if 'application/json' in request.headers.get('Accept'):
                    return Response(params, status=400)
                return redirect(f"/control?{params}")

            # not supported request.method in ['GET','DELETE']
            return Response("method not supported", status=405)

        elif request.path == '/release_versions':
            if request.method == 'GET':
                [owner,repo] = env_name_values.get('repo').split('/')
                versions = ControlConfig.get_versions(owner,repo)
                return Response(json.dumps(versions), content_type='application/json')

            # not supported request.method in ['POST','PUT','DELETE']
            return Response("method not supported", status=405)

        elif request.path == '/repo_branches':
            if request.method == 'GET':
                [owner,repo] = env_name_values.get('repo').split('/')
                branches = ControlConfig.get_branches(owner,repo)
                return Response(json.dumps(branches), content_type='application/json')

            # not supported request.method in ['POST','PUT','DELETE']
            return Response("method not supported", status=405)

        elif request.path == '/config_files':
            if request.method == 'GET':
                config_dir = env_name_values.get('config_dir')
                config_files = ControlConfig.config_files(config_dir)
                return Response(json.dumps(config_files), content_type='application/json')

            # not supported request.method in ['POST','PUT','DELETE']
            return Response("method not supported", status=405)

        elif request.path == '/deb_download_url':
            if request.method == 'GET':
                branch = request.args.get('branch')
                if not branch:
                    return Response("no branch argument provided", status=400)

                env_name_values.get('config_dir')
                [owner,repo] = env_name_values.get('repo').split('/')
                artifact_dict_response = ArtifactURL.deb_url_by_branch(
                    owner,
                    repo,
                    branch,
                    env_name_values.get('artifact'),
                    env_name_values.get('github_read_token'))

                return Response(json.dumps(artifact_dict_response), content_type='application/json')

            # not supported request.method in ['POST','PUT','DELETE']
            return Response("method not supported", status=405)

        elif request.path == '/summary':
            report_obj = JobSummary.create(self.jobs)
            if self.hosts.host_count:
                report_obj['host_count'] = self.hosts.host_count
            else:
                report_obj['host_count'] = 0
            self.jobs.update_running_status(report_obj['is_running'])

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

        elif request.path in ['/progress', '/grid', '/control', '/detail', '/showlog']:
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
                + HtmlPage.profile_top_bar_html(login, avatar_url) \
                + html_factory.contents('navbar.html') \
                + html_factory.contents(request.path) \
                + html_factory.contents('footer.html')
            else:
                html_content = html_factory.contents('header.html') \
                + HtmlPage.default_top_bar_html(\
                    GitHubOauth.assemble_oauth_url(referring_url, env_name_values)\
                ) \
                + HtmlPage.not_authorized() \
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
                    + HtmlPage.profile_top_bar_html(login, avatar_url) \
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
            + HtmlPage.default_top_bar_html(GitHubOauth.assemble_oauth_url(referral_path, env_name_values)) \
            + HtmlPage.not_authorized("Auth Failed Could Not Retreive Access Token: Try Again") \
            + html_factory.contents('footer.html')
            return Response(no_token_html, status=403, content_type='text/html')

        elif request.path == '/start':
            if self.jobs.is_running:
                params = urlencode({
                    "error": "Jobs Already In Progress can not start\n"
                })
                if 'application/json' in request.headers.get('Accept'):
                    return Response(params, status=400)
                return redirect(f"/control?{params}")

            # Path to the shell script
            script_dir = env_name_values.get('script_dir')
            script_path = f"{script_dir}/replayhost/run-replay-instance.sh"
            # divide jobs by 5 return a whole number max 120 min of 5
            workers = max(5, min(120, len(self.jobs) // 5))
            # Execute the shell script
            result = subprocess.run([script_path, str(workers)],
                shell=False,
                check=False,
                capture_output=True,
                text=True)
            if result.returncode == 0:
                # set number of hosts allocated
                self.hosts.set_count(workers)
                params = urlencode({
                    "success": f"Successfully Allocated {workers} Hosts"
                })
                if 'application/json' in request.headers.get('Accept'):
                    return Response(params, status=200)
                return redirect(f"/control?{params}")

            params = urlencode({
                "error": f"Error: {result.stderr}"
            })
            if 'application/json' in request.headers.get('Accept'):
                return Response(params, status=500)
            return redirect(f"/control?{params}")

        elif request.path == '/stop':
            if not self.hosts.has_hosts():
                params = urlencode({
                    "error": "No jobs running can not stop\n"
                })
                if 'application/json' in request.headers.get('Accept'):
                    return Response(params, status=400)
                return redirect(f"/control?{params}")

            # Path to the shell script
            script_dir = env_name_values.get('script_dir')
            script_path = f"{script_dir}/replayhost/terminate-replay-instance.sh"
            workers = "ALL"
            # Execute the shell script
            result = subprocess.run([script_path, workers],
                shell=False,
                check=False,
                capture_output=True,
                text=True)
            if result.returncode == 0:
                # set number of hosts allocated
                self.hosts.set_count(0)
                params = urlencode({
                    "success": "Sucessfully Shutdown Hosts"
                })
                if 'application/json' in request.headers.get('Accept'):
                    return Response(params, status=200)
                return redirect(f"/control?{params}")

            params = urlencode({
                "error": result.stderr
            })
            if 'application/json' in request.headers.get('Accept'):
                return Response(params, status=500)
            return redirect(f"/control?{params}")

        return Response("Not found", status=404)

if __name__ == '__main__':
    # env holds oauth, location of config files, and github repos
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

    # initialize
    app = WebService(args.config,env_name_values.get('datacenter_config'))
    # run web service
    run_simple(args.host, args.port, app.application)
