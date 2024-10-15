#!/usr/bin/env bash

USER=ubuntu

## addition ssh keys ##
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHUWNQ0UISbfmtQFdkwws25WfdOSITAVoxfXF0rD/Djv eric.passmore@eosnetwork.com - superbee.local" \
  | sudo -u "${USER}" tee -a /home/${USER}/.ssh/authorized_keys
echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEhjX5L263F2nMkkEp6HuqD+JUL9orBwkQg7tYvux8tU zach.butler@eosnetwork.com (nu-scorpii)' \
  | sudo -u "${USER}" tee -a /home/${USER}/.ssh/authorized_keys

## packages ##
apt-get update >> /dev/null
apt-get install -y git unzip jq curl python3 python3-pip build-essential libpcre3 libpcre3-dev zlib1g zlib1g-dev libssl-dev

## aws cli ##
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "/tmp/awscliv2.zip"
unzip /tmp/awscliv2.zip -d /tmp/ >> /dev/null
/tmp/aws/install
rm -rf /tmp/aws /tmp/awscliv2.zip

## git scripts for enf-user ##
sudo -i -u "${USER}" git clone https://github.com/eosnetworkfoundation/replay-test
sudo -i -u "${USER}" pip install datetime argparse werkzeug bs4 numpy

## download nginx with lau script mod ##
NGINX_VERSION=1.27.2
curl -L http://nginx.org/download/nginx-${NGINX_VERSION}.tar.gz --output /tmp/nginx-${NGINX_VERSION}.tar.gz >> /dev/null
tar -xzvf /tmp/nginx-${NGINX_VERSION}.tar.gz -C /tmp >> /dev/null
git clone https://github.com/openresty/lua-nginx-module /tmp/lua-nginx-module >> /dev/null
# lua mod needs lua jit
git clone https://luajit.org/git/luajit.git /tmp/luajit
cd /tmp/luajit || exit
make && make install >> /dev/null
# set env for LUA
export LUAJIT_LIB=/usr/local/lib
export LUAJIT_INC=/usr/local/include/luajit-2.1

for file in .profile .bashrc
do
  if [ -s /home/${USER}/${file} ]; then
    echo "export LUAJIT_LIB=/usr/local/lib" >> /home/${USER}/${file}
    echo "export LUAJIT_INC=/usr/local/include/luajit-2.1" >> /home/${USER}/${file}
  fi
done

# compile NGINX
cd /tmp/nginx-${NGINX_VERSION} || exit
./configure --with-http_ssl_module --with-ld-opt="-Wl,-rpath,$LUAJIT_LIB" --add-module=/tmp/lua-nginx-module
make && make install >> /dev/null
CHECK_LUA=$(/usr/local/nginx/sbin/nginx -V 2>&1 | grep lua | wc -l)
if [ $CHECK_LUA -lt 1 ]; then
  echo "error LAU Module not enabled with NGINX"
fi
# lau mod requires lua-resty-core and lua-restylrucache
git clone https://github.com/openresty/lua-resty-core /tmp/lua-resty-core
cd /tmp/lua-resty-core || exit
make install PREFIX=/usr/local/nginx/ LUA_LIB_DIR=/usr/local/share/lua/5.1
git clone https://github.com/openresty/lua-resty-lrucache /tmp/lua-resty-lrucache
cd /tmp/lua-resty-lrucache || exit
make install PREFIX=/usr/local/nginx/ LUA_LIB_DIR=/usr/local/share/lua/5.1
# put this in nginx http section
# lua_package_path "/usr/local/share/lua/5.1/lualib/?.lua;;";
cd /home/"${USER}" || exit
# clean up
rm -f /tmp/nginx-${NGINX_VERSION}.tar.gz
rm -rf /tmp/nginx-${NGINX_VERSION} /tmp/luajit /tmp/lua-nginx-module

## config nginx proxy ##
[ ! -d /etc/nginx ] && mkdir /etc/nginx && chmod 755 /etc/nginx
cp /home/"${USER}"/replay-test/config/nginx.conf /etc/nginx/nginx.conf
cp /home/"${USER}"/replay-test/config/vhost-replay-test.conf /etc/nginx/sites-available/
rm /etc/nginx/sites-enabled/default
ln -s /etc/nginx/sites-available/vhost-replay-test.conf /etc/nginx/sites-enabled/default
# copy in html, css, js, images
cp -r /home/"${USER}"/replay-test/webcontent/* /var/www/html/
[ ! -d /var/log/jobfiles ] && mkdir -p /var/log/jobfiles
chmod 777 /var/log/jobfiles
/usr/local/nginx/sbin/nginx -c /etc/nginx/nginx.conf -g 'daemon on; master_process on;'
# add nginx alias
for file in .profile .bashrc
do
  if [ -s /home/${USER}/${file} ]; then
    echo 'alias nginx="/usr/local/nginx/sbin/nginx -c /etc/nginx/nginx.conf"' >> /home/${USER}/${file}
    echo 'alias killnginx="sudo pkill -u root nginx -P 1 --signal 15"' >> /home/${USER}/${file}
    echo 'alias startnginx="sudo /usr/local/nginx/sbin/nginx -c /etc/nginx/nginx.conf -g \"daemon on; master_process on;\""'  >> /home/${USER}/${file}
  fi
done


# copy the default env so the system will start
if [ ! -s /home/"${USER}"/env ]; then
  cp /home/"${USER}"/replay-test/env.default /home/"${USER}"/env
fi

## startup service in background ##
sudo -i -u "${USER}" python3 /home/"${USER}"/replay-test/orchestration-service/web_service.py \
    --config /home/"${USER}"/replay-test/meta-data/full-production-run-20240101.json \
    --host 0.0.0.0 \
    --log /home/"${USER}"/orch-complete-timings.log &

## add cron to prune job logs
echo "0 4 * * * find /var/log/jobfiles/ -type f -mtime +3 -exec rm -f {} \; >> /dev/null" | crontab -u ${USER} - && echo "Cron job added successfully"
