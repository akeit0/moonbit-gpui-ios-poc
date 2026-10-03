"""GPUI.NET source staging, ABI generation and native link requirements."""
import json
from pathlib import Path
import re
import shutil
import subprocess

from .generate_abi import generate
from tools.shared.moon import stage_module

FRAMEWORKS = "UIKit Metal MetalKit QuartzCore CoreGraphics CoreText CoreFoundation Foundation Security SystemConfiguration AudioToolbox WebKit CoreMedia AVFoundation LocalAuthentication Contacts EventKit StoreKit CoreMotion".split()


def default_archive(host: Path, platform: str) -> Path:
    target = "aarch64-apple-ios" if platform == "device" else "aarch64-apple-ios-sim"
    return host / f"crates/gpui-dotnet/target/{target}/debug/libgpui_dotnet.a"


def stage(root: Path, host: Path, compiler: Path, platform: str) -> Path:
    name = {"simulator": "moonbit-stage", "device": "moonbit-device-stage",
            "desktop": "moonbit-desktop-stage"}[platform]
    destination = root / "artifacts" / name
    stage_module(root / "examples/counter", destination, compiler, root)
    adapter = Path(__file__).resolve().parent
    for source in (adapter / "moonbit").iterdir():
        if source.is_file():
            shutil.copyfile(source, destination / source.name)
    generate(host, destination / "gpui_native.g.h")
    semantic = (host / "crates/gpui-dotnet/src/semantic.g.rs").read_text()
    schema = re.search(r"pub const SCHEMA_HASH: u64 = (0x[0-9A-Fa-f]+|\d+);", semantic)
    revision = subprocess.run(["git", "-C", str(host), "rev-parse", "HEAD"],
                              capture_output=True, text=True)
    info = {"adapter": "gpui_dotnet", "abi_version": 1,
            "schema_hash": schema[1] if schema else None,
            "host_revision": revision.stdout.strip() if revision.returncode == 0 else None}
    (destination / "host-info.json").write_text(json.dumps(info, indent=2) + "\n")
    return destination
