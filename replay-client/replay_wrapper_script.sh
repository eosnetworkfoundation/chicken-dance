#!/usr/bin/env bash

# simple wrapper script used by cronjob to run replay
USER="enf-replay"

IP_FILE=/home/"${USER}"/orchestration-ip.txt
if [ ! -f "$IP_FILE" ]; then
  echo "${IP_FILE} does not exist cannot source IP address and cannot connect to orchestration service"
  exit 1
fi
ORCH_IP=$(cat ${IP_FILE})
if [ -z "${ORCH_IP}" ]; then
  echo "no ip address in file, ${IP_FILE} cannot connect to orchestration service"
  exit 1
fi

/home/${USER}/replay-test/replay-client/start-nodeos-run-replay.sh ${ORCH_IP} >> /home/${USER}/last-replay.log 2>&1
