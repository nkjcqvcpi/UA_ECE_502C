# {repo_root}/docker/Dockerfile
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    software-properties-common \
    && add-apt-repository -y universe \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
    build-essential \
    curl wget git \
    vim less file jq \
    lsof procps psmisc \
    strace ltrace \
    gdb gdbserver \
    tcpdump \
    iproute2 iputils-ping net-tools dnsutils ethtool \
    iptables nftables \
    sysstat \
    linux-tools-common \
    binutils elfutils \
    && rm -rf /var/lib/apt/lists/*

# Keep the container alive by default
CMD ["bash", "-lc", "trap : TERM INT; sleep infinity & wait"]
