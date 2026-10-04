#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build-tests

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
