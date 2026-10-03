"""Renderer-independent Apple app packaging, signing and launch helpers."""
import json
from pathlib import Path
import plistlib
import shutil
import subprocess

from .process import execute


def read_bundle_id(app):
    with (app / "Info.plist").open("rb") as stream:
        return plistlib.load(stream)["CFBundleIdentifier"]


def build_app(destination, generated, compiler, platform, sources, includes,
              libraries, frameworks, bundle_id, display_name="MoonBit mobile"):
    sdk = "iphoneos" if platform == "device" else "iphonesimulator"
    app = destination / "MoonMobile.app"
    app.mkdir()
    launchers = []
    for index, source in enumerate(sources):
        obj = destination / f"objects/launcher-{index}.o"
        include_flags = [arg for path in includes for arg in ("-I", path)]
        execute([compiler, "-fobjc-arc", "-Wall", "-Wextra", "-Werror", *include_flags,
                 "-c", source, "-o", obj])
        launchers.append(obj)
    framework_flags = [arg for name in frameworks for arg in ("-framework", name)]
    execute([compiler, *launchers, *generated, *libraries, "-ObjC", "-lc++", "-lm",
             "-Wl,-dead_strip", *framework_flags, "-o", app / "MoonMobile"])
    sdk_version = execute(["xcrun", "--sdk", sdk, "--show-sdk-version"], capture=True).strip()
    info = {
        "CFBundleExecutable": "MoonMobile", "CFBundleIdentifier": bundle_id,
        "CFBundleName": "MoonMobile", "CFBundleDisplayName": display_name,
        "CFBundlePackageType": "APPL", "CFBundleVersion": "1", "CFBundleShortVersionString": "0.1.0",
        "MinimumOSVersion": "16.0", "CFBundleSupportedPlatforms": ["iPhoneOS" if platform == "device" else "iPhoneSimulator"],
        "DTPlatformName": sdk, "DTSDKName": sdk + sdk_version,
        "UIDeviceFamily": [1, 2], "LSRequiresIPhoneOS": True,
        "UILaunchScreen": {}, "UISupportedInterfaceOrientations": ["UIInterfaceOrientationPortrait"],
        "UIApplicationSceneManifest": {
            "UIApplicationSupportsMultipleScenes": False,
            "UISceneConfigurations": {"UIWindowSceneSessionRoleApplication": [{
                "UISceneConfigurationName": "Default Configuration",
                "UISceneDelegateClassName": "SceneDelegate",
            }]},
        },
    }
    with (app / "Info.plist").open("wb") as stream:
        plistlib.dump(info, stream)
    if platform == "simulator":
        execute(["codesign", "--force", "--sign", "-", app])
    else:
        print("Device app linked successfully; unsigned. Supply --team or --sign-identity/--profile to sign it.")
    return app


def sign_device(app, identity, profile):
    """Use an explicitly supplied development profile, without provisioning network calls."""
    bundle_id = read_bundle_id(app)
    profile = profile.expanduser().resolve(strict=True)
    data = subprocess.run(["security", "cms", "-D", "-i", str(profile)], check=True,
                          stdout=subprocess.PIPE).stdout
    provisioning = plistlib.loads(data)
    entitlements = provisioning["Entitlements"]
    app_id = entitlements.get("application-identifier", "")
    prefix = provisioning["ApplicationIdentifierPrefix"][0] + "."
    expected = prefix + bundle_id
    if app_id != expected and not (app_id.endswith("*") and expected.startswith(app_id[:-1])):
        raise RuntimeError(f"Provisioning profile does not cover {bundle_id}")
    from datetime import datetime, timezone
    expiry = provisioning["ExpirationDate"].replace(tzinfo=timezone.utc)
    if expiry <= datetime.now(timezone.utc):
        raise RuntimeError("Provisioning profile has expired")
    if not provisioning.get("ProvisionedDevices") or not entitlements.get("get-task-allow"):
        raise RuntimeError("Supply an iOS development profile with provisioned devices")
    entitlements = dict(entitlements)
    entitlements["application-identifier"] = expected
    if "keychain-access-groups" in entitlements:
        entitlements["keychain-access-groups"] = [
            group.replace(prefix + "*", expected) for group in entitlements["keychain-access-groups"]]
    path = app.parent / "device-entitlements.plist"
    with path.open("wb") as stream:
        plistlib.dump(entitlements, stream)
    shutil.copyfile(profile, app / "embedded.mobileprovision")
    execute(["codesign", "--force", "--sign", identity, "--entitlements", path,
             "--generate-entitlement-der", app])
    execute(["codesign", "--verify", "--strict", app])


def xcode_sign(app, team, device, project, derived):
    """Provision and sign the prebuilt app using the caller's explicit Xcode team."""
    bundle_id = read_bundle_id(app)
    execute(["xcodebuild", "-quiet", "-hideShellScriptEnvironment", "-project",
             project, "-scheme", "MoonMobile", "-configuration", "Debug",
             "-destination", "id=" + device, "-allowProvisioningUpdates",
             "-allowProvisioningDeviceRegistration", "DEVELOPMENT_TEAM=" + team,
             "MOON_MOBILE_APP_DIR=" + str(app), "MOON_MOBILE_BUNDLE_ID=" + bundle_id, "-derivedDataPath", derived, "build"])
    signed = derived / "Build/Products/Debug-iphoneos/MoonMobile.app"
    execute(["codesign", "--verify", "--strict", signed])
    return signed


def device_run(app, device, console=False):
    bundle_id = read_bundle_id(app)
    execute(["xcrun", "devicectl", "device", "install", "app", "--device", device, app])
    args = ["xcrun", "devicectl", "device", "process", "launch", "--device", device,
            "--terminate-existing"]
    if console:
        args.append("--console")
    execute([*args, bundle_id])


def simulator_run(app, device, logs):
    bundle_id = read_bundle_id(app)
    devices = json.loads(execute(["xcrun", "simctl", "list", "devices", "available", "--json"], capture=True))
    available = [item for group in devices["devices"].values() for item in group]
    if device:
        selected = next((item for item in available if device in (item["udid"], item["name"])), None)
    else:
        selected = next((item for item in available if item["state"] == "Booted"), None)
        selected = selected or next((item for item in available if item["name"].startswith("iPhone")), None)
    if not selected:
        raise RuntimeError("No available iOS Simulator; supply --device NAME_OR_UDID")
    udid = selected["udid"]
    if selected["state"] != "Booted":
        execute(["xcrun", "simctl", "boot", udid])
    developer = Path(execute(["xcode-select", "-p"], capture=True).strip())
    simulator = developer / "Applications/Simulator.app"
    hub = developer.parent / "Applications/DeviceHub.app"
    if simulator.exists():
        execute(["open", "-a", simulator, "--args", "-CurrentDeviceUDID", udid])
    elif hub.exists():
        execute(["open", "-a", hub])
    execute(["xcrun", "simctl", "bootstatus", udid, "-b"])
    execute(["xcrun", "simctl", "install", udid, app])
    execute(["xcrun", "simctl", "launch", "--terminate-running-process",
             "--stdout=" + str(logs / "simulator-stdout.log"),
             "--stderr=" + str(logs / "simulator-stderr.log"), udid, bundle_id])
