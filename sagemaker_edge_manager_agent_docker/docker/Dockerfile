FROM nvcr.io/nvidia/l4t-base:r32.5.0

ADD 1.20210512.96da6cc.tgz /opt/edge_manager/agent
RUN chmod +x /opt/edge_manager/agent/bin/*
RUN apt update -y && \
	apt install -y curl sudo ca-certificates && \
	update-ca-certificates --fresh && \
	rm -rf /var/lib/apt/lists/*

RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
RUN adduser --disabled-password --gecos '' --ingroup users agent
RUN usermod -a -G sudo,video agent
ENV PATH=/opt/edge_manager/agent/bin:/home/agent/bin:$PATH

ENV TVM_TENSORRT_MAX_WORKSPACE_SIZE=2147483647

USER agent
WORKDIR /home/agent

RUN mkdir -p /home/agent/bin/ && echo "\
if [ ! -f \"conf/agent.json\" ]; then\n\
    echo \"Please, mount dir 'conf' from host to '/home/agent/conf'. This dir needs to contain config.json, certificates and other stuff\"\n\
    exit 0\n\
fi\n\
sagemaker_edge_agent_binary -c /home/agent/conf/agent.json -a /home/agent/sock/edge_agent\n\
" >> bin/init_agent.sh
RUN chmod +x bin/init_agent.sh

ENTRYPOINT ["/bin/bash", "/home/agent/bin/init_agent.sh"]
