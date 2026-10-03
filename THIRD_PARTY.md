# Dependency notes

Code specific to this repository uses the standard [Unlicense](https://unlicense.org/)
statement in `UNLICENSE`. That choice covers the shared build/hosting code,
GPUI adapter, counter example and tests written for this repository. It does
not change the terms of external dependencies or generated/linked dependency code.

[GPUI.NET](https://github.com/akeit0/gpui-dotnet) is an external build input. This repository does not vendor its Rust
source, prebuilt archives, generated ABI declarations or its dependencies.
The tested checkout contains an MIT `LICENSE` and a `NOTICE` describing its
GPUI Component/gpui-base references. Retain and review that project's license and
notice when preparing any distribution containing its code or linked archives.

MoonBit compiler, core modules and runtime sources are supplied by the installed
toolchain, not copied into this repository. Runtime sources and core module code
are compiled into the application. Review the terms supplied with the selected
toolchain before distributing application binaries.

Xcode/iOS SDKs and Apple signing material are local development inputs. Generated
apps, SDK files, provisioning profiles, certificates and private keys are excluded
from this repository. Source licensing alone does not describe the terms of
every component in a linked application.
