"""Regression checks that do not require Moon, Xcode, or a GPUI checkout."""
from datetime import datetime, timedelta
import json
from pathlib import Path
import plistlib
import tempfile
import unittest
from unittest.mock import patch

from tools.environment import DEFAULT_BUNDLE_ID, load_settings, toolchain_environment
from tools.shared.apple import device_run, sign_device, xcode_sign
from tools.shared.moon import MARKER, stage_module


class BuildSupportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.host = self.root / "host"
        self.host.mkdir()

    def config(self, values):
        path = self.root / "moon-mobile.local.json"
        path.write_text(json.dumps(values))
        return path

    def test_public_defaults_and_missing_host(self):
        with self.assertRaisesRegex(ValueError, "setup.py"):
            load_settings(self.root, environ={})
        settings = load_settings(self.root, overrides={"host_root": self.host}, environ={})
        self.assertEqual(settings.bundle_id, DEFAULT_BUNDLE_ID)
        self.assertIsNone(settings.archive("device"))

    def test_repo_local_defaults_and_toolchain_override(self):
        host = self.root / ".deps/gpui-dotnet"
        host.mkdir(parents=True)
        self.assertEqual(load_settings(self.root, environ={}).host_root, host)
        home = self.root / ".tools/moon"
        (home / "bin").mkdir(parents=True)
        (home / "bin/moon").touch()
        env = toolchain_environment(self.root, {"PATH": "/usr/bin"})
        self.assertEqual(env["MOON_HOME"], str(home))
        self.assertEqual(env["PATH"], str(home / "bin") + ":/usr/bin")
        custom = self.root / "custom-moon"
        (custom / "bin").mkdir(parents=True)
        (custom / "bin/moon").touch()
        env = toolchain_environment(self.root, {"MOON_HOME": str(custom), "PATH": "/usr/bin"})
        self.assertEqual(env["MOON_HOME"], str(custom))
        self.assertTrue(env["PATH"].startswith(str(custom / "bin")))

    def test_precedence_and_config_relative_paths(self):
        self.config({"host_root": "host", "bundle_id": "test.file.app",
                     "device_archive": "archives/device.a"})
        env = {"MOON_MOBILE_BUNDLE_ID": "test.env.app"}
        settings = load_settings(self.root, environ=env)
        self.assertEqual(settings.host_root, self.host)
        self.assertEqual(settings.device_archive, self.root / "archives/device.a")
        self.assertEqual(settings.bundle_id, "test.env.app")
        settings = load_settings(self.root, environ=env,
                                 overrides={"bundle_id": "test.cli.app"})
        self.assertEqual(settings.bundle_id, "test.cli.app")

    def test_config_rejects_typo_or_implicit_signing(self):
        for values in ({"host_root": "host", "team": "SECRET"},
                       {"host_root": 42}, [], {"host_root": ""}):
            with self.subTest(values=values):
                self.config(values)
                with self.assertRaises(ValueError):
                    load_settings(self.root, environ={})
        self.config({"host_root": "host", "bundle_id": "invalid/id"})
        with self.assertRaisesRegex(ValueError, "reverse-DNS"):
            load_settings(self.root, environ={})

    def test_staging_preserves_source_and_rejects_unsafe_outputs(self):
        source = self.root / "source"
        source.mkdir()
        package = 'pkgtype(kind: "foreign_library")\n'
        (source / "moon.pkg").write_text(package)
        output = self.root / "output"
        stage_module(source, output, Path("/clang path"), self.root)
        self.assertIn('"/clang path"', (output / "moon.pkg").read_text())
        self.assertEqual((source / "moon.pkg").read_text(), package)
        (output / "stale.c").write_text("old")
        stage_module(source, output, Path("/clang"), self.root)
        self.assertFalse((output / "stale.c").exists())
        (output / MARKER).unlink()
        with self.assertRaisesRegex(RuntimeError, "unmarked"):
            stage_module(source, output, Path("/clang"), self.root)
        link = self.root / "link"
        link.symlink_to(output, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, "escapes"):
            stage_module(source, link, Path("/clang"), self.root)
        with self.assertRaisesRegex(RuntimeError, "escapes"):
            stage_module(source, self.root.parent / "outside", Path("/clang"), self.root)

    def app(self):
        app = self.root / "MoonMobile.app"
        app.mkdir()
        (app / "Info.plist").write_bytes(plistlib.dumps({"CFBundleIdentifier": "test.custom.app"}))
        return app

    def test_launch_and_xcode_sign_use_built_bundle_id(self):
        app = self.app()
        with patch("tools.shared.apple.execute") as execute:
            device_run(app, "DEVICE")
            self.assertEqual(execute.call_args.args[0][-1], "test.custom.app")
            xcode_sign(app, "TEAM", "DEVICE", self.root / "Signing.xcodeproj", self.root / "derived")
            command = execute.call_args_list[-2].args[0]
            self.assertIn("MOON_MOBILE_BUNDLE_ID=test.custom.app", command)

    def test_manual_profile_validates_configured_bundle_before_signing(self):
        app = self.app()
        profile = self.root / "profile.mobileprovision"
        profile.write_bytes(b"placeholder")
        data = {"ApplicationIdentifierPrefix": ["TEAM"],
                "ExpirationDate": datetime.utcnow() + timedelta(days=1),
                "ProvisionedDevices": ["DEVICE"],
                "Entitlements": {"application-identifier": "TEAM.other.app",
                                 "get-task-allow": True}}
        with patch("tools.shared.apple.subprocess.run") as run, patch("tools.shared.apple.execute") as execute:
            run.return_value.stdout = plistlib.dumps(data)
            with self.assertRaisesRegex(RuntimeError, "test.custom.app"):
                sign_device(app, "IDENTITY", profile)
            execute.assert_not_called()
            self.assertFalse((app / "embedded.mobileprovision").exists())
            data["Entitlements"].update({"application-identifier": "TEAM.*",
                                         "keychain-access-groups": ["TEAM.*"]})
            run.return_value.stdout = plistlib.dumps(data)
            sign_device(app, "IDENTITY", profile)
            entitlements = plistlib.loads((self.root / "device-entitlements.plist").read_bytes())
            self.assertEqual(entitlements["application-identifier"], "TEAM.test.custom.app")
            self.assertEqual(entitlements["keychain-access-groups"], ["TEAM.test.custom.app"])


if __name__ == "__main__":
    unittest.main()
