#!/usr/bin/env bash

# kill off instances by ID.
# When ALL provided terminates all instances in the file ~/aws-replay-instances.txt

INSTANCE_FILE="/home/ubuntu/aws-replay-instances.txt"

INSTANCE_ID=${1:ALL}
DRY_RUN=${2}

if [ -n "$DRY_RUN" ]; then
  DRY_RUN="--dry-run"
else
  DRY_RUN="--no-dry-run"
fi
# remove hypens for later string compare
DRY_RUN_CMPT=$(echo $DRY_RUN | tr -d  '-')

# All instances
if [ "$INSTANCE_ID" == "ALL" ]; then
  # on termination remove user provided config 
  rm /var/www/html/usernodeosconfig/user_provided_cmd_line.conf
  # check file exists and has contents
  if [[ -e "$INSTANCE_FILE" && -s "$INSTANCE_FILE" ]]; then
    ALL_INSTANCES=$(paste -s -d ' ' "$INSTANCE_FILE")
    aws ec2 terminate-instances "$DRY_RUN" --instance-ids $ALL_INSTANCES
    # not dry-run remove file
    if [ "$DRY_RUN_CMPT" == "nodryrun" ]; then
      rm "$INSTANCE_FILE"
    fi
  fi
# Single instance
else
  if [ -n "$INSTANCE_ID" ]; then
     aws ec2 terminate-instances "$DRY_RUN" --instance-ids $INSTANCE_ID
  else
    echo "Must provide AWS instance ID or ALL as first arg"
    exit 1
  fi
fi
