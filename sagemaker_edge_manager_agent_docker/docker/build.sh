#!/bin/bash

if [ ! -f "1.20210512.96da6cc.tgz" ]; then
	echo 'Downloading file'
	aws s3 cp s3://sagemaker-edge-release-store-us-west-2-linux-armv8/Releases/1.20210512.96da6cc/1.20210512.96da6cc.tgz .
fi
docker build -t edge_manager:1.0 .

