#!/usr/bin/env bash

# launch replay nodes from command line

HOME="/home/ubuntu"
INSTANCE_FILE="${HOME}/aws-replay-instances.txt"
SCRIPTS_DIR="${HOME}/replay-test/scripts"
AWS_REPLAY_TEMPLATE="ChickenReplayHost"
AWS_REPLAY_TEMPLATE_VERSION="13"

source ${HOME}/replay-test/scripts/replayhost/env

NUM_INSTANCES=${1:-1}
DRY_RUN=${2}

if [ -n "$DRY_RUN" ]; then
  DRY_RUN="--dry-run"
else
  DRY_RUN=""
fi

if [ $NUM_INSTANCES -lt 1 ]; then
  echo "Number of replay hosts must be greater then zero"
  exit 127
fi

# modify user data script to stuff in private ip of orchestration server
ORCH_IP=$(sh /home/ubuntu/replay-test/scripts/get_private_ip.sh)
sed "s^# MACRO_P echo \$ORCH_IP^echo $ORCH_IP^" "${SCRIPTS_DIR}/replay-node-bootstrap.sh" > /tmp/replay-node-bootstrap.sh
mv /tmp/replay-node-bootstrap.sh "${SCRIPTS_DIR}/replay-node-bootstrap.sh"

# find the number of zones we can use
NUM_ZONES=0
for _ in $(aws ec2 describe-availability-zones --region ${AWS_REGION} --query 'AvailabilityZones[].ZoneName' --output text)
do
  let NUM_ZONES=NUM_ZONES+1
done
# get the equal number of instances per zone
# intereger math always gets floor
ZONE_NUM_INSTANCES=$((NUM_INSTANCES / NUM_ZONES))
HALF_ZONE_NUM_INSTANCES=$((ZONE_NUM_INSTANCES / 2))

# clear out file
touch /tmp/aws-run-instance-out.json
:> /tmp/aws-run-instance-out.json
for AZ in $(aws ec2 describe-availability-zones --region ${AWS_REGION} --query 'AvailabilityZones[].ZoneName' --output text)
do
  echo "Attempting to allocate ${ZONE_NUM_INSTANCES} in ${AZ}"

  # need the correct subnet for each Availability Zone
  case $AZ in
    "us-east-1a")
      SUBNET=$SUBNET_1A;;
    "us-east-1b")
      SUBNET=$SUBNET_1B;;
    "us-east-1c")
      SUBNET=$SUBNET_1C;;
    "us-east-1d")
      SUBNET=$SUBNET_1D;;
    "us-east-1e")
      SUBNET=$SUBNET_1E;;
    "us-east-1f")
      SUBNET=$SUBNET_1F;;
    *)
      SUBNET=$SUBNET_1F;;
  esac

  cp /tmp/aws-run-instance-out.json /tmp/aws-run-instance-out.json.bak
  aws ec2 run-instances --launch-template LaunchTemplateName=${AWS_REPLAY_TEMPLATE},Version=${AWS_REPLAY_TEMPLATE_VERSION} \
  --placement AvailabilityZone=$AZ \
  --network-interfaces "[{\"DeviceIndex\":0,\"SubnetId\":\"${SUBNET}\",\"AssociatePublicIpAddress\":true,\"Groups\":[\"${SECURITY_GROUP}\"]}]" \
  --user-data file://"${SCRIPTS_DIR}"/replay-node-bootstrap.sh \
  --count $ZONE_NUM_INSTANCES $DRY_RUN >> /tmp/aws-run-instance-out.json

  # if request failed try request again with half as many replay hosts
  # a smaller number might be allocated
  if [ $? -ne 0 ]; then
    cp /tmp/aws-run-instance-out.json.bak /tmp/aws-run-instance-out.json
    echo "Trying again to allocate ${HALF_ZONE_NUM_INSTANCES} in ${AZ}"
    aws ec2 run-instances --launch-template LaunchTemplateName=${AWS_REPLAY_TEMPLATE},Version=${AWS_REPLAY_TEMPLATE_VERSION} \
    --placement AvailabilityZone=$AZ \
    --network-interfaces "[{\"DeviceIndex\":0,\"SubnetId\":\"${SUBNET}\",\"AssociatePublicIpAddress\":true,\"Groups\":[\"${SECURITY_GROUP}\"]}]" \
    --user-data file://"${SCRIPTS_DIR}"/replay-node-bootstrap.sh \
    --count $HALF_ZONE_NUM_INSTANCES $DRY_RUN >> /tmp/aws-run-instance-out.json \
    && echo "Half Allocation Succeeded"
  else
    echo "Full Allocation Succeeded"
    rm /tmp/aws-run-instance-out.json.bak
  fi
done


# append so you can run several times
# terminate will clear out the instance file
grep "InstanceId" /tmp/aws-run-instance-out.json | cut -d':' -f2 | tr -d ' ",' >> "$INSTANCE_FILE"
