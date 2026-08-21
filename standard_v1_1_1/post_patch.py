from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = Path(__file__).resolve().parent
BUILD = DIR / "build_system.py"
TEMPLATES = DIR / "templates"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Missing marker for {label}: {old[:140]}")
    return text.replace(old, new, 1)


def patch_build() -> None:
    source = BUILD.read_text(encoding="utf-8")
    source = replace_once(
        source,
        '"immutable_core_sha256": core_sha256(html),',
        '"immutable_core_sha256": core_sha256(start.read_text(encoding="utf-8")),',
        "manifest hash after write_text normalization",
    )

    core_key_marker = '            "FUNCTIONAL_CORE_TEMPLATE_v1.0.1.html"\n'
    if core_key_marker in source:
        source = source.replace(
            core_key_marker,
            '            "FUNCTIONAL_CORE_TEMPLATE_v1.0.1.html",\n            "verify_functional_core.py"\n',
            1,
        )

    system_key_marker = '        "FUNCTIONAL_CORE_TEMPLATE_v1.0.1.html",\n        "VERIFICATION_REPORT_v1.1.1.md"'
    if system_key_marker in source:
        source = source.replace(
            system_key_marker,
            '        "FUNCTIONAL_CORE_TEMPLATE_v1.0.1.html",\n        "verify_functional_core.py",\n        "VERIFICATION_REPORT_v1.1.1.md"',
            1,
        )

    old_report = '''Функциональный шаблон проверен как автономный HTML. Пройдены синтаксис JavaScript, отсутствие внешних зависимостей, хеш ядра, светлая и тёмная темы, режим компетенции без линий, фокус дисциплины и аккордеон проблем.\n'''
    new_report = '''Функциональный шаблон проверен как автономный HTML. Пройдены синтаксис JavaScript, отсутствие внешних зависимостей, хеш ядра, светлая и тёмная темы, режим компетенции без линий, фокус дисциплины и аккордеон проблем. Hotfix P0-CORE-01 подтверждён вычисленными стилями активных элементов; светлые границы проверены на panel, panel_alt и bg.\n'''
    if old_report in source:
        source = source.replace(old_report, new_report, 1)

    BUILD.write_text(source, encoding="utf-8")


def patch_templates() -> None:
    verifier = TEMPLATES / "verify_functional_core.py"
    text = verifier.read_text(encoding="utf-8")
    text = text.replace(
        '18_FUNCTIONAL_CORE_MANIFEST_v1.0.json',
        '18_FUNCTIONAL_CORE_MANIFEST_v1.0.1.json',
    )
    verifier.write_text(text, encoding="utf-8")

    for path in TEMPLATES.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        changed = False
        if data.get("version") == "1.1.0":
            data["version"] = "1.1.1"
            changed = True
        if data.get("functional_core_version") == "1.0.0":
            data["functional_core_version"] = "1.0.1"
            changed = True
        if isinstance(data.get("functional_core"), dict) and data["functional_core"].get("version") == "1.0.0":
            data["functional_core"]["version"] = "1.0.1"
            changed = True
        if changed:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    patch_build()
    patch_templates()
    print(json.dumps({"status": "post-patched", "build": str(BUILD), "templates": str(TEMPLATES)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
