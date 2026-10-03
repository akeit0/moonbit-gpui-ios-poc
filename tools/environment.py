"""Resolve machine-specific settings without putting them in shared build code."""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re

ENV_KEYS = {
    "host_root": "MOON_MOBILE_HOST_ROOT",
    "bundle_id": "MOON_MOBILE_BUNDLE_ID",
    "simulator_archive": "MOON_MOBILE_SIMULATOR_ARCHIVE",
    "device_archive": "MOON_MOBILE_DEVICE_ARCHIVE",
}
DEFAULT_BUNDLE_ID = "org.example.moonmobile"


@dataclass(frozen=True)
class Settings:
    host_root: Path
    bundle_id: str
    simulator_archive: Path = None
    device_archive: Path = None

    def archive(self, platform):
        return self.device_archive if platform == "device" else self.simulator_archive


def load_settings(root: Path, *, config: Path = None, overrides=None, environ=None):
    """CLI > environment > JSON > defaults; JSON paths are relative to that file."""
    explicit = config is not None
    config = (config or root / "moon-mobile.local.json").expanduser().resolve()
    values = {}
    if explicit or config.exists():
        values = json.loads(config.read_text())
        if not isinstance(values, dict) or set(values) - set(ENV_KEYS):
            raise ValueError("Config must be an object containing only: " + ", ".join(ENV_KEYS))
        if any(not isinstance(value, str) or not value.strip() for value in values.values()):
            raise ValueError("Config settings must be nonempty strings")
        for key in ("host_root", "simulator_archive", "device_archive"):
            if key in values:
                path = Path(values[key]).expanduser()
                values[key] = str(path if path.is_absolute() else config.parent / path)
    env = os.environ if environ is None else environ
    values.update({key: env[name] for key, name in ENV_KEYS.items() if env.get(name)})
    values.update({key: value for key, value in (overrides or {}).items() if value is not None})
    if not values.get("host_root"):
        values["host_root"] = root / ".deps/gpui-dotnet"
        if not Path(values["host_root"]).is_dir():
            raise ValueError("Run python3 tools/setup.py first, or supply --host-root")
    bundle_id = values.get("bundle_id", DEFAULT_BUNDLE_ID)
    if not re.fullmatch(r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", bundle_id):
        raise ValueError("bundle_id must be a reverse-DNS identifier with at least two components")
    host = Path(values["host_root"]).expanduser().resolve(strict=True)
    if not host.is_dir():
        raise ValueError("host_root must be a directory")
    archives = {key: Path(values[key]).expanduser().resolve() if values.get(key) else None
                for key in ("simulator_archive", "device_archive")}
    return Settings(host, bundle_id, **archives)


def toolchain_environment(root: Path, environ=None):
    """Prefer the repo-local compiler; an explicit MOON_HOME overrides it."""
    environment = dict(os.environ if environ is None else environ)
    local = root / ".tools/moon"
    home = Path(environment["MOON_HOME"]).expanduser().resolve() if environment.get("MOON_HOME") else local
    if (home / "bin/moon").is_file():
        environment["MOON_HOME"] = str(home)
        environment["PATH"] = str(home / "bin") + os.pathsep + environment.get("PATH", "")
    return environment
