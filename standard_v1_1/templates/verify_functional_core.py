#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path


def extract_literal(source: str, const_name: str) -> tuple[int, int]:
    match = re.search(rf"\bconst\s+{re.escape(const_name)}\s*=\s*", source)
    if not match:
        raise RuntimeError(f"Constant not found: {const_name}")
    start = match.end()
    while start < len(source) and source[start].isspace():
        start += 1
    if start >= len(source) or source[start] not in "[{":
        raise RuntimeError(f"Unsupported literal for {const_name}")

    stack = ["}" if source[start] == "{" else "]"]
    quote = None
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
                    return start, i + 1
        i += 1
    raise RuntimeError(f"Unterminated literal for {const_name}")


def normalized_core(source: str, constants: list[str]) -> str:
    replacements = []
    for name in constants:
        start, end = extract_literal(source, name)
        replacements.append((start, end, f"__SUBJECT_DATA_{name}__"))
    result = source
    for start, end, replacement in sorted(replacements, reverse=True):
        result = result[:start] + replacement + result[end:]
    return result


def main() -> int:
    html_path = Path(sys.argv[1] if len(sys.argv) > 1 else "START.html")
    manifest_path = Path(sys.argv[2] if len(sys.argv) > 2 else "18_FUNCTIONAL_CORE_MANIFEST_v1.0.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source = html_path.read_text(encoding="utf-8")
    constants = manifest["allowed_subject_data_constants"]
    actual = hashlib.sha256(normalized_core(source, constants).encode("utf-8")).hexdigest()
    expected = manifest["immutable_core_sha256"]
    result = {
        "html": str(html_path),
        "manifest": str(manifest_path),
        "expected": expected,
        "actual": actual,
        "match": actual == expected
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["match"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
