# GPUI.NET mobile adapter

This adapter targets the mobile host's ABI 1 and `GpuiDotnetApiV1`. It is
incompatible with the ABI-8 `mbt` frontend. It implements the small counter
surface and single embedded window rather than the full GPUI frontend.

See [GPUI-specific findings](FINDINGS.md) for ABI compatibility and runtime behavior.

| Source | Role |
| --- | --- |
| `build.py` | Staging composition, archive target paths, link frameworks and host metadata |
| `generate_abi.py` | Conservative generation from host Rust ABI/schema declarations |
| `moonbit/ffi.mbt`, `ui.mbt` | Foreign calls, semantic builder and rooted application/handler registry |
| `moonbit/bridge.c`, `arena.c`, `commands.c` | Static ABI dispatch, bounded arena encoding and application commands |
| `ios/host.m` | GPUI implementation of the shared UIKit renderer interface |
| `tests/bridge_test.c` | Fake ABI-1 host exercising the actual counter |

Setup fetches [akeit0/gpui-dotnet](https://github.com/akeit0/gpui-dotnet) at commit
`31420b25a99479d3169f4e922ca7a5bf1b09ffce` into `.deps/gpui-dotnet`.
To override setup, supply a source checkout containing `crates/gpui-dotnet/src/abi.rs` and
`semantic.g.rs`, plus its matching Rust archive:

- Simulator: `crates/gpui-dotnet/target/aarch64-apple-ios-sim/debug/libgpui_dotnet.a`
- Device: `crates/gpui-dotnet/target/aarch64-apple-ios/debug/libgpui_dotnet.a`

The [validation record](../../docs/VALIDATION.md) names the known working revision.
The host source is read-only. The ABI parser is deliberately limited to the
observed fixed-width records and extern-C callbacks; unsupported declarations
fail generation. Startup validates table size, ABI version, schema hash and all
required entries against the actual linked library.

The example and adapter sources are merged only in ignored staging. Generated
`gpui_native.g.h` and `semantic.g.mbt` are not vendored. A semantic Button holds
its identity key and displays a Text child. Render frames have arena lifetime,
and callbacks remain rooted after embedded startup returns.

From the repository root:

```sh
python3 tools/moonbit.py test
```

This checks the real generated MoonBit application against a fake native host;
it does not test Metal, UIKit or native GPUI implementation behavior.
