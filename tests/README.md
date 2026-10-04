# Build and VM tests

Run on an x86_64 Linux host with Docker and the `vhost_vsock` kernel module.
Both guests use QEMU TCG, so KVM and nested virtualization are not required.
The vsock device is required; a missing device fails the test. The test
container disables Docker's default seccomp and AppArmor profiles because they
block host `AF_VSOCK` sockets. Ubuntu 26.04 supplies virtiofsd with read-only
export support.

From the repository root:

```sh
sudo modprobe vhost_vsock
sudo chmod a+rw /dev/vhost-vsock
docker build -t puipui-tests -f tests/Dockerfile .
docker run --rm --device /dev/vhost-vsock --security-opt seccomp=unconfined --security-opt apparmor=unconfined \
  --user "$(id -u):$(id -g)" \
  -v "$PWD:/workspace" puipui-tests
```

The suite obtains missing x86_64-hosted toolchains from the pinned
`musl-cc/musl.cc` GitHub mirror because musl.cc blocks Actions traffic.
`tests/toolchains.sha256` pins hashes verified against the original musl.cc
archives; extraction happens only after verification. Existing local toolchains
are reused.

The same command runs in `.github/workflows/test.yml`. It checks config
stability, builds both architectures, checks config-update failure handling,
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
