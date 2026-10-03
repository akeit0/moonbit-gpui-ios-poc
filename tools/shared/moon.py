"""Stage a MoonBit module and compile its installed C-backend build plan."""
import json
import os
from pathlib import Path
import shlex
import shutil

from .process import execute

MARKER = ".moon-mobile-owned"


def stage_module(source: Path, destination: Path, compiler: Path, workspace: Path):
    if destination.is_symlink() or not destination.resolve().is_relative_to(workspace.resolve()):
        raise RuntimeError(f"Build directory escapes workspace: {destination}")
    if destination.exists():
        marker = destination / MARKER
        if marker.is_symlink() or not marker.is_file() or marker.read_text() != "moon-mobile\n":
            raise RuntimeError(f"Refusing to replace unmarked directory: {destination}")
        shutil.rmtree(destination)
    shutil.copytree(source, destination,
                    ignore=shutil.ignore_patterns("_build", ".mooncakes", ".DS_Store"))
    (destination / MARKER).write_text("moon-mobile\n")
    # The original module remains platform-neutral; only the disposable copy gets compilers.
    for path in destination.rglob("moon.pkg"):
        option = '"link": {"native": ' + json.dumps({
                "cc": str(compiler), "stub-cc": str(compiler),
                "stub-cc-flags": "-std=c11 -fPIC",
            }) + '}'
        source = path.read_text()
        if "options(" in source:
            source = source.replace("options(", "options(" + option + ",\n", 1)
        else:
            source += "\noptions(" + option + ")\n"
        path.write_text(source)
    return destination


def compile_objects(destination: Path, compiler: Path, ios_include: Path = None):
    environment = os.environ.copy()
    environment.update(MOONBIT_NEW_NATIVE="0", MOONBIT_ALLOCATOR="system", MOON_AR="/usr/bin/ar")
    moon_home = Path(environment.get("MOON_HOME", Path.home() / ".moon")).resolve()
    execute(["moon", "check", "--target", "native"], cwd=destination, env=environment)
    plan = execute(["moon", "build", "--target", "native", "--release", "--dry-run"],
                   cwd=destination, env=environment, capture=True)
    (destination / "build-plan.txt").write_text(plan)
    commands = [shlex.split(line.replace("$MOON_HOME", str(moon_home)))
                for line in plan.splitlines() if line.strip()]
    # Execute only the official compiler's IR/C steps. Moon never links the application.
    for args in commands:
        if Path(args[0]).name == "moonc":
            (destination / args[args.index("-o") + 1]).parent.mkdir(parents=True, exist_ok=True)
            if "-all-pkgs" in args:
                # --dry-run omits Moon's auxiliary metadata write. `check` produced it.
                metadata = next(destination.rglob("all_pkgs.json"))
                args[args.index("-all-pkgs") + 1] = str(metadata)
            execute(args, cwd=destination, env=environment)
    output = destination / "objects"
    output.mkdir()
    generated = []
    for args in commands:
        if Path(args[0]).name == "moonc":
            continue
        if not any(arg.endswith(".c") for arg in args):
            continue
        if "-c" in args:
            # Build distributed portable runtime sources for this SDK. Scalar UTF-8 avoids
            # the installed macOS-only SIMD objects; stack traces need a separate port.
            args = [arg for arg in args if arg not in ("-DMOONBIT_USE_SIMDUTF", "-DMOONBIT_ALLOW_STACKTRACE")]
            args[0] = str(compiler)
            if ios_include and any(arg.endswith("/runtime/env.c") for arg in args):
                args += ["-I", str(ios_include)]
            index = args.index("-o") + 1
            args[index] = str(output / Path(args[index]).name)
            execute(args, cwd=destination, env=environment)
            generated.append(Path(args[index]))
        else:
            sources = [arg for arg in args if arg.endswith(".c")]
            if not sources:
                continue
            # Preserve compiler flags from the installed Moon build, discard its link inputs.
            flags = []
            index = 1
            while index < len(args):
                arg = args[index]
                if arg == "-o":
                    index += 2
                    continue
                if arg.endswith((".c", ".a", ".o")) or arg.startswith("-l"):
                    index += 1
                    continue
                flags.append(arg)
                index += 1
            obj = output / (Path(sources[0]).stem + ".o")
            execute([compiler, *flags, "-c", sources[0], "-o", obj], cwd=destination, env=environment)
            generated.append(obj)
    if not generated:
        raise RuntimeError("Installed Moon build plan did not contain recognized C compiler steps")
    return generated
