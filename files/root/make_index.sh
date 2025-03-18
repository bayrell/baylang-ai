#!/bin/bash

if [ "`whoami`" != "root" ]; then
	echo "Script must be run as root"
	exit 1
fi

sudo -u www-data /opt/conda/bin/python3 /app/main/Backend/make_index.py
