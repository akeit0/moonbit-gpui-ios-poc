# Architecture

## Source boundaries

`tools/setup.py` prepares pinned toolchain/host inputs within the repo; it does not
read an existing developer checkout. `tools/moonbit.py` is the counter/GPUI composition entry point. It resolves local
settings, chooses a target, stages the example with the adapter, and invokes the
shared build functions. The shared functions accept paths, compiler, libraries,
frameworks and bundle ID as inputs; they do not import the GPUI adapter.

| Layer | Files | Dependency boundary |
| --- | --- | --- |
| Environment | `tools/environment.py`, optional local JSON | Resolves repo defaults/overrides and bundle ID; no signing defaults |
| Moon build | `tools/shared/moon.py` | Stages a module and consumes the installed compiler plan |
| Apple build | `tools/shared/apple.py`, compiler wrappers | Packages, signs and launches the supplied native app |
| UIKit host | `shared/ios/main.m`, `mobile_host.h` | Calls a small renderer interface on the main thread |
| GPUI adapter | `adapters/gpui_dotnet/` | Implements that interface and the GPUI ABI-1 semantic frontend |
| Example | `examples/counter/` | Owns the counter model and UI using the GPUI frontend |

`adapters/gpui_dotnet/build.py` assembles the example and adapter into a flat,
disposable Moon module, generates ABI declarations from the selected host, and
records its revision/schema. The checked-in example package declares the
adapter's native stubs; the example is intended to be built through the entry
point, not directly through `moon build`. This is a source split, not a published
Moon package or a stable multi-renderer plugin API.

## Runtime path

```text
shared UIKit AppDelegate / SceneDelegate
    | mobile_host_* interface + moonbit_init()
    v
GPUI adapter ios/host.m
    | gpui_moonbit_start()
    v
MoonBit counter + App / render / click closures
    | native C backend
    v
GPUI bridge.c + arena.c + commands.c
    | gpui_dotnet_get_api(1), validated function table
    v
existing libgpui_dotnet.a → GPUI / Metal UIViewController
    ^ returned through mobile_host_view_controller()
```

The shared UIKit host owns the scene, safe-area container and display link.
The GPUI adapter owns window lookup, renderer layout/frame requests, lifecycle
forwarding and the sample's background color. The shared iOS runtime shim adapts
the installed Moon runtime's entropy call without modifying that runtime.

Simulator and device builds use the same source with separate staging directories
and matching SDK/compiler/archive targets. Shared Apple packaging accepts the app
identifier from resolved settings. Signing and launch read that identifier from
the built Info.plist. The signing-only Xcode target copies the existing executable
and processes its Info.plist; it does not compile MoonBit or Rust. Its bundle ID
is passed as a build setting, and the copy phase declares sandbox inputs/outputs.

## GPUI frontend lifetime

The adapter supports one application and one window, both using ID 1.
`App::start_embedded()` registers three non-capturing C dispatch functions.
Capturing callbacks remain in a MoonBit closure registry. Unsupported list, menu,
control and dynamic callbacks return an error.

The native host owns each render arena. The C builder writes bounded flat nodes,
operations, child edges and UTF-8 data. If buffers are too small, it counts the
full requirements without out-of-bounds writes and requests a retry. Successful
renders pass the native validator. The MoonBit handler registry is replaced only
after a frame completes, so growth retries preserve the previous callbacks.
Native validation failures stop the sample's render path.

Frames and Elements are valid only inside the current render closure. Render
closures must be deterministic and must not mutate application state. Event
handlers mutate the `Ref` model and invalidate the window. Rendering reconstructs
the entire tree; there is no retained MoonBit View tree or reactive scheduler.

All startup/callback work runs on the UIKit main thread. Process state remains
alive after embedded startup returns. Restart, teardown/reinitialization and
multiple simultaneous windows are not implemented. The static bridge does not
use dynamic library loading.

## Reuse

A different native renderer can reuse `tools/shared/` and `shared/ios/` by supplying
its own implementation of `mobile_host.h`, app export, frontend sources and link
inputs. It must also provide a composition entry point/staging policy. Only the
GPUI adapter has been implemented and tested. Its ABI parser, closure registry,
semantic arena encoding and link frameworks remain adapter-specific.
