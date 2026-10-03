# moonbit-gpui-ios-poc

A proof of concept: MoonBit owns a counter's state, layout and button callback;
GPUI renders it through Metal in a UIKit application. Supports Apple Silicon
iOS Simulator and arm64 device builds.

The native host comes from **[akeit0/gpui-dotnet](https://github.com/akeit0/gpui-dotnet)**,
checked out at commit
[`31420b25a99479d3169f4e922ca7a5bf1b09ffce`](https://github.com/akeit0/gpui-dotnet/commit/31420b25a99479d3169f4e922ca7a5bf1b09ffce).
Setup clones that GitHub repo and uses a detached checkout of this exact commit.
It does not use a sibling checkout, a developer's home-directory project, or a
prebuilt archive from another workspace.

## Prerequisites

- Apple Silicon macOS, full Xcode, and an installed iOS simulator runtime.
  Open Xcode once to finish its installation and accept its license. Ensure
  `xcode-select -p` points to the Xcode developer directory.
- Python 3.9 or newer, Git and curl (available with Apple's development tools).
- [Rustup](https://www.rust-lang.org/tools/install) with `rustup` and `cargo` on
  `PATH`. Setup installs the pinned Rust toolchain and required iOS target.

No .NET workload is needed for this MoonBit app. Setup downloads its own MoonBit
compiler/runtime/core modules; an existing MoonBit installation is not required.

## Reproduce in the simulator

From the cloned repository:

```sh
python3 tools/setup.py
python3 tools/moonbit.py ios-run
```

The first command downloads the pinned MoonBit toolchain into `.tools/moon`,
clones GPUI.NET into `.deps/gpui-dotnet`, installs Rust 1.98.0's simulator target,
and builds its native archive with Cargo `--locked`. Downloads and first native
compilation can take several minutes. No personal config file is needed.

The second command compiles the counter and Moon runtime for iOS, links the new
archive, boots an available simulator, opens Simulator or Device Hub, and installs
and launches `artifacts/moonbit-stage/MoonMobile.app`. Tap **Tap me** to change
**Count: 0** to **Count: 1**.

Choose a simulator using `xcrun simctl list devices available`, then:

```sh
python3 tools/moonbit.py ios-run --device 'YOUR_SIMULATOR_NAME'
```

To build without launching:

```sh
python3 tools/moonbit.py ios-build
```

All dependency versions, source URLs and MoonBit archive hashes are in
[`dependencies.lock.json`](dependencies.lock.json). Setup is repeatable for
unchanged pins and refuses to overwrite a dependency checkout at another
revision or with tracked local changes.

## Physical device

Prepare the device Rust archive:

```sh
python3 tools/setup.py --platform device
```

Use `--platform both` to prepare both archives. Then build without provisioning:

```sh
python3 tools/moonbit.py ios-build --platform device
```

For install/launch, pair the phone, enable Developer Mode, and configure an Xcode
account. Use your own app identifier, team ID and device UDID:

```sh
python3 tools/moonbit.py ios-run --platform device \
  --bundle-id com.yourname.moonbitgpui \
  --team YOUR_TEAM_ID --device YOUR_DEVICE_UDID
```

Find the device identifier with `xcrun devicectl list devices`.
`--team` permits Xcode provisioning updates/device registration with Apple.
It signs the existing executable rather than compiling MoonBit/Rust through
Xcode. The signed output is
`artifacts/device-signing/Build/Products/Debug-iphoneos/MoonMobile.app`.
Nothing is uploaded.

Alternatively, supply an existing matching development profile:

```sh
python3 tools/moonbit.py ios-run --platform device \
  --bundle-id com.yourname.moonbitgpui --device YOUR_DEVICE_UDID \
  --sign-identity 'Apple Development: YOUR_IDENTITY' \
  --profile /path/to/MoonMobile.mobileprovision
```

Manual signing checks the app identifier, profile expiration and development
provisioning. The profile must include the chosen device. Output stays at
`artifacts/moonbit-device-stage/MoonMobile.app`. Use `ios-build` to sign without
installing; add `--console` to device `ios-run` to attach to app output.

## Source layout

| Part | Location |
| --- | --- |
| Shared MoonBit/Apple build support | `tools/shared/` |
| Shared UIKit host and runtime SDK shim | `shared/ios/` |
| GPUI.NET ABI/frontend/renderer adapter | `adapters/gpui_dotnet/` |
| Counter state, layout and callback | `examples/counter/` |
| Dependency setup | `tools/setup.py`, `dependencies.lock.json` |
| Environment resolution | `tools/environment.py` |

Shared code has no GPUI symbols or checkout paths. The example uses the adapter's
`App`/`Element` API. Staging assembles these sources into a disposable module;
this is not a published frontend package or a multi-renderer framework.

## Optional environment overrides

Default paths are relative to this repository: `.deps/gpui-dotnet` and
`.tools/moon`. To use a different host, archive or bundle ID, use CLI arguments
or copy `moon-mobile.example.json` to the ignored `moon-mobile.local.json`.

Settings precedence is **CLI > environment > JSON > repo defaults**.
JSON paths resolve beside that file; CLI/environment paths resolve from the
working directory. `--config PATH` selects another JSON file.

| JSON key | Environment variable |
| --- | --- |
| `host_root` | `MOON_MOBILE_HOST_ROOT` |
| `bundle_id` | `MOON_MOBILE_BUNDLE_ID` |
| `simulator_archive` | `MOON_MOBILE_SIMULATOR_ARCHIVE` |
| `device_archive` | `MOON_MOBILE_DEVICE_ARCHIVE` |

`--archive PATH` overrides the selected native archive. An explicit `MOON_HOME`
can select another installed Moon toolchain. Signing settings are explicit CLI
arguments and cannot be enabled through the config.

## Checks and details

```sh
python3 -m unittest discover -s tests -v
python3 tools/moonbit.py test
```

Python checks need no compiler. The fake-host check compiles the actual counter
and checks state changes, callbacks after startup returns, arena retries,
main-thread enforcement and ABI mismatch rejection.

Generated headers, C, objects, apps, logs, downloaded tools and dependency
checkouts are ignored. Keep source edits in `examples/`, `adapters/` and
`shared/`; each build refreshes its marked staging directory.
No CI or publishing configuration is included.

See [setup details](docs/SETUP.md), [architecture](docs/ARCHITECTURE.md),
[compiler findings](docs/FINDINGS.md), [tested environment](docs/VALIDATION.md)
and the [GPUI adapter](adapters/gpui_dotnet/README.md) / [GPUI-specific findings](adapters/gpui_dotnet/FINDINGS.md).
Repository-specific code uses the [Unlicense](UNLICENSE); external dependencies
retain their own terms described in [dependency notes](THIRD_PARTY.md).

This is a single-window PoC. App Store distribution, teardown/restart, full
frontend parity, accessibility coverage and minimum-version iOS 16 runtime
behavior are not verified.
