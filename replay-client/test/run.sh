#!/usr/bin/env bash

# integration tests start up service
cp ../../meta-data/test-simple-jobs.json ../../meta-data/test-modify-jobs.json

{ python3 ../../orchestration-service/web_service.py --config "../../meta-data/test-modify-jobs.json" --host 127.0.0.1 > /dev/null 2>&1 & }
WEB_SERVICE_PID=$!

# prevent tests from running before web service is up
sleep 1

# now test web service
# pop job make sure id comes back
JOBID=$(python3 ../job_operations.py --host 127.0.0.1 --operation pop | python3 ../parse_json.py job_id )
if [ -z $JOBID ]; then
    echo "Error POP Job Failed"
    # shutdown service
    kill "$WEB_SERVICE_PID"
    exit 1
fi
# check status
COUNT=$(curl -s http://127.0.0.1:4000/job\?jobid\=${JOBID} --connect-timeout 1 | grep STARTED | wc -l)
if [ $COUNT -ne 1 ]; then
    echo "ERROR Job did not have STARTED status"
    # shutdown service
    kill "$WEB_SERVICE_PID"
    exit 1
fi
# check status changed
python3 ../job_operations.py --host 127.0.0.1 --operation update-status --status WORKING --job-id $JOBID
COUNT=$(curl -s http://127.0.0.1:4000/job\?jobid\=${JOBID} | grep WORKING | wc -l)
if [ $COUNT -ne 1 ]; then
    echo "ERROR Job did not have WORKING status"
    # shutdown service
    kill "$WEB_SERVICE_PID"
    exit 1
fi
python3 ../job_operations.py --host 127.0.0.1 --operation update-progress --block-processed 20 --job-id $JOBID
if [ $? -eq 0 ]; then
    echo "JOB OPERATIONS TESTS PASSED"
fi

# run config operation to update integrity hash
python3 ../config_operations.py --host 127.0.0.1 --operation update --end-block-num 324302525 --integrity-hash NANANANANANA

DIFF_CNT=$(diff ../../meta-data/test-simple-jobs.json ../../meta-data/test-modify-jobs.json | grep "^>" | wc -l)
if [ "$DIFF_CNT" -lt 1 ]; then
    echo "ERROR integrity hash in meta-data file was not modified"
    cat ../../meta-data/test-modify-jobs.json
    exit 1
fi
echo "CONFIG OPERATIONS TESTS PASSED"


# shutdown service and cleanup
kill "$WEB_SERVICE_PID"
rm ../../meta-data/test-modify-jobs.json
rm orchestration.log
