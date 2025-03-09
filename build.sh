#!/bin/bash

SCRIPT=$(readlink -f $0)
SCRIPT_PATH=`dirname $SCRIPT`
BASE_PATH=`dirname $SCRIPT_PATH`

RETVAL=0
VERSION=1.0
SUBVERSION=1
IMAGE="baylang-ai"
TAG=`date '+%Y%m%d_%H%M%S'`

case "$1" in
	
	test)
		DOCKER_BUILDKIT=0 docker build ./ -t bayrell/$IMAGE:$VERSION-$SUBVERSION-$TAG --file Dockerfile
	;;
	
	amd64)
		export DOCKER_DEFAULT_PLATFORM=linux/amd64
		docker build ./ -t bayrell/$IMAGE:$VERSION-$SUBVERSION \
			--file Dockerfile --build-arg ARCH=amd64/
	;;
	
	upload-github)
		docker tag bayrell/$IMAGE:$VERSION-$SUBVERSION \
			ghcr.io/bayrell-os/$IMAGE:$VERSION-$SUBVERSION
		
		docker push ghcr.io/bayrell-os/$IMAGE:$VERSION-$SUBVERSION
	;;
	
	all)
		$0 amd64
	;;
	
	*)
		echo "Usage: $0 {amd64|manifest|all|test}"
		RETVAL=1

esac

exit $RETVAL
