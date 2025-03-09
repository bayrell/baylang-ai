#!/bin/bash

if [ "`whoami`" != "root" ]; then
  echo "Script must be run as root"
  exit 1
fi

export EDITOR=nano

# Run scripts
if [ -d /root/run.d ]; then
  for i in /root/run.d/*.sh; do
    if [ -f $i ]; then
      . $i start
    fi
  done
  unset i
fi

# Run main script
echo "Started"
/root/main.py
