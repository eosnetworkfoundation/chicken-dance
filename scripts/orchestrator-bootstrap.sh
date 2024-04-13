#!/usr/bin/env bash

USER=ubuntu

## addition ssh keys ##
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHUWNQ0UISbfmtQFdkwws25WfdOSITAVoxfXF0rD/Djv eric.passmore@eosnetwork.com - superbee.local" \
  | sudo -u "${USER}" tee -a /home/${USER}/.ssh/authorized_keys
echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEhjX5L263F2nMkkEp6HuqD+JUL9orBwkQg7tYvux8tU zach.butler@eosnetwork.com (nu-scorpii)' \
  | sudo -u "${USER}" tee -a /home/${USER}/.ssh/authorized_keys

## packages ##
apt-get update >> /dev/null
apt-get install -y git unzip jq curl nginx python3 python3-pip

## aws cli ##
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "/tmp/awscliv2.zip"
unzip /tmp/awscliv2.zip -d /tmp/ >> /dev/null
/tmp/aws/install
rm -rf /tmp/aws /tmp/awscliv2.zip

## git scripts for enf-user ##
sudo -i -u "${USER}" git clone https://github.com/eosnetworkfoundation/replay-test
sudo -i -u "${USER}" pip install datetime argparse werkzeug bs4 numpy

## config nginx proxy ##
cp /home/"${USER}"/replay-test/config/nginx-replay-test.conf /etc/nginx/sites-available/
rm /etc/nginx/sites-enabled/default
ln -s /etc/nginx/sites-available/nginx-replay-test.conf /etc/nginx/sites-enabled/default
# copy in html, css, js, images
cp -r /home/"${USER}"/replay-test/webcontent/* /var/www/html/
systemctl reload nginx

# copy the default env so the system will start
if [ ! -s /home/"${USER}"/env ]; then
  cp /home/"${USER}"/replay-test/env.default /home/"${USER}"/env
fi

## startup service in background ##
sudo -i -u "${USER}" python3 /home/"${USER}"/replay-test/orchestration-service/web_service.py \
    --config /home/"${USER}"/replay-test/meta-data/full-production-run-20240101.json \
    --host 0.0.0.0 \
    --log /home/"${USER}"/orch-complete-timings.log &
