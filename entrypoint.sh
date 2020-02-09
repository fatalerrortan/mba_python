#!/bin/bash 

currency_code=$1

if service redis-server start; then
    python3 app.py $currency_code
else
    echo ">>> trying to start redis server <<<"
fi
