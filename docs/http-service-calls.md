# HTTP Service Calls

## Summary
- job - gets/sets configuration data for the replay nodes
- status - gets a replay nodes progress and state
- config - get/sets the configuration data used to initialize the job
- summary - progress of current run and reports any failed jobs
- oauthback - login callback from OAuth provider
- logout
- process - Dynamic HTML for summary page
- grid - Dynamic HTML with grid of jobs
- control - Dynamic HTML with controls to operate replays
- healthcheck - gets 200/0K always

## Job
A GET or POST request with the path `/job`. The `/job` GET request it can take a URL parameter of `nextjob` with no value or a URL parameter of `jobid` with an value.
*Note:* `/job` will return `replay_slice_id`, this value can be used as the `sliceid` parameter for `/status` and `/config` to check status or look up the job's configuration information.

### GET
When `nextjob` parameter is present the web application returns all the information needed to perform the job in the body with a HTTP 200 code.
When the `jobid` parameter is present the web application returns the current status of the job as results in the body with an HTTP 200 code.
When no parameters are provided the web applications issues a 301 redirect to `/job?nextjob`
- If the Accepts header of the GET request is `text/plain; charset=us-ascii` the results are formatted as text string.
- If the Accepts header of the GET request is `application/json` the results are formatted as json.

### POST
The `/job` POST request must have a URL parameter for 'job' with a value.
If no parameter is present a 404 error is returned.
The content-type of the POST request is always `application/json`.
The body of the POST request contains JSON which is parsed into a
dictionary and stored into the memory of the web application.

## Status
`/status` GET requests take zero or one parameter `sliceid`. This allows filtering to a slice.
*Note:* status will return `replay_slice_id`, this value can be used as the `sliceid` parameter for `/status` and `/config`

### GET
For the GET request when parameter `sliceid` is present call return the status for the job handling the give replay slice.
- If the Accepts header is text-html returns html
- If Accepts header is application/json returns json
- If Accepts header is text/plain return a string
For the GET request when there are no parameters return statuses for all jobs. Returning all status respected same accepts encoding an per slice configuration.

## Config
`/config` GET requests take one parameter `sliceid`. The `sliceid` must be specified
`/config` POST requests has no parameters, and has two items in the body `end_block_num` and `integrity_hash`
*Note:* status will return `replay_slice_id`, this value can be used as the `sliceid` parameter for `/status` and `/config`

### GET
For the GET returns the configuration details for the given replay slice.
- If the Accepts header is text-html returns html
- If Accepts header is application/json returns json
For the GET request when there are no parameters return statuses for all jobs. Returning all status respected same accepts encoding an per slice configuration.

### POST
When running replay tests we don't always known the expected integrity hash. For example when state database is updated, which may come as part of an update the leap version. For that reason we take the integrity hash, after loading a snapshot, as the known good integrity hash at that block height. The `/config` POST request used the `end_block_num` in the body to look up the configuration slice. Following that the POST updates the configuration in memory and flushes back to disk. This persists the integrity hash as the known good, and expected value at `end_block_num`.

## UserConfig
`/userconfig` allows custom nodeos options to be passed in chicken dance. 

###POST
POST JSON with one field `userconfigtxt` . This field contains all of the command line options to be passed to nodeos. After successful completion create the following asset `https://example.com/usernodeosconfig/user_provided_cmd_line.conf`

## Clean
Remove config 

### POST
Takes no arguments. Removes user provided nodoes configuration.

## Summary (Progress)

### GET
`/summary` Returns the following
- number of blocks processed
- total number of blocks to process
- jobs completed
- jobs failed
- jobs remaining

In addition, lists the failed jobs with the status, links to job details, and config slice.

Content Type Support.
- If the Accepts header is text-html returns html
- If Accepts header is application/json returns json

## Authentication

There are two request, `/oauthback` and `/logout`.
- `/oauthback` is the call back from the OAuth provider, and it is used to set the authentication cookie. This call performs separate web calls to make sure the user has the correct privileges and may be allowed access.
- `/logout` clears the cookie preventing access to the application.


## Healthcheck
`/healthcheck` Always returns same value used for healthchecks

### GET
Only get request is supported. Always returns body of `OK` with status `200`
- Only returns `text/plain utf-8` encoded content.

## config_file
`/config_file` retrieves list of meta-data the contain the block intervals and configuration information for the jobs

### GET
Only get supported 

## release_versions
`/release_version` gets the list of release from git hub

### GET 
Using the Github API to pull the list of releases. Presented on the control script to pick the release version you want to use for the chicken-dance. 

## restart
`/restart` reloads the jobs and their configuration information into the orchestration service. Called `restart` because it effectively wipes out everything replacing it with new configuration. Perfectly fine and safe to outside of a normal run. 

### PUT /POST
Takes three values 
- `config_file_path`  the path to the configuration file (job info and block intervals)
- `target_version`  release branch or official release version to use
- `forced` force the restart even if running jobs are detected. 

## start
`/start` starts a chicken dance and allocates AWS replay hosts based on the number of jobs. Redirects back to control with error messages 

### GET PUT POST
doesn't check method 

## stop
`/stop` stops a chicken dance terminating the running AWS replay hosts. Redirects back to control with error messages 

### GET PUT POST
doesn't check method 

## repo_branches
`/repo-branches` queries github the first 100 branches . Returns the list of release branches first followed by the other branches.

### GET

## deb_download URL
`/deb_download_url` gets the deb package corresponding to the branch or release. This deb is downloaded and used to extract the nodeos software

### GET



