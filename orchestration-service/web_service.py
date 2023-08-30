"""modules needed for web application"""
import argparse
import json
import sys
from werkzeug.wrappers import Request, Response
from werkzeug.serving import run_simple
from report_templates import ReportTemplate
from replay_configuration import ReplayConfigManager
from job_status import JobManager

@Request.application
# pylint: disable=too-many-return-statements disable=too-many-branches
def application(request):
    """
    using werkzeug and python create a web application that supports
    /job
    /status
    /restart
    /healthcheck
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
    print (f"""\nSTART: Request Path {request.path}
    Method {request.method}
    Params {request.args.keys()}
    Content Type {request.headers.get('Content-Type')}
    Accept  {request.headers.get('Accept')}""")
    if request.path == '/job':
        # capture Accept Header
        request_accept_type = request.headers.get('Accept')

        # Work through GET Requests first
        if request.method == 'GET':
            jobid = request.args.get('jobid')

            # Handle URL Parameters
            if jobid is not None:
                result = jobs.get_job(jobid)
            elif 'nextjob' in request.args.keys():
                result = jobs.get_next_job()
            else:
                return Response("", status=301, headers={"Location": "/job?nextjob"})

            # Check we have a legit value
            if result is None:
                return Response("Could not find job", status=404)

            # Format based on content type
            # content type is None when no content-type passed in
            # redirect strips content type
            # DEFAULT and PLAIN TEXT
            if ('text/plain; charset=utf-8' in request_accept_type or
                'text/plain' in request_accept_type or
                '*/*' in request_accept_type or
                request_accept_type is None):
                return Response(str(result), content_type='text/plain; charset=utf-8')
            # JSON
            if 'application/json' in request_accept_type:
                return Response(json.dumps(result.as_dict()), content_type='application/json')

        # Work through POST Requests
        elif request.method == 'POST':

            # must have jobid parameter
            jobid = request.args.get('jobid')
            if not jobid:
                return Response("jobid parameter is missing", status=404)

            data = request.get_json()
            if not data:
                return Response("Invalid JSON data", status=400)

            # expects id to exist
            if not 'job_id' in data:
                data['job_id'] = jobid
            # check bool success for set_job to ensure valid data
            if jobs.set_job(data):
                return Response(json.dumps({"status": "updated"}), content_type='application/json')
            return Response("Invalid job JSON data", status=400)

    elif request.path == '/status':
        # Capture the Accept Type
        request_accept_type = request.headers.get('Accept')
        replay_slice = request.args.get('pos')
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
            if 'text/html' in request_accept_type:
                # Converting to simple HTML representation (adjust as needed)
                content = ReportTemplate.status_html_report(results)
                return Response(content, content_type='text/html')
            # JSON
            if 'application/json' in request_accept_type:
                # Converting from object to dictionarys to dump json
                results_as_dict = [obj.as_dict() for obj in results]
                return Response(json.dumps(results_as_dict),content_type='application/json')
            # DEFAULT and PLAIN TEXT
            if ('text/plain; charset=utf-8' in request_accept_type or
                'text/plain' in request_accept_type or
                '*/*' in request_accept_type or
                request_accept_type is None):
                # Converting to simple Text format
                content = ReportTemplate.status_html_report(results)
                return Response(content,content_type='text/plain; charset=uft-8')

    return Response("Not found", status=404)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Orchestration Service \
to manage tests to replay on the antelope blockchain')
    parser.add_argument('--config', '-c', type=str, help='Path to config json')
    parser.add_argument('--port', type=int, default=4000, help='Port for web service')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Listening service name or ip')

    args = parser.parse_args()

    # remove this if Local config works
    if args.config is None:
        sys.exit("Must provide config with --config option")
    replay_config_manager = ReplayConfigManager(args.config)
    jobs = JobManager(replay_config_manager)
    run_simple(args.host, args.port, application)

# POST with jobid parses body and updates  status for that job
# POST with no jobid return 404 error
# /reset POST with bearer token
# POST parses body to get bearer_token. If bearer_token matches sets all jobs to status "terminated"
# /healthcheck
# GET request always returns 200 OK
