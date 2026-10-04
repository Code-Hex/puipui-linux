FROM ubuntu:26.04

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    build-essential flex bison bc perl pkg-config libelf-dev libssl-dev \
    curl ca-certificates tar xz-utils bzip2 gzip cpio python3 \
    qemu-system-x86 qemu-system-arm virtiofsd openssh-client sshpass \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
CMD ["bash", "tests/run.sh"]
