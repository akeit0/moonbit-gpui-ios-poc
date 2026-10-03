# Setup details

## Inputs

`dependencies.lock.json` pins:

- [GPUI.NET](https://github.com/akeit0/gpui-dotnet) source commit
  `31420b25a99479d3169f4e922ca7a5bf1b09ffce`, exposing mobile ABI 1.
- Rust `1.98.0`.
- MoonBit compiler `0.10.14+7d59c7ec9`, with Moon
  `0.1.20260920`, and its matching core archive.
- SHA-256 hashes for the MoonBit/core downloads.

Moon download locations and core bundling follow the
[official installer](https://cli.moonbitlang.com/install/unix.sh);
setup performs those steps under this repo instead of changing shell startup
files or installing into a home-directory Moon installation.

## What setup changes

`python3 tools/setup.py`:

1. Checks Apple Silicon macOS, Xcode SDK access, Git, curl, Rustup and Cargo.
2. Downloads the pinned Moon/compiler archive and core sources into `.downloads/`
   and verifies their hashes.
3. Installs/bundles them in `.tools/moon`; the app build selects that installation.
4. Clones the public GPUI.NET Git URL into `.deps/gpui-dotnet` and checks out the
   exact commit with detached HEAD.
5. Installs the pinned toolchain/target through Rustup, then builds the native
   library with the host's committed Cargo lockfile.

Rustup and Cargo use their normal per-user toolchain/download caches.
`CARGO_TARGET_DIR` is explicitly set inside the dependency checkout, so an
inherited value cannot redirect the native archive into another workspace.
Setup builds native Rust only; its existing build script generates C# binding
source as a side effect, but no .NET installation or managed build is needed.

The default target is `aarch64-apple-ios-sim`. `--platform device` builds
`aarch64-apple-ios`; `--platform both` builds both. These match the adapter's
standard archive paths under `.deps/gpui-dotnet/crates/gpui-dotnet/target/`.

## Reruns and failures

Matching downloaded archives and the completed Moon installation are reused.
Cargo incrementally rebuilds the selected target. Setup never resets tracked
changes or switches an existing host checkout to a different revision.

If compilation fails, correct the reported prerequisite/dependency problem and
run setup again. An owned, interrupted Moon staging installation is recreated on
retry. Unrecognized tool directories and changed dependency checkouts are
preserved; move them aside intentionally before preparing a new one.

Versioned Moon archives depend on upstream retention; a pin does not guarantee
that its URL remains hosted forever. Retain the checksum-verified downloads for
repeat local setup. If upstream removes a pin, update/test the version and hashes
together rather than silently switching to `latest`.

For another Xcode installation, use the standard `DEVELOPER_DIR` environment
variable or `xcode-select`. This PoC fixes Apple target deployment minimums at
iOS 16; the observed runtime versions are listed in [validation](VALIDATION.md).
