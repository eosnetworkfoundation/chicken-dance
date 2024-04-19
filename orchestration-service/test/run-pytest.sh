#!/usr/bin/env bash

export PYTHONPATH=..:meta-data:orchestration-service:orchestration-service/test:$PYTHONPATH
# copy in env file for testing purposes
cp -f ../../env.development env
# setup test file for persistance testing
cp ../../meta-data/test-simple-jobs.json ../../meta-data/test-modify-jobs.json
pytest test_summary_report.py
pytest test_replay_configuration.py
pytest test_jobs_class.py
# dump and remove file used for persistance testing
DIFF_CNT=$(diff ../../meta-data/test-simple-jobs.json ../../meta-data/test-modify-jobs.json | grep "^>" | wc -l)
if [ "$DIFF_CNT" -lt 1 ]; then
  echo "ERROR first pass meta-data File was not modified"
  cat ../../meta-data/test-modify-jobs.json
  exit 1
fi
if [ "$DIFF_CNT" -gt 15 ]; then
  echo "Meta-data file was not updated correctly, in first test pass"
  cat ../../meta-data/text-modify-jobs.json
  exit 1
fi
rm ../../meta-data/test-modify-jobs.json

cp ../../meta-data/test-simple-jobs.json ../../meta-data/test-modify-jobs.json
# make client calls to web service with access control diabled
{ python3 ../web_service.py --config "../../meta-data/test-modify-jobs.json" --host 127.0.0.1 --html-dir "../../webcontent/" --disable-auth > /dev/null 2>&1 & }
WEB_SERVICE_PID=$!
# prevent tests running before service is up
sleep 1

# now test web service
pytest test_web_service.py

sleep 1

DIFF_CNT=$(diff ../../meta-data/test-simple-jobs.json ../../meta-data/test-modify-jobs.json | grep "^>" | wc -l)
if [ "$DIFF_CNT" -lt 1 ]; then
  echo "ERROR second pass meta-data File was not modified"
  cat ../../meta-data/test-modify-jobs.json
  exit 1
fi

# shutdown and cleanup
kill "$WEB_SERVICE_PID"
rm ../../meta-data/test-modify-jobs.json

cp ../../meta-data/test-simple-jobs.json ../../meta-data/test-modify-jobs.json
# test access control, all web calls should fail with 403
{ python3 ../web_service.py --config "../../meta-data/test-modify-jobs.json" --host 127.0.0.1 --html-dir "../../webcontent/" > /dev/null 2>&1 & }
WEB_SERVICE_PID=$!
# prevent tests running before service is up
sleep 1

# now test web service
pytest test_no_auth_api.py

sleep 1

DIFF_CNT=$(diff ../../meta-data/test-simple-jobs.json ../../meta-data/test-modify-jobs.json | grep "^>" | wc -l)
if [ "$DIFF_CNT" -ne 0 ]; then
  echo "ERROR meta-data modified during auth check expected no changes"
  exit 1
fi

# shutdown service clean up file
kill "$WEB_SERVICE_PID"
rm ../../meta-data/test-modify-jobs.json
rm orchestration.log
rm ./env
