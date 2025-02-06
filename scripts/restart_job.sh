#!/usr/bin/env bash

JOBID=$1
ORCH_IP=${2:-127.0.0.1}
ORCH_PORT=${3:-4000}

if [ -z $JOBID ]; then
  echo "one arg JOBID required"
  exit
fi

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
python3 ${SCRIPT_DIR}/../replay-client/job_operations.py --host ${ORCH_IP} --port ${ORCH_PORT} --operation update-status --status "WAITING_4_WORKER" --job-id ${JOBID}

