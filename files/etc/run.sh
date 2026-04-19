#!/bin/bash

if [ ! -d /data/model ]; then
	mkdir -p /data/model
fi

node --watch /app/index.js
