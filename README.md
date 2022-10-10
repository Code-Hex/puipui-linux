# PUI PUI Linux

![puipui](https://user-images.githubusercontent.com/6500104/194863884-2b3fb507-e3ad-413c-93f1-b4249068f218.png)


This is the minimum linux for testing the apple virtualization framework (https://github.com/Code-Hex/vz). So I assumed to support architectures are only x86\_64 and aarch64 (arm64).


This vmlinux is actually very very small other than linux distributions.

Since file size is very small in totally, I can do testing on the any CI with download them.

## Kernel

What's supported:

- Internet
- VIRTIO (Virt device I/O)
  - virtio blk device
  - virtio console (via hvc drivers. e.g. `console=hvc0`)
  - virtio filesystem (virtfs)
  - af\_vsock

## Initramfs

Our initramfs has a very simple init system controlled by `fs/init` script on this repository root. this script will do:

- Mount any file systems (proc, sysfs and devfs).
- Setup console which is an user specified by a console kernel parameter.
  - Find devices and add them to `/etc/inittab` and `/etc/securetty`.

You can use it with other linux distributions.

## Usage

### Build all

```
$ ./puipui-linux-tool
```

### Update Kernel config

```
$ ./puipui-linux-tool -u
```

## Hack

This tool is used musl cross compiler. On arm64 environment the tool will be downloaded those pre build toolchains from https://github.com/Code-Hex/musl-cross-make-arm64
