from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any

ALLOWED_CONSTANTS = [
    "PROFILE",
    "SOURCE_MANIFEST",
    "CATALOG",
    "NODE_DEFS",
    "CONTINUATION_DEFS",
    "STATIC_ISSUES",
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2))


def extract_const_literal(source: str, const_name: str) -> tuple[str, int, int]:
    match = re.search(rf"\bconst\s+{re.escape(const_name)}\s*=\s*", source)
    if not match:
        raise RuntimeError(f"Constant not found: {const_name}")
    start = match.end()
    while start < len(source) and source[start].isspace():
        start += 1
    if start >= len(source) or source[start] not in "[{":
        raise RuntimeError(f"Unsupported literal for {const_name}")

    stack = ["}" if source[start] == "{" else "]"]
    quote: str | None = None
    escaped = False
    i = start + 1
    while i < len(source):
        ch = source[i]
        if quote is not None:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
        else:
            if ch in "'\"`":
                quote = ch
            elif ch == "{":
                stack.append("}")
            elif ch == "[":
                stack.append("]")
            elif ch in "}]":
                if not stack or ch != stack[-1]:
                    raise RuntimeError(f"Unbalanced literal for {const_name}")
                stack.pop()
                if not stack:
                    return source[start:i + 1], start, i + 1
        i += 1
    raise RuntimeError(f"Unterminated literal for {const_name}")


def normalized_core(source: str, constants: list[str] | None = None) -> str:
    constants = constants or ALLOWED_CONSTANTS
    replacements: list[tuple[int, int, str]] = []
    for name in constants:
        _, start, end = extract_const_literal(source, name)
        replacements.append((start, end, f"__SUBJECT_DATA_{name}__"))
    result = source
    for start, end, replacement in sorted(replacements, reverse=True):
        result = result[:start] + replacement + result[end:]
    return result


def core_sha256(source: str, constants: list[str] | None = None) -> str:
    return sha256_bytes(normalized_core(source, constants).encode("utf-8"))


def executable_scripts(source: str) -> list[str]:
    scripts: list[str] = []
    for attrs, body in re.findall(r"<script([^>]*)>(.*?)</script>", source, flags=re.DOTALL | re.IGNORECASE):
        if "application/json" not in attrs.lower():
            scripts.append(body)
    return scripts


def safe_zip(source_dir: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source_dir).as_posix())
    with zipfile.ZipFile(destination) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f"Corrupt ZIP member: {bad}")
        for name in archive.namelist():
            parts = Path(name).parts
            if name.startswith("/") or ".." in parts:
                raise RuntimeError(f"Unsafe ZIP path: {name}")


def package_manifest(directory: Path, package: str, version: str, created_at: str, start_file: str | None = None) -> dict[str, Any]:
    files = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != "PACKAGE_MANIFEST.json":
            files.append({
                "name": path.relative_to(directory).as_posix(),
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            })
    return {
        "package": package,
        "version": version,
        "created_at": created_at,
        "start_file": start_file,
        "autonomous_start": bool(start_file),
        "files": files,
    }


def contrast_ratio(hex_a: str, hex_b: str) -> float:
    def luminance(value: str) -> float:
        value = value.lstrip("#")
        channels = [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        linear = [channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
    a = luminance(hex_a)
    b = luminance(hex_b)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)
