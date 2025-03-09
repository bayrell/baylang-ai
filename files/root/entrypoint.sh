#!/bin/bash

trap 'kill -TERM $PID' SIGHUP SIGINT SIGQUIT SIGTERM
sudo -u root -E /root/run.sh &
PID=$!
wait $PID

echo "Shutdown container"