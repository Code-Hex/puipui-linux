# CLAUDE.md - AI Assistant Guide for PUI PUI Linux

This document provides comprehensive information about the PUI PUI Linux codebase for AI assistants working on this project.

## Project Overview

**PUI PUI Linux** is a minimal Linux distribution designed specifically for testing the Apple Virtualization Framework (https://github.com/Code-Hex/vz). The project prioritizes:

- **Minimalism**: Extremely small kernel and initramfs for fast downloads and testing in CI environments
- **Architecture Support**: Only aarch64 (arm64) and x86_64 architectures
- **Virtualization-First**: Built exclusively for virtualized environments using VIRTIO devices

### Current Version
- Tool Version: 1.0.3
- Kernel Version: 7.2.9
- BusyBox Version: 1.36.1
- Dropbear Version: 2024.86
- Socat Version: 1.8.0.1

## Repository Structure

```
puipui-linux/
├── .git/                       # Git repository metadata
├── .gitignore                  # Git ignore patterns
├── README.md                   # User-facing documentation
├── CLAUDE.md                   # This file
├── puipui-linux-tool           # Main build script (Bash)
├── kconfig/                    # Kernel configuration files
│   ├── aarch64.config         # ARM64 kernel config (defconfig format)
│   └── x86_64.config          # x86_64 kernel config (defconfig format)
├── busybox_config/            # BusyBox configuration
│   └── config                 # BusyBox build configuration
├── fs/                        # Initramfs filesystem template
│   ├── init                   # Init script (runs at boot)
│   ├── alpine-chroot-install  # Alpine chroot installer utility
│   ├── etc/                   # System configuration files
│   │   ├── inittab           # BusyBox init configuration
│   │   ├── passwd            # User accounts
│   │   ├── group             # Group definitions
│   │   ├── securetty         # Secure TTY list
│   │   ├── resolv.conf       # DNS configuration
│   │   ├── issue             # Login banner
│   │   ├── conf.d/           # Service configurations
│   │   └── init.d/           # Init scripts
│   └── usr/                   # User binaries and libraries
└── build-*/                   # Build artifacts (gitignored)
    ├── linux-kernel/          # Kernel build directory
    ├── busybox/               # BusyBox build directory
    ├── fs/                    # Built filesystem
    ├── dropbear/              # Dropbear SSH build
    ├── socat/                 # Socat build
    ├── curl/                  # Curl binary download
    └── artifact/              # Final build outputs
        ├── Image.gz (aarch64) or bzImage (x86_64)
        └── initramfs.cpio.gz
```

## Architecture Support

### Supported Architectures

1. **aarch64 (ARM64)**
   - Kernel output: `arch/arm64/boot/Image.gz`
   - Kernel arch name: `arm64`
   - Cross-compile prefix: `aarch64-linux-musl-`

2. **x86_64 (AMD64)**
   - Kernel output: `arch/x86/boot/bzImage`
   - Kernel arch name: `x86`
   - Cross-compile prefix: `x86_64-linux-musl-`

### Architecture-Specific Behavior

- On ARM64 hosts, the build tool downloads musl toolchains from https://github.com/Code-Hex/musl-cross-make-arm64
- On x86_64 hosts, toolchains come from https://musl.cc/
- Native builds use `*-linux-musl-native` directories
- Cross-compilation uses `*-linux-musl-cross` directories

## Build System

### Main Build Tool: `puipui-linux-tool`

The build script is a monolithic Bash script that orchestrates the entire build process.

**Usage:**
```bash
./puipui-linux-tool           # Build everything
./puipui-linux-tool -u        # Update kernel configs only
./puipui-linux-tool -h        # Show help
./puipui-linux-tool -v        # Show version
```

### Build Process Flow

1. **Download Dependencies** (if not present):
   - Linux kernel tarball from kernel.org
   - BusyBox from busybox.net
   - Dropbear from matt.ucc.asn.au
   - Socat from dest-unreach.org
   - Musl cross-compilation toolchains

2. **Build Kernel** (`build_kern`):
   - Prepares config for each architecture
   - Runs `make olddefconfig` to update config
   - Builds kernel with musl toolchain
   - Outputs to `build-{arch}/artifact/`

3. **Download Curl** (`download_curl`):
   - Fetches static curl binaries from moparisthebest/static-curl
   - Places in `build-{arch}/curl/`

4. **Build Initramfs** (`build_initramfs`):
   - Copies `fs/` template to `build-{arch}/fs/`
   - Builds and installs Dropbear SSH server
   - Builds and installs Socat
   - Installs static curl binary
   - Copies CA certificates for HTTPS support
   - Builds BusyBox and installs to filesystem
   - Creates compressed cpio archive: `initramfs.cpio.gz`

5. **Pack Artifacts** (`pack_artifacts`):
   - Creates `puipui_linux_v{version}_{arch}.tar.gz`
   - Contains kernel image and initramfs

### Build Directories (Gitignored)

All build artifacts go into `build-{arch}/` directories:
- `build-aarch64/`
- `build-x86_64/`

These are gitignored along with downloaded source tarballs.

## Key Components

### 1. Linux Kernel

**Features Enabled:**
- Networking (TCP/IP stack)
- VIRTIO drivers:
  - `virtio_blk` - Block devices
  - `virtio_console` - Console via hvc drivers
  - `virtio_fs` - Filesystem sharing (virtfs)
  - `virtio_vsock` - AF_VSOCK socket family
  - `virtio_gpu` - GPU support (recent addition)
- CONFIG_IKCONFIG - Kernel configuration in /proc/config.gz
- CONFIG_NO_HZ - Tickless kernel
- CONFIG_HIGH_RES_TIMERS - High-resolution timers
- CONFIG_CC_OPTIMIZE_FOR_SIZE - Size optimization
- ACPI support (x86_64)
- GPIO support (aarch64 for power events)

**Kernel Configuration Management:**
- Configs stored as defconfig format in `kconfig/{arch}.config`
- Use `./puipui-linux-tool -u` to update configs
- Process: `olddefconfig` → `savedefconfig` (both target toolchains; failures stop the command)
- Always use `olddefconfig` for non-interactive updates

### 2. Initramfs & Init System

**Init Script:** `fs/init`
- Written in BusyBox sh
- Runs as PID 1
- Responsibilities:
  - Install BusyBox applets (`busybox --install -s`)
  - Mount pseudo-filesystems (proc, sysfs, devtmpfs)
  - Setup device nodes with mdev
  - Create essential devices (/dev/null, /dev/kmsg, /dev/ptmx)
  - Mount devpts for PTY support
  - Mount tmpfs for /dev/shm
  - Parse kernel command line for parameters
  - Setup console devices in /etc/inittab and /etc/securetty
  - Set hostname to "localhost"
  - Set root password to "passwd"
  - Handle `vsock_port=` kernel parameter (defaults to 2222)
  - Execute `/linuxrc` (BusyBox init)

**Kernel Command Line Parsing:**
- `vsock_port=N` - Sets VSOCK_PORT environment variable

**Console Setup:**
- Automatically detects console devices from kernel
- Dynamically adds getty entries to `/etc/inittab`
- Updates `/etc/securetty` for root login

### 3. Included Software

**BusyBox:**
- Provides core Unix utilities
- Configuration in `busybox_config/config`
- Built statically with musl libc
- Installed to `/bin/busybox` with symlinks

**Dropbear SSH:**
- Lightweight SSH server
- Built statically without zlib
- Login and wtmp disabled
- Configuration goes to `/etc/dropbear/`

**Socat:**
- Multi-purpose relay tool
- Built statically without OpenSSL, readline, libwrap
- Workaround for getprotobynumber_r issue (Alpine Linux patch)

**Curl:**
- Pre-built static binary (not compiled from source)
- HTTPS support with CA certificates from host
- CA certs copied to `/etc/ssl/certs/ca-certificates.crt`

## Development Workflow

### Making Changes to Kernel Config

**For aarch64:**
```bash
# Edit kconfig/aarch64.config manually or use menuconfig
./puipui-linux-tool -u
# Review changes in kconfig/aarch64.config
git add kconfig/aarch64.config
git commit -m "updated aarch64 kconfig to enable FEATURE_X"
```

**For x86_64:**
```bash
# Edit kconfig/x86_64.config manually or use menuconfig
./puipui-linux-tool -u
# Review changes in kconfig/x86_64.config
git add kconfig/x86_64.config
git commit -m "enabled CONFIG_FEATURE_X for x86_64"
```

**Interactive menuconfig:**
```bash
# After running build once to download kernel sources
cd build-aarch64/linux-kernel  # or build-x86_64/linux-kernel
make menuconfig
# Save and exit
cd ../..
./puipui-linux-tool -u  # Update defconfig
```

### Modifying Initramfs

1. Edit files in `fs/` directory:
   - `fs/init` - Boot initialization script
   - `fs/etc/inittab` - Init configuration
   - `fs/etc/passwd`, `fs/etc/group` - User/group setup
   - Add new files/directories as needed

2. Rebuild:
   ```bash
   ./puipui-linux-tool
   ```

3. The `fs/` directory is copied to `build-{arch}/fs/` during build
4. Additional components installed during build:
   - Dropbear (built from source)
   - Socat (built from source)
   - Curl (downloaded binary)
   - CA certificates (copied from host)
   - BusyBox (built and symlinks created)

### Modifying BusyBox Config

1. Edit `busybox_config/config`
2. Or use menuconfig:
   ```bash
   cd build-aarch64/busybox  # After first build
   make menuconfig
   cp .config ../../busybox_config/config
   ```
3. Rebuild with `./puipui-linux-tool`

### Testing Changes

The build produces:
- `build-{arch}/artifact/Image.gz` or `bzImage`
- `build-{arch}/artifact/initramfs.cpio.gz`
- `puipui_linux_v{version}_{arch}.tar.gz`

Use these with the vz framework for testing.

## Git Workflow

### Branch Naming

- Feature branches: `claude/feature-name-{sessionId}`
- Example: `claude/add-claude-documentation-bBPid`
- CRITICAL: Branches must start with `claude/` and end with matching session ID for successful push

### Commit Message Conventions

Based on recent history, commits follow these patterns:

**Good examples:**
- `"fixed x86_64 config and enabled VIRTIO_GPU in both"`
- `"allow specifing vsock port on cmdline"`
- `"use v6.11.5 kernel and updated some config"`
- `"enabled CONFIG_ACPI_PCI_SLOT and CONFIG_ACPI_APEI for x86_64"`

**Conventions:**
- Use lowercase imperative mood ("fixed", "enabled", "added", "updated")
- Be specific about what changed
- Reference architecture if change is arch-specific
- For config changes, mention the CONFIG_ symbol
- Keep messages concise but descriptive

### Pushing Changes

```bash
git push -u origin <branch-name>
```

**Important:** If push fails due to network errors, retry up to 4 times with exponential backoff (2s, 4s, 8s, 16s).

## Important Conventions for AI Assistants

### 1. Don't Break the Build

- Always test with `./puipui-linux-tool` before committing
- Kernel config changes must be validated with `-u` flag
- Never commit broken configs or syntax errors in scripts

### 2. Preserve Cross-Architecture Support

- Changes must work for BOTH aarch64 and x86_64
- Test both architectures when modifying kernel configs
- Architecture-specific changes must be clearly documented

### 3. Maintain Minimalism

- This is a **minimal** Linux distribution
- Don't add unnecessary features or bloat
- Consider size impact of any additions
- Question whether a feature is needed for virtualization testing

### 4. Handle Musl Libc Constraints

- All userspace is built against musl libc, not glibc
- Some features may not be available
- Prefer static linking for reliability
- Be aware of musl vs glibc differences

### 5. Respect the Init System

- Init is a simple BusyBox-based system
- No systemd, no complex init systems
- Keep init script simple and readable
- Changes to boot process go in `fs/init`

### 6. Configuration File Formats

- **Kernel configs:** defconfig format (minimal, not full .config)
- **BusyBox config:** full .config format
- Never commit generated configs from build directories
- Only commit configs from `kconfig/` and `busybox_config/`

### 7. Build Determinism

- Builds use `SOURCE_DATE_EPOCH` for reproducibility
- `KBUILD_BUILD_HOST="molbuilder"`
- `KBUILD_BUILD_USER="codehex"`
- Don't modify these unless necessary

### 8. Dependency Management

- All external dependencies are downloaded during build
- Never commit downloaded sources (gitignored)
- URL changes should be rare and carefully considered
- Verify download URLs are stable

### 9. Security Considerations

- Root password is hardcoded: "passwd" (this is for testing only)
- No security hardening (this is a test environment)
- SSH via Dropbear is for convenience, not production use
- CA certificates included only for testing HTTPS in curl

### 10. File Paths and Structure

- Never use relative paths in scripts
- Build script maintains working directory carefully
- All paths calculated from `$srcdir` variable
- Use helper functions: `_builddir`, `_artifact`, `_kconfig`, etc.

## Common Tasks Reference

### Update to New Kernel Version

1. Edit `puipui-linux-tool`: change `kernver=7.2.9` to new version
2. Run `./puipui-linux-tool` - it will download new kernel
3. May need to update configs: `./puipui-linux-tool -u`
4. Test both architectures
5. Commit with message like: `"use v6.12.0 kernel and updated some config"`

### Enable a New Kernel Feature

1. Edit `kconfig/{arch}.config` to add `CONFIG_FEATURE=y`
2. Run `./puipui-linux-tool -u` to validate
3. Review changes to ensure only intended options changed
4. If multiple architectures: repeat for each
5. Commit: `"enabled CONFIG_FEATURE for {arch}"`

### Add a New Utility to Initramfs

1. Decide: compile from source or download binary?
2. If compiling: add fetch, build, and install functions (like `install_dropbear`)
3. If binary: add download and install (like `download_curl`)
4. Modify `build_initramfs` to call your install function
5. Test the build
6. Commit changes with clear description

### Modify Init Behavior

1. Edit `fs/init`
2. Follow BusyBox sh syntax (limited compared to bash)
3. Test in actual VM environment
4. Consider backward compatibility
5. Document any new kernel parameters

### Debug Build Issues

1. Check `build-{arch}/` directories for logs
2. Kernel build logs in `build-{arch}/linux-kernel/`
3. BusyBox logs in `build-{arch}/busybox/`
4. Component builds in respective directories
5. Use `make V=1` for verbose output if needed

### Clean Build

```bash
rm -rf build-* linux-* busybox-* dropbear-* socat-* *-linux-musl-* *.tar.gz *.tar.xz *.tgz
./puipui-linux-tool  # Fresh build
```

## Technical Details

### Cross-Compilation

- Musl cross-compilers used for deterministic, static builds
- `CROSS_COMPILE` environment variable set for make
- `CC`, `AR`, `RANLIB`, `STRIP` explicitly set for configure scripts
- `ARCH` variable maps to kernel arch names (arm64, x86)

### Static Linking

- All binaries statically linked against musl
- `LDFLAGS="-static"` for BusyBox
- Configure flags for Dropbear and Socat
- Ensures initramfs has no external dependencies

### Initramfs Format

- Created with: `find . | cpio -o -H newc | gzip -9`
- Format: newc (new ASCII format)
- Compression: gzip -9 (maximum compression)
- Kernel loads via CONFIG_BLK_DEV_INITRD

### VIRTIO Dependencies

The system relies entirely on VIRTIO for I/O:
- **No native disk drivers** (only virtio_blk)
- **No native network drivers** (virtio_net via networking stack)
- **Console via hvc** (virtio_console)
- **File sharing via virtfs** (virtio_fs, 9p filesystem)
- **Sockets via vsock** (virtio_vsock, AF_VSOCK)

This means the system ONLY works in virtualized environments with VIRTIO support.

## File Location Quick Reference

| What | Where |
|------|-------|
| Main build script | `./puipui-linux-tool` |
| ARM64 kernel config | `kconfig/aarch64.config` |
| x86_64 kernel config | `kconfig/x86_64.config` |
| BusyBox config | `busybox_config/config` |
| Init script | `fs/init` |
| Init configuration | `fs/etc/inittab` |
| User accounts | `fs/etc/passwd`, `fs/etc/group` |
| Build artifacts | `build-{arch}/artifact/` |
| Final tarballs | `puipui_linux_v{version}_{arch}.tar.gz` |

## Troubleshooting

### "No rule to make target" errors
- Clean build: remove `build-*` directories
- Re-run `./puipui-linux-tool`

### Config update changes unexpected options
- Kernel config dependencies may enable/disable related options
- Review with `git diff kconfig/`
- This is normal for defconfig format

### Musl toolchain not found
- Ensure internet connectivity
- Check GitHub/musl.cc availability
- Verify architecture matches uname -m

### Init fails to boot
- Check syntax with `sh -n fs/init`
- Verify BusyBox applets are available
- Check for missing dependencies in initramfs

### Binary too large
- Review kernel config for bloat (modules, debugging)
- Check if unnecessary features enabled
- Consider CONFIG_CC_OPTIMIZE_FOR_SIZE (already enabled)

## Recent Changes (Last 20 Commits)

```
a74100f fixed x86_64 config and enabled VIRTIO_GPU in both
7c10926 allow specifing vsock port on cmdline
96c1436 revert login settings in busybox config
83d66c9 use v6.11.5 kernel and updated some config
51a0147 bump 0.0.2
5c0c20e updated curl and dropbear
e6fcf91 enabled /dev/input/event* in x86_64
888abb7 updated aarch64 kconfig to handle poweroff GPIO event
0b77236 added event handler for request stop
```

Notable recent developments:
- Added VIRTIO_GPU support
- Added vsock_port kernel parameter
- Updated to kernel 6.11.5
- Improved GPIO event handling for power management
- Input event support for x86_64

---

**Last Updated:** 2026-01-05
**Document Version:** 1.0
**For:** PUI PUI Linux v1.0.3

This document should be updated whenever significant architectural changes are made to the project.
