#!/bin/bash 

if service redis-server start; then
    python3 app.py
else
    echo ">>> trying to start redis server <<<"
fi
