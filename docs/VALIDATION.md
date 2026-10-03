# Tested environment

| Component | Tested value |
| --- | --- |
| Host source | [GPUI.NET](https://github.com/akeit0/gpui-dotnet), commit `31420b25a99479d3169f4e922ca7a5bf1b09ffce` |
| Host ABI / semantic hash | `1` / `0x177F52C11588A433` |
| Moon | `0.1.20260920`, revision `914d7da` |
| moonc | `0.10.14+7d59c7ec9` |
| Rust | `1.98.0` |
| Xcode / SDK | `27.0`, build `27A266a` / SDK 27.0 |
| Simulator | Apple Silicon, iPhone 18 Pro, iOS 27.0 |
| Physical device | iPhone 14 / Apple A15 / iOS 26.6 |
| Build minimum | iOS 16.0, arm64 |

The counter has displayed and handled real taps in the simulator and on the
physical device. Hardware logs confirmed Metal renderer initialization, startup
status 0 and counter redraws from 0 to 1 to 2. The fake-host checks verify the
actual compiled MoonBit counter, callback lifetime, arena growth/retry, state
updates, invalidation, thread rejection and incompatible ABI rejection.

The shared/adapter source split has passed simulator/device compilation and
development signing. Simulator startup/rendering has also been checked after
the split. Physical touch evidence was obtained before that split.

The standalone setup was run using downloads and a fresh public GitHub checkout,
without a personal config or a prebuilt archive from another workspace. Both
Rust targets compiled with the pinned toolchain and locked dependencies; the
simulator app built, launched and visibly displayed the counter with startup
status 0. The physical-device app also compiled. Setup then reran successfully
for both targets, reusing its own downloads/compiler and incremental artifacts.

Ten Python setup/config/staging/signing checks and all six fake-host modes passed.
This verifies the documented setup/build path on the tested machine; Rustup/Cargo
used their standard download caches. The standalone device app was not provisioned
or retested for touch, and has no personal signing defaults.

iOS 16 runtime behavior, x86_64 simulators, accessibility semantics, multiple
windows, restart/teardown and App Store distribution remain unverified.
