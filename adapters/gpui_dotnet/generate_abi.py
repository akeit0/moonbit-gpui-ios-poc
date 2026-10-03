"""Generate the admitted ABI-1 C contract from the supplied local Rust checkout."""
import re
from pathlib import Path


def generate(host: Path, output: Path):
    source = (host / "crates/gpui-dotnet/src/abi.rs").read_text()
    version = re.search(r"pub const ABI_VERSION: u32 = (\d+);", source)
    if not version or version[1] != "1":
        raise RuntimeError("This proof of concept requires the mobile host's ABI 1")
    records = re.findall(r"#\[repr\(C\)\]\s*(?:#\[[^\]]+\]\s*)*pub struct (\w+) \{([^}]+)\}", source)
    aliases = re.findall(r"pub type (\w+) =\s*unsafe extern \"C\" fn\((.*?)\) -> (\w+);", source, re.S)
    scalars = {"u8": "uint8_t", "u16": "uint16_t", "u32": "uint32_t", "u64": "uint64_t",
               "i32": "int32_t", "f32": "float"}
    admitted = {name for name, _ in records} | {name for name, _, _ in aliases}

    def c_type(rust):
        rust = rust.strip()
        if rust.startswith("*const "):
            return "const " + c_type(rust[7:]) + " *"
        if rust.startswith("*mut "):
            return c_type(rust[5:]) + " *"
        if rust.startswith("Option<") and rust.endswith(">"):
            name = rust[7:-1]
            if name not in {name for name, _, _ in aliases}:
                raise RuntimeError(f"Unsupported nullable ABI type: {rust}")
            return name
        if rust in scalars:
            return scalars[rust]
        if rust in admitted:
            return rust
        raise RuntimeError(f"Unsupported Rust ABI type: {rust}")

    if len(records) != len(re.findall(r"pub struct ", source)) or len(aliases) != len(re.findall(r"pub type ", source)):
        raise RuntimeError("Unrecognized Rust ABI declaration")
    lines = ["// Generated from the selected gpui-dotnet ABI; do not edit.",
             "#pragma once", "#include <stdint.h>", "#define GPUI_NATIVE_ABI_VERSION 1u"]
    lines += [f"typedef struct {name} {name};" for name, _ in records]
    for name, args, result in aliases:
        types = [c_type(arg) for arg in args.split(",") if arg.strip()]
        lines.append(f"typedef {c_type(result)} (*{name})({', '.join(types) or 'void'});")
    for name, fields in records:
        lines.append(f"struct {name} {{")
        for field in fields.split(","):
            match = re.fullmatch(r"\s*pub (\w+): (.+?)\s*", field, re.S)
            if not field.strip():
                continue
            if not match:
                raise RuntimeError(f"Unrecognized field: {field}")
            lines.append(f"    {c_type(match[2])} {match[1]};")
        lines.append("};")
    semantic = (host / "crates/gpui-dotnet/src/semantic.g.rs").read_text()
    constants = re.findall(r"pub const (\w+): (?:u16|u32|u64) = (0x[0-9A-Fa-f]+|\d+);", semantic)
    for name, value in constants:
        lines.append(f"#define GPUI_{name} {value}ull")
    output.write_text("\n".join(lines) + "\n")
    mbt = ["// Generated from the selected host's semantic schema; do not edit."]
    mbt += [f"pub const {name} : Int = {value}" for name, value in constants
            if name.startswith(("COMPONENT_", "OP_"))]
    output.with_name("semantic.g.mbt").write_text("\n\n".join(mbt) + "\n")
