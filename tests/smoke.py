"""Boot the packaged images, exercise guest interfaces, and retain failure logs."""
import argparse
import pathlib
import os
import shutil
import socket
import subprocess
import tarfile
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("arch", choices=("aarch64", "x86_64"))
    parser.add_argument("archive", type=pathlib.Path)
    parser.add_argument("kernel_version")
    args = parser.parse_args()
    root = pathlib.Path(__file__).resolve().parent.parent
    logs_dir = root / "build-tests" / args.arch
    logs_dir.mkdir(parents=True, exist_ok=True)
    kernel, machine, cpu, port, cid, vsock_port = {
        "aarch64": ("Image.gz", "virt", "cortex-a72", 12223, 43, 2345),
        "x86_64": ("bzImage", "q35", "max", 12222, 42, 2222),
    }[args.arch]
    processes = []
    logs = []

    def start(command, name):
        log = open(logs_dir / name, "w")
        logs.append(log)
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
                                   stderr=subprocess.STDOUT)
        processes.append(process)
        return process

    with tempfile.TemporaryDirectory(prefix="puipui-smoke-") as directory:
        work = pathlib.Path(directory)

        def ssh(command):
            return subprocess.run(
                ["sshpass", "-p", "passwd", "ssh", "-o", "StrictHostKeyChecking=no",
                 "-o", f"UserKnownHostsFile={work}/known_hosts", "-o", "ConnectTimeout=3",
                 "-p", str(port), "root@127.0.0.1", command],
                capture_output=True, text=True, timeout=15,
            )

        try:
            # Copy only the expected regular files; reject incompatible archive layouts.
            with tarfile.open(args.archive, "r:gz") as archive:
                files = [member for member in archive.getmembers() if not member.isdir()]
                if sorted(member.name.removeprefix("./") for member in files) != sorted([kernel, "initramfs.cpio.gz"]):
                    raise RuntimeError("Unexpected archive contents")
                for member in files:
                    if not member.isfile():
                        raise RuntimeError("Archive contains a non-regular file")
                    with archive.extractfile(member) as source:
                        (work / member.name.removeprefix("./")).write_bytes(source.read())
            shared = work / "shared"
            shared.mkdir()
            (shared / "host.txt").write_text("from-host\n")
            virtiofsd = shutil.which("virtiofsd") or "/usr/libexec/virtiofsd"
            for tag in ("rw", "ro"):
                command = [virtiofsd, "--shared-dir", str(shared), "--socket-path",
                           str(work / f"{tag}.sock"), "--sandbox", "none",
                           "--translate-uid", f"map:0:{os.getuid()}:1",
                           "--translate-gid", f"map:0:{os.getgid()}:1"]
                if tag == "ro":
                    command.append("--readonly")
                daemon = start(command, f"virtiofs-{tag}.log")
                deadline = time.monotonic() + 10
                while not (work / f"{tag}.sock").exists():
                    if daemon.poll() is not None or time.monotonic() >= deadline:
                        raise RuntimeError(f"virtiofsd failed; see {logs_dir}")
                    time.sleep(.1)
            command = [f"qemu-system-{args.arch}", "-machine", machine, "-accel", "tcg",
                       "-cpu", cpu, "-m", "256", "-smp", "1", "-display", "none",
                       "-monitor", "none", "-serial", "none", "-kernel", str(work / kernel),
                       "-initrd", str(work / "initramfs.cpio.gz"), "-append",
                       "console=hvc0" + (f" vsock_port={vsock_port}" if args.arch == "aarch64" else ""),
                       "-object", "memory-backend-memfd,id=mem,size=256M,share=on",
                       "-numa", "node,memdev=mem", "-device", "virtio-serial-pci",
                       "-chardev", f"file,id=console,path={logs_dir}/console.log",
                       "-device", "virtconsole,chardev=console", "-netdev",
                       f"user,id=net,hostfwd=tcp:127.0.0.1:{port}-:22",
                       "-device", "virtio-net-pci,netdev=net,romfile=",
                       "-device", "virtio-rng-pci", "-device", "virtio-balloon-pci",
                       "-device", f"vhost-vsock-pci,guest-cid={cid}"]
            for tag in ("rw", "ro"):
                command += ["-chardev", f"socket,id={tag},path={work}/{tag}.sock",
                            "-device", f"vhost-user-fs-pci,chardev={tag},tag={tag}"]
            vm = start(command, "qemu.log")
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                if vm.poll() is not None:
                    raise RuntimeError(f"QEMU exited early; see {logs_dir}")
                try:
                    result = ssh("uname -r")
                except subprocess.TimeoutExpired:
                    continue
                if result.returncode == 0:
                    if result.stdout.strip() != args.kernel_version:
                        raise RuntimeError(f"Unexpected kernel: {result.stdout}")
                    break
                time.sleep(1)
            else:
                raise RuntimeError(f"Guest SSH did not become ready; see {logs_dir}")
            result = ssh('''set -eu
ip addr show eth0
mkdir -p /mnt/rw /mnt/ro
mount -t virtiofs rw /mnt/rw
mount -t virtiofs ro /mnt/ro
test "$(cat /mnt/rw/host.txt)" = from-host
test "$(cat /mnt/ro/host.txt)" = from-host
echo from-guest > /mnt/rw/guest.txt
if touch /mnt/ro/must-not-exist 2>/dev/null; then exit 1; fi
test -c /dev/hvc0
test -c /dev/hwrng
''')
            (logs_dir / "guest.log").write_text(result.stdout + result.stderr)
            if result.returncode or (shared / "guest.txt").read_text() != "from-guest\n":
                raise RuntimeError(f"Guest interface checks failed; see {logs_dir}")
            console = (logs_dir / "console.log").read_text()
            if "lease of " not in console or " obtained from " not in console:
                raise RuntimeError("Guest did not obtain a DHCP lease")
            with socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM) as connection:
                connection.settimeout(10)
                connection.connect((cid, vsock_port))
                banner = b""
                while b"\n" not in banner and len(banner) < 256:
                    chunk = connection.recv(256)
                    if not chunk:
                        break
                    banner += chunk
                if not banner.startswith(b"SSH-2.0-dropbear"):
                    raise RuntimeError(f"Unexpected vsock response: {banner!r}")
            ssh("poweroff")
            if vm.wait(timeout=30) != 0:
                raise RuntimeError("Guest shutdown failed")
            print(f"{args.arch}: {args.kernel_version}, DHCP, SSH, virtiofs RW/RO, "
                  f"vsock {vsock_port}, poweroff: PASS", flush=True)
        finally:
            for process in reversed(processes):
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
            for log in logs:
                log.close()


if __name__ == "__main__":
    main()
