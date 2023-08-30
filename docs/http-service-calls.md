# HTTP Service Calls

## Summary
- job - gets/sets configuration data for the replay nodes
- status - gets/sets a replay nodes progress and state
- reset - throws away all the status updates and re-initalized jobs data. only impacts web services does not updates replay nodes.
- healthcheck - gets 200/0K always

## Job
A GET or POST request with the path '/job'. The '/job' GET request it can take a URL parameter of 'nextjob' with no value or a URL parameter of 'jobid' with an value.

### GET
When 'nextjob' parameter is present the web application calls jobs.get_next_job() and returns the results in the body with a HTTP 200 code.
When the 'jobid' parameter is present the web application will call jobs.get_job(jobid) and returns the results in the body with an HTTP 200 code.
When no parameters are provided the web applications issues a 301 redirect to '/job?nextjob'
If the content-type of the GET request is 'text/plain; charset=us-ascii' the results are formated as text string.
If the content-type of the GET request is 'application/json' the results are formated as json.

### POST
The '/job' POST request must have a URL parameter for 'job' with a value.
If no parameter is present a 404 error is returned.
The content-type of the POST request is always 'application/json'.
The body of the POST request contains JSON which is parsed into a
dictionary named updated_values and passed to the method 'job.set_job(updated_values)'

## Status
'/status' GET and POST requests take zero or one parameter 'jobid'

### GET
For the GET request when parameter 'jobid' is present call 'jobs.get_job(jobid)'
and return the status for that job. If the if content-type is text-html returns html
if content-type is application/json returns json
if content-type is text/plain return a string
For the GET request when there are no parameters
call 'jobs.get_all()' and return statuses for all jobs.
If content-type is text-html returns html
if content-type is application/json returns json
if content-type is text/plain return a string

### POST 
The POST request '/status' must have a jobid parameter and value.
For the POST request parse the json in the body as a
dictionary and pass the dictionary to 'jobs.set_job(data)'
When the POST request has no URL parameters return 404