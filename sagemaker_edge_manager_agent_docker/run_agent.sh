#!/bin/bash
mkdir -p /tmp/sock_agent_0
docker run -it --rm --ipc=host --runtime nvidia -e DISPLAY=$DISPLAY \
	-v /tmp/.X11-unix/:/tmp/.X11-unix \
	-v $PWD/conf:/home/agent/conf \
	-v $PWD/models:/home/agent/models \
	-v $PWD/certs:/home/agent/certs \
	-v /tmp/sock_agent_0:/home/agent/sock \
	edge_manager:1.0
