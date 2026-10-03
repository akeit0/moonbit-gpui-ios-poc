# MoonBit iOS C-backend findings

These findings describe the shared MoonBit/Apple build support. Renderer-specific
behavior is documented in the [GPUI.NET findings](../adapters/gpui_dotnet/FINDINGS.md).
Tested versions and runtime evidence are in [validation](VALIDATION.md).

## Compiler pipeline

With `MOONBIT_NEW_NATIVE=0` and `MOONBIT_ALLOCATOR=system`, the tested release plan
contains:

1. `moonc build-package` produces `.core` IR.
2. `moonc link-core` produces application C.
3. Clang compiles foreign stubs and distributed runtime C sources.
4. Moon normally links generated C directly into a native executable.

The shared helper runs `moon check`, then obtains
`moon build --target native --release --dry-run`. It runs the compiler steps and
preserves the discovered C flags, including `-fwrapv`, `-fno-strict-aliasing`,
`-O2` and the system allocator macro. Apple compiler wrappers select the iOS
target. Moon's final linker command is not executed; Apple clang links the supplied
app/native inputs.

The dry run does not write `all_pkgs.json`; the helper reuses metadata from
`moon check`. Moon also probes an archiver beside a compiler wrapper. The
`tools/shared/ar` wrapper satisfies that discovery while the archive steps
themselves are skipped. The helper consumes the observed toolchain's plan format,
not a stable Moon compiler-driver API.

## Runtime objects must match the Apple platform

The toolchain's distributed `libmoonbitrun.o` is arm64 **macOS**, with Mach-O
platform 1 and minimum OS 11.0. It cannot be reused for an arm64 iOS app merely
because its CPU architecture matches.

The shared build compiles distributed runtime C sources for the chosen SDK.
These supply allocation/drop helpers, encoding/layout functions and
`moonbit_println`. Final iOS linking uses none of the toolchain's macOS
`.o`/`.a` runtime assets.

Two runtime options are removed:

- `MOONBIT_USE_SIMDUTF`: use scalar UTF code instead of shipped macOS SIMD objects.
- `MOONBIT_ALLOW_STACKTRACE`: avoid the distributed macOS `libbacktrace.a`.

No replacement allocator or language runtime was implemented.

## Entropy SDK adaptation

The tested distributed `env.c` includes `sys/random.h` and calls `getentropy`,
which this iOS SDK does not provide. Omitting that source breaks generated panic
paths that need `moonbit_println`.

`shared/ios/include/sys/random.h` supplies that entropy interface using
`SecRandomCopyBytes` and preserves the 256-byte limit. Installed runtime source
is unchanged. This narrow adaptation does not certify every `core/env` API for iOS.

## C exports and UIKit ownership

The tested compiler accepts `#export_name` on a function in a
`foreign_library` package and emits the named C symbol. Native foreign-library
packaging is unnecessary here: Apple clang compiles the generated C as an object.
UIKit calls `moonbit_init()` before dispatching the application export through
the renderer adapter.

The shared launcher owns `UIApplicationMain`, app/scene delegates, a safe-area
container and a `CADisplayLink`. It calls the `mobile_host.h` interface for
renderer startup, view-controller lookup, layout/frame requests and lifecycle
forwarding. The renderer must return from embedded startup and keep later
callbacks valid; how the GPUI adapter achieves this belongs in its own findings.

## Primary references

- [MoonBit FFI and exports](https://docs.moonbitlang.com/en/stable/language/ffi.html)
- [Moon package configuration](https://docs.moonbitlang.com/en/stable/toolchain/moon/package.html)
- [Moon compiler/allocator orchestration](https://github.com/moonbitlang/moon/blob/main/crates/moonutil/src/compiler_flags.rs)

The captured build plan and the pinned toolchain's artifacts are authoritative;
online documentation may describe another revision.
