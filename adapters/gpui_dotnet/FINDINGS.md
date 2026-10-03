# GPUI.NET-specific findings

These findings concern the renderer/semantic adapter. Shared compiler/runtime
findings live in [docs/FINDINGS.md](../../docs/FINDINGS.md).

## ABI compatibility

The examined `mbt` branch frontend uses ABI 8 and `GpuiDotnetApiV3`. The
[pinned mobile host](https://github.com/akeit0/gpui-dotnet/commit/31420b25a99479d3169f4e922ca7a5bf1b09ffce)
exposes ABI 1 and `GpuiDotnetApiV1`, with semantic hash
`0x177F52C11588A433`. Changing the old frontend's loading mechanism alone cannot
make those table layouts compatible.

This PoC implements the counter surface against ABI 1. It generates a C header
and semantic constants from the selected host's `abi.rs` and `semantic.g.rs`.
The parser admits the observed fixed-width records/extern-C callback aliases;
it is not a general Rust header generator.

Startup compares the ABI version, table prefix size, schema hash and all six
required pointers against the actual statically linked host. No dynamic
library loading is used. Host source and archive must come from the same build.

## Embedded GPUI and application lifetime

`ios/host.m` implements the shared `mobile_host.h` interface.
`gpui_ios_set_embedded()` makes GPUI startup return to UIKit. The adapter calls
the counter's C export `gpui_moonbit_start()` after Moon runtime initialization
and returns GPUI's view controller to the shared safe-area container.

The MoonBit application root and capturing closure registry remain live after
startup returns. Non-capturing C dispatch functions service later render/click
callbacks. The adapter forwards layout, frame and active/background events to
GPUI. It supports one application and one window, both ID 1; restart/teardown is
not implemented.

## Semantic encoding

An ABI-1 Button uses UTF-8 data as its identity key and displays a Text child.
Using only label data produces an empty button, so the example constructs a
keyed Button with a Text child. Explicit 100% width/height make the root fill the
safe-area bounds.

The native host owns render arenas. The C builder counts all node/operation/edge/
UTF-8 capacity requirements even when supplied buffers have zero capacity,
without writing outside those buffers. An insufficient arena requests a retry.
The handler registry changes only after a frame completes, preserving committed
callbacks during growth retries. Successful frames pass native validation.

Render closures must be deterministic; event handlers mutate the counter and
request native invalidation. Frames and Elements have current-render lifetime.
List/menu/control/dynamic frontend callbacks are outside this PoC surface and
return errors.

## Adapter checks

The fake ABI-1 host runs the actual compiled MoonBit counter and verifies:

- callback lifetime after embedded startup returns;
- count changes, native invalidation and accepted redraws;
- exact arena growth followed by a successful retry;
- invalid token and worker-thread rejection;
- null API, undersized table, wrong ABI/hash and missing-entry rejection.

The [validation record](../../docs/VALIDATION.md) distinguishes simulator,
physical-device and fake-host evidence. Native Rust host behavior is not covered
by the fake host; it is exercised through the actual application launch.
