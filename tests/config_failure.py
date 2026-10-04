"""A failed config update must report failure and preserve the source configs."""
import pathlib
import platform
import shutil
import subprocess
import sys
import tempfile

root = pathlib.Path(__file__).resolve().parent.parent
with tempfile.TemporaryDirectory(prefix="puipui-config-") as directory:
    work = pathlib.Path(directory)
    (work / f"linux-{sys.argv[1]}").symlink_to(root / f"linux-{sys.argv[1]}")
    for arch in ("aarch64", "x86_64"):
        suffix = "native" if arch == platform.machine() else "cross"
        (work / f"{arch}-linux-musl-{suffix}" / "bin").mkdir(parents=True)
    shutil.copytree(root / "kconfig", work / "kconfig")
    result = subprocess.run(
        [str(root / "puipui-linux-tool"), "-u"], cwd=work,
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60,
    )
    (root / "build-tests/config-failure.log").write_text(result.stdout + result.stderr)
    if result.returncode == 0 or "not found" not in result.stderr:
        raise RuntimeError("Missing compiler did not produce the expected failure")
    for config in (work / "kconfig").iterdir():
        if config.read_bytes() != (root / "kconfig" / config.name).read_bytes():
            raise RuntimeError(f"Failed update changed {config.name}")
print("Config failure propagation and preservation: PASS")
