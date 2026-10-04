#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build-tests

# musl.cc blocks Actions; these mirror files match the original archives.
while read -r checksum archive; do
    if [ ! -d "${archive%.tgz}" ]; then
        (
            staging=$(mktemp -d)
            trap 'rm -rf "$staging"' EXIT
            curl -fL --retry 3 --connect-timeout 30 \
                "https://github.com/musl-cc/musl.cc/releases/download/v0.0.1/$archive" \
                -o "$staging/$archive"
            printf '%s  %s\n' "$checksum" "$staging/$archive" | sha256sum --check
            tar -xzf "$staging/$archive" -C "$staging"
            mv "$staging/${archive%.tgz}" .
        )
    fi
done < tests/toolchains.sha256

# Keep the build's non-interactive input and diagnostics identical in CI and locally.
bash -n puipui-linux-tool
echo "Checking fresh and repeated config updates"
sha256sum kconfig/*.config >build-tests/config.sha256
./puipui-linux-tool -u </dev/null >build-tests/config.log 2>&1
sha256sum --check build-tests/config.sha256
./puipui-linux-tool -u </dev/null >>build-tests/config.log 2>&1
sha256sum --check build-tests/config.sha256

echo "Building both architectures (see build-tests/build.log)"
./puipui-linux-tool </dev/null >build-tests/build.log 2>&1
version=$(sed -n 's/^version=//p' puipui-linux-tool)
kernel=$(sed -n 's/^kernver=//p' puipui-linux-tool)
python3 tests/config_failure.py "$kernel"
for arch in aarch64 x86_64; do
    python3 tests/smoke.py "$arch" "puipui_linux_v${version}_${arch}.tar.gz" "$kernel"
done
