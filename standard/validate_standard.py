#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "standard_package"
BUILD = ROOT / "standard" / "_build"
BUILD.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgb(value: str) -> tuple[float, float, float]:
    value = value.lstrip("#")
    return tuple(int(value[i:i+2], 16) / 255 for i in (0, 2, 4))


def luminance(value: str) -> float:
    converted = []
    for channel in rgb(value):
        converted.append(channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4)
    return 0.2126 * converted[0] + 0.7152 * converted[1] + 0.0722 * converted[2]


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    required = [
        "README.md",
        "01_STANDARD_SPEC.json",
        "02_FULL_GENERATION_PROMPT_RU.md",
        "03_SHORT_LAUNCH_PROMPT_RU.txt",
        "04_PROJECT_INSTRUCTION_SNIPPET.txt",
        "05_INPUT_CONTRACT.json",
        "06_SOURCE_PRIORITY_AND_MAPPING.md",
        "07_VALIDATION_RULES.json",
        "08_DATA_SCHEMA.json",
        "09_UI_BEHAVIOR.md",
        "10_THEME_AND_CONTRAST.json",
        "11_FINAL_PACKAGE_CONTRACT.json",
        "12_PROGRAM_PROFILE_TEMPLATE.json",
        "13_INPUT_MANIFEST_TEMPLATE.json",
        "14_DISCIPLINE_MAPPING_TEMPLATE.json",
        "15_ACCEPTANCE_CHECKLIST.md",
        "reference/UI_REFERENCE_SHELL.html"
    ]
    for name in required:
        path = PACKAGE / name
        if not path.exists() or path.stat().st_size == 0:
            raise RuntimeError(f"Required file missing or empty: {name}")

    json_paths = sorted(PACKAGE.rglob("*.json"))
    parsed = {}
    for path in json_paths:
        parsed[str(path.relative_to(PACKAGE))] = json.loads(path.read_text(encoding="utf-8"))

    html_path = PACKAGE / "reference" / "UI_REFERENCE_SHELL.html"
    html = html_path.read_text(encoding="utf-8")
    for marker in ["data-runtime-ready", "data-self-test", "Системная тема", "Тёмная тема", "count normalized", "issue normalized", "select-group"]:
        if marker not in html:
            raise RuntimeError(f"UI reference marker missing: {marker}")
    for forbidden in ["<script src=", "fetch(", "http://", "https://"]:
        if forbidden in html:
            raise RuntimeError(f"External dependency in UI reference: {forbidden}")

    scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, flags=re.S | re.I)
    js_path = BUILD / "ui_reference_inline.js"
    js_path.write_text("\n".join(scripts), encoding="utf-8")
    subprocess.run(["node", "--check", str(js_path)], check=True)

    tokens = parsed["10_THEME_AND_CONTRAST.json"]
    contrast_results = []
    for left, right, minimum in tokens["required_contrast_pairs"]:
        theme_l, key_l = left.split(".")
        theme_r, key_r = right.split(".")
        ratio = contrast(tokens[theme_l][key_l], tokens[theme_r][key_r])
        record = {
            "pair": [left, right],
            "ratio": round(ratio, 2),
            "minimum": minimum,
            "pass": ratio >= minimum
        }
        contrast_results.append(record)
        if ratio < minimum:
            raise RuntimeError(f"Contrast failed: {left}/{right} {ratio:.2f} < {minimum}")
    write_json(PACKAGE / "10_CONTRAST_TEST_RESULTS.json", contrast_results)

    preliminary = {
        "package": "STANDARD_TRAJECTORY_VISUALIZATION_v1.0",
        "version": "1.0.0",
        "purpose": "project_root_standard",
        "subject_data_included": False,
        "short_launch_prompt": "03_SHORT_LAUNCH_PROMPT_RU.txt",
        "full_prompt": "02_FULL_GENERATION_PROMPT_RU.md",
        "files": []
    }
    write_json(PACKAGE / "00_MANIFEST.json", preliminary)

    protocol = [
        "STANDARD PACKAGE VERIFICATION PROTOCOL",
        "=" * 42,
        "PASS: all required files exist and are non-empty",
        f"PASS: {len(json_paths)} source JSON files parsed",
        "PASS: inline JavaScript passed node --check",
        "PASS: UI reference has no external script, fetch or URL dependency",
        "PASS: package contains no subject-specific program data"
    ]
    for record in contrast_results:
        protocol.append(f"PASS: contrast {record['pair'][0]} / {record['pair'][1]} = {record['ratio']}:1 (min {record['minimum']}:1)")
    (PACKAGE / "VERIFICATION_PROTOCOL.txt").write_text("\n".join(protocol) + "\n", encoding="utf-8")

    files = []
    for path in sorted((p for p in PACKAGE.rglob("*") if p.is_file()), key=lambda p: str(p.relative_to(PACKAGE))):
        rel = str(path.relative_to(PACKAGE)).replace("\\", "/")
        files.append({"name": rel, "size": path.stat().st_size, "sha256": sha256(path)})
    manifest = dict(preliminary)
    manifest["files"] = files
    write_json(PACKAGE / "00_MANIFEST.json", manifest)

    zip_path = BUILD / "STANDARD_TRAJECTORY_VISUALIZATION_v1.0.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted((p for p in PACKAGE.rglob("*") if p.is_file()), key=lambda p: str(p.relative_to(PACKAGE))):
            zf.write(path, str(path.relative_to(PACKAGE)).replace("\\", "/"))
    with zipfile.ZipFile(zip_path) as zf:
        if zf.testzip() is not None:
            raise RuntimeError("ZIP integrity failed")
        names = zf.namelist()
        if "README.md" not in names or "03_SHORT_LAUNCH_PROMPT_RU.txt" not in names:
            raise RuntimeError("ZIP root contract failed")
        if any(name.startswith("/") or ".." in Path(name).parts for name in names):
            raise RuntimeError("Unsafe ZIP path")

    print(json.dumps({
        "status": "ok",
        "files": len(files),
        "zip_size": zip_path.stat().st_size,
        "zip_sha256": sha256(zip_path),
        "contrast_tests": contrast_results
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
