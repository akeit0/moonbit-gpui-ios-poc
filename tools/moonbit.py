#!/usr/bin/env python3
"""Build the MoonBit counter using shared iOS support and the GPUI.NET adapter."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
# This entry point also works when invoked from outside the repository.
sys.path.insert(0, str(ROOT))

from adapters.gpui_dotnet import build as gpui
from tools.environment import load_settings, toolchain_environment
from tools.shared.apple import build_app, device_run, sign_device, simulator_run, xcode_sign
from tools.shared.moon import compile_objects
from tools.shared.process import execute


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["ios-stage", "ios-objects", "ios-build", "ios-run", "test"])
    parser.add_argument("--config", type=Path, help="Settings JSON; defaults to ignored moon-mobile.local.json")
    parser.add_argument("--bundle-id", help="App identifier; default org.example.moonmobile")
    parser.add_argument("--host-root", type=Path, help="GPUI.NET mobile ABI-1 source checkout")
    parser.add_argument("--archive", type=Path, help="Existing ABI-1 arm64 Rust archive matching --platform")
    parser.add_argument("--platform", choices=["simulator", "device"], default="simulator")
    parser.add_argument("--sign-identity", help="Device signing identity name or certificate SHA-1")
    parser.add_argument("--profile", type=Path, help="iOS development .mobileprovision for the configured bundle ID")
    parser.add_argument("--team", help="Xcode development team ID; allows automatic device provisioning")
    parser.add_argument("--device", help="Simulator name/UDID, or physical-device UDID for device signing/run")
    parser.add_argument("--console", action="store_true", help="Attach to device app output until it exits (ios-run --platform device)")
    args = parser.parse_args()
    if bool(args.sign_identity) != bool(args.profile):
        parser.error("--sign-identity and --profile must be supplied together")
    if (args.sign_identity or args.profile or args.team) and (args.command not in ("ios-build", "ios-run") or args.platform != "device"):
        parser.error("device signing options require ios-build/ios-run --platform device")
    if args.team and (args.profile or args.sign_identity):
        parser.error("choose automatic --team signing or manual --profile/--sign-identity")
    if args.team and not args.device:
        parser.error("--team requires --device with the physical-device UDID")
    if args.command == "ios-run" and args.platform == "device" and (not args.device or not (args.team or args.profile)):
        parser.error("device ios-run requires --device and either --team or manual signing options")
    if args.console and (args.command != "ios-run" or args.platform != "device"):
        parser.error("--console requires ios-run --platform device")
    try:
        settings = load_settings(ROOT, config=args.config,
                                 overrides={"host_root": args.host_root, "bundle_id": args.bundle_id})
    except (ValueError, OSError) as error:
        parser.error(str(error))
    platform = "desktop" if args.command == "test" else args.platform
    os.environ.update(toolchain_environment(ROOT))
    compiler = (Path("/usr/bin/clang") if platform == "desktop" else
                ROOT / f"tools/shared/apple-clang-ios-{'device' if platform == 'device' else 'sim'}")
    # Fail before generating C if a link input is missing.
    archive = None
    if args.command in ("ios-build", "ios-run"):
        archive = (args.archive or settings.archive(platform) or
                   gpui.default_archive(settings.host_root, platform)).expanduser().resolve(strict=True)
    destination = gpui.stage(ROOT, settings.host_root, compiler, platform)
    if args.command == "ios-stage":
        print(destination)
        return
    generated = compile_objects(destination, compiler,
                                None if platform == "desktop" else ROOT / "shared/ios/include")
    if args.command == "test":
        binary = destination / "bridge-test"
        execute([compiler, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
                 "-I", destination, ROOT / "adapters/gpui_dotnet/tests/bridge_test.c",
                 *generated, "-lm", "-o", binary])
        for mode in range(6):
            execute([binary, mode])
    elif args.command == "ios-objects":
        print(destination)
    else:
        app = build_app(destination, generated, compiler, platform,
                        [ROOT / "shared/ios/main.m", ROOT / "adapters/gpui_dotnet/ios/host.m"],
                        [ROOT / "shared/ios"], [archive], gpui.FRAMEWORKS,
                        settings.bundle_id, "MoonBit + GPUI")
        if args.team:
            app = xcode_sign(app, args.team, args.device,
                             ROOT / "shared/ios/Signing.xcodeproj",
                             ROOT / "artifacts/device-signing")
        elif args.profile:
            sign_device(app, args.sign_identity, args.profile)
        if args.command == "ios-run":
            if platform == "device":
                device_run(app, args.device, args.console)
            else:
                simulator_run(app, args.device, ROOT / "artifacts")
        print(app)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print(f"Build failed: {error}", file=sys.stderr)
        sys.exit(1)
