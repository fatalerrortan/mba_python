#!/bin/bash 

currency_code=$1
exec_mode=$2

if service redis-server start; then
    python3 app.py $currency_code $exec_mode
else
    echo ">>> trying to start redis server <<<"
fi
