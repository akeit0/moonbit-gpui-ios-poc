#!/usr/bin/env python3
"""Fetch pinned dependencies and build the native host inside this repository."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.shared.process import execute

TARGETS = {"simulator": "aarch64-apple-ios-sim", "device": "aarch64-apple-ios"}


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def download(url, destination, expected):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and digest(destination) == expected:
        return
    partial = destination.with_suffix(".partial")
    execute(["curl", "--fail", "--location", "--retry", "3", "--output", partial, url])
    if digest(partial) != expected:
        partial.unlink()
        raise RuntimeError(f"Checksum mismatch for {url}; dependency pins were not changed")
    partial.replace(destination)


def extract(archive, destination):
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as stream:
        for item in stream.getmembers():
            target = (destination / item.name).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise RuntimeError("Archive path escapes its installation directory")
            if item.issym() or item.islnk():
                base = target.parent if item.issym() else destination
                if not (base / item.linkname).resolve().is_relative_to(destination.resolve()):
                    raise RuntimeError("Archive link escapes its installation directory")
            elif not item.isfile() and not item.isdir():
                raise RuntimeError("Unsupported archive member")
        stream.extractall(destination)


def setup_moon(pin):
    home = ROOT / ".tools/moon"
    marker = home / ".poc-toolchain.json"
    if home.exists():
        if home.is_symlink() or not marker.is_file() or json.loads(marker.read_text()) != pin:
            raise RuntimeError("Existing .tools/moon is not the pinned installation; move it aside first")
        return
    pending = ROOT / ".tools/moon-install"
    if pending.exists():
        owner = pending / ".poc-installing.json"
        if pending.is_symlink() or not owner.is_file() or json.loads(owner.read_text()) != pin:
            raise RuntimeError("Unrecognized .tools/moon-install exists; move it aside before retrying")
        shutil.rmtree(pending)
    compiler = ROOT / ".downloads/moonbit.tar.gz"
    core = ROOT / ".downloads/core.tar.gz"
    download(pin["toolchain_url"], compiler, pin["toolchain_sha256"])
    download(pin["core_url"], core, pin["core_sha256"])
    pending.mkdir(parents=True)
    (pending / ".poc-installing.json").write_text(json.dumps(pin))
    extract(compiler, pending)
    extract(core, pending / "lib")
    # The official archive ships binaries without execute bits.
    for executable in (pending / "bin").rglob("*"):
        if executable.is_file():
            executable.chmod(executable.stat().st_mode | 0o111)
    environment = os.environ.copy()
    environment.update(MOON_HOME=str(pending), PATH=str(pending / "bin") + os.pathsep + environment["PATH"])
    moon = pending / "bin/moon"
    version = execute([moon, "version", "--all"], env=environment, capture=True)
    if "moonc v" + pin["version"] not in version:
        raise RuntimeError("Downloaded MoonBit compiler does not match the pinned version")
    print(version, end="")
    execute([moon, "-C", pending / "lib/core", "bundle", "--warn-list", "-a", "--all"], env=environment)
    execute([moon, "-C", pending / "lib/core", "bundle", "--warn-list", "-a",
             "--target", "wasm-gc", "--quiet"], env=environment)
    (pending / ".poc-toolchain.json").write_text(json.dumps(pin, indent=2) + "\n")
    (pending / ".poc-installing.json").unlink()
    pending.rename(home)


def setup_host(pin):
    host = ROOT / ".deps/gpui-dotnet"
    if host.is_symlink():
        raise RuntimeError("Dependency checkout must not be a symlink")
    if not host.exists():
        host.parent.mkdir(parents=True, exist_ok=True)
        execute(["git", "clone", "--no-checkout", pin["url"], host])
        execute(["git", "-C", host, "checkout", "--detach", pin["revision"]])
    revision = execute(["git", "-C", host, "rev-parse", "HEAD"], capture=True).strip()
    if revision != pin["revision"]:
        raise RuntimeError("Existing dependency checkout is at a different revision; move it aside first")
    changes = execute(["git", "-C", host, "status", "--porcelain", "--untracked-files=no"], capture=True)
    if changes:
        raise RuntimeError("Dependency tracked files have local changes; setup will not overwrite them")
    return host


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=["simulator", "device", "both"], default="simulator")
    args = parser.parse_args()
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        parser.error("This PoC setup supports Apple Silicon macOS")
    for name in ("git", "curl", "xcrun", "rustup", "cargo"):
        if not shutil.which(name):
            parser.error(f"Install prerequisite {name} before running setup; see README.md")
    execute(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-path"])
    pins = json.loads((ROOT / "dependencies.lock.json").read_text())
    setup_moon(pins["moonbit"])
    host = setup_host(pins["gpui_dotnet"])
    rust = pins["rust_toolchain"]
    execute(["rustup", "toolchain", "install", rust, "--profile", "minimal"])
    selected = list(TARGETS) if args.platform == "both" else [args.platform]
    environment = os.environ.copy()
    environment["CARGO_TARGET_DIR"] = str(host / "crates/gpui-dotnet/target")
    for selected_platform in selected:
        target = TARGETS[selected_platform]
        execute(["rustup", "target", "add", "--toolchain", rust, target])
        execute(["cargo", "+" + rust, "build", "--locked", "--manifest-path",
                 host / "crates/gpui-dotnet/Cargo.toml", "--target", target, "--lib"],
                cwd=host, env=environment)
    print("Setup complete. See README.md for build and run commands.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError, ValueError) as error:
        print(f"Setup failed: {error}", file=sys.stderr)
        sys.exit(1)
