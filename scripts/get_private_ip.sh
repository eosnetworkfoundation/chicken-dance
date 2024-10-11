#!/usr/bin/env bash

# run this on orchastor to get local private ip address
IP=$(ip addr show eth0 | grep "inet\b" | awk '{print $2}' | cut -d/ -f1)
echo $IP
