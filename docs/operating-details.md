# Operating Details

Outlines the scripts that are called and where data, logs and configuration files live.

## Orchestration

All scripts are under the `ubunutu` user. The `replay-test` github repository is cloned into this directory.
### `Top Level Items`
- /home/ubuntu/orchestration-service/web_service.py : python http application
- /home/ubuntu/replay-test/scripts/replay-host/run-replay-instance.sh : script to spin up replay hosts
- /home/ubuntu/replay-test/scripts/replay-host/terminate-replay-instance.sh : script to terminate existing replay hosts
- /home/ubuntu/orchestration.log : log from orchestration service
- /home/ubuntu/aws-replay-instances.txt : instance id list of aws replay hosts, used by termination script
- /tmp/aws-run-instance-out.json : full json from `aws run-instance` command

### `Additional Items`
- /home/ubuntu/scripts/process_orchestration_log.py : parses log to produce stats on timing

## Replay hosts
All scripts are under the `enf-replay` user. The `replay-test` github repository is cloned into this directory.

### `Top Level Items`
- /home/enf-replay/orchestration-ip.txt : ip address of the orchestration service
- /tmp/replay.lock : lock file with pid of job that created the lock
- /home/enf-replay/replay-test/replay-client/replay_wrapper_script.sh : script the crontjob runs
- /home/enf-replay/replay-test/replay-client/start-nodeos-run-replay.sh : the script running the job
- /home/enf-replay/replay-test/config/*.ini : nodeos configuration files
- /data/nodeos/snapshot : location of snapshot to load
- /data/nodoes/data : data directory for nodeos
- /data/nodeos/log : log director for nodeos
  - end_integrity_hash.txt : final integrity hash
  - nodoes.log : log from syncing runing
  - nodeos-readonly.log : log from readonly spinup of nodoes

### `Additional Items`
  - /home/enf-replay/replay-test/replay-client/background_status_update.sh : background job that send progress updates to orchestration service
  - /home/enf-replay/replay-test/replay-client/config_operations.py : python script to HTTP POST integrity hash updates
  - /home/enf-replay/replay-test/replay-client/create-nodeos-dir-struct.sh : init dir structure
  - /home/enf-replay/replay-test/replay-client/get_integrity_hash_from_log.sh : pull out the integrity hash from nodeos logs
  - /home/enf-replay/replay-test/replay-client/head_block_num_from_log.sh : pull out the most recent block process from nodeos logs
  - /home/enf-replay/replay-test/replay-client/install-nodoes.sh : pull down deb and install locally
  - /home/enf-replay/replay-test/replay-client/job_operations.py : python script to HTTP POST job updates and status changes
  - /home/enf-replay/replay-test/replay-client/manage_blocks_log.sh : script to retrieve blocks.log from cloud storage
  - /home/enf-replay/replay-test/replay-client/parse_json.py : parses JSON to bridge access to JSON from shell scripts
  - /home/enf-replay/replay-test/replay-client/replay-node-cleanup.sh : cleans out previous run, creates a blank slate
