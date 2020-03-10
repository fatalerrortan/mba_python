#!/bin/bash 

currency_code=$1
exec_mode=$2
rule_dir=$3

# bind redis server to ipv4 instead of ipv6

sed -i "s/bind 127.0.0.1 ::1/bind 127.0.0.1/g" /etc/redis/redis.conf
sed -i "s/supervised no/supervised systemd/g" /etc/redis/redis.conf

if service redis-server start; then
    python3 app.py $currency_code $exec_mode $rule_dir
else
    echo ">>> cannot run redis server <<<"
fi