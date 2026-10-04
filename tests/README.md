# Build and VM tests

Run directly on an x86_64 Linux host. CI uses Ubuntu 26.04; its virtiofsd
supports read-only exports and UID/GID translation. Both guests use QEMU TCG,
so KVM and nested virtualization are not required.

On Ubuntu 26.04, install the dependencies and run from the repository root:

```sh
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  build-essential flex bison bc perl pkg-config libelf-dev libssl-dev \
  curl ca-certificates tar xz-utils bzip2 gzip cpio python3 \
  qemu-system-x86 qemu-system-arm virtiofsd openssh-client sshpass
sudo modprobe vhost_vsock
sudo chmod a+rw /dev/vhost-vsock
bash tests/run.sh
```

To build and test only one architecture, use `bash tests/run.sh aarch64` or
`bash tests/run.sh x86_64`. The build tool also accepts `-a aarch64` or
`-a x86_64`; without it, both architectures are built as before.

The suite obtains missing x86_64-hosted toolchains from the pinned
`musl-cc/musl.cc` GitHub mirror because musl.cc blocks Actions traffic.
`tests/toolchains.sha256` pins hashes verified against the original musl.cc
archives; extraction happens only after verification. Existing local toolchains
are reused.

Actions runs each architecture on a separate runner in parallel and caches
its toolchain and kernel build directory. The cache key includes the build
script, kernel configs, and toolchain checksums. A cache hit still runs the
build and all checks; it only avoids recompiling unchanged kernel objects.
Userspace and release archives are rebuilt on every run.

The suite checks config stability and config-update failure handling,
and boots the resulting release archives with 256 MiB of RAM. VM checks cover
the kernel version, DHCP, password SSH login, virtiofs read/write and read-only
exports, console and RNG devices, the SSH banner over default/custom vsock
ports, and guest poweroff.

Logs are written to `build-tests/`, including QEMU and guest console output.
Actions uploads these logs even on failure and uploads the archives only after
all tests pass. Source downloads and build directories remain available for
local reruns. For an existing build, rerun one VM test with:

```sh
python3 tests/smoke.py aarch64 puipui_linux_v1.0.3_aarch64.tar.gz 7.2.9
```

The standalone VM test needs Python 3, QEMU, virtiofsd, OpenSSH and sshpass,
and access to `/dev/vhost-vsock`. Ports 12222/12223 and guest vsock CIDs 42/43
must be unused. Run only one suite per host at a time.

These tests do not exercise Apple Virtualization Framework, host-requested
shutdown, or an aarch64 build host.
