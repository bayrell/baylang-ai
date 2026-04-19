#!/bin/bash

# Script for building Docker container BayLang AI

VERBOSE=false

# Image name
IMAGE_NAME="bayrell/baylang-ai"

# Get version from package.json or use "latest"
VERSION=$(node -p "require('./src/package.json').version" 2>/dev/null || echo "latest")

# Function to build image
build_image() {
	local VERSION=$1
	local ARCH=$2
	
	if [ -z "$ARCH" ]; then
		ARCH="amd64"
	fi
	
	echo "Building Docker image $IMAGE_NAME:$VERSION"
	
	if [ "$VERBOSE" == "true" ]; then
		docker build -t $IMAGE_NAME:$VERSION \
			--build-arg="$ARCH/" --progress=plain .
	else
		docker build -t $IMAGE_NAME:$VERSION \
			--build-arg="$ARCH/" .
	fi
	
	# Check build success
	if [ $? -eq 0 ]; then
		echo "✅ Image $IMAGE_NAME:$VERSION successfully built!"
		return 0
	else
		echo "❌ Error building image $IMAGE_NAME:$VERSION"
		return 1
	fi
}

# Get first argument (build target)
TARGET=$1

# Use switch case to select build target
case "$TARGET" in
	test)
		# Generate label with current date and time
		TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
		build_image "$TIMESTAMP"
		exit $?
		;;
	amd64)
		build_image "$VERSION-amd64" "amd64"
		;;
	prod)
		build_image "$VERSION"
		exit $?
		;;
	*)
		echo "Usage: $0 {test|prod}"
		echo "   test  - build test container"
		echo "   prod  - build production container"
		exit 1
		;;
esac