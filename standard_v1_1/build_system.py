from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from core_tools import (
    ALLOWED_CONSTANTS,
    contrast_ratio,
    core_sha256,
    executable_scripts,
    package_manifest,
    safe_zip,
    sha256_file,
    write_json,
    write_text,
)

ROOT = Path(__file__).resolve().parents[1]
RC2_ZIP = ROOT / "build_rc2" / "TRAJECTORY_FUNCTIONAL_REFERENCE_v0.9-rc2.zip"
OUT = ROOT / "build_standard_v1_1"
FUNCTIONAL_DIR = OUT / "functional_reference_v1_0"
STANDARD_DIR = OUT / "standard_v1_1"
SYSTEM_DIR = OUT / "system_v1_1"
TEST_DIR = OUT / "tests"
TEMPLATES = Path(__file__).resolve().parent / "templates"
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

FUNCTIONAL_ZIP = OUT / "TRAJECTORY_FUNCTIONAL_REFERENCE_v1.0.zip"
STANDARD_ZIP = OUT / "STANDARD_TRAJECTORY_VISUALIZATION_v1.1.zip"
SYSTEM_ZIP = OUT / "TRAJECTORY_VISUALIZATION_SYSTEM_v1.1.zip"


def run(cmd: list[str], *, timeout: int = 180, stdout_path: Path | None = None) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd), flush=True)
    if stdout_path:
        with stdout_path.open("w", encoding="utf-8") as handle:
            return subprocess.run(cmd, text=True, check=True, timeout=timeout, stdout=handle)
    return subprocess.run(cmd, text=True, check=True, timeout=timeout, capture_output=True)


def build_reference_html() -> tuple[Path, dict]:
    if not RC2_ZIP.exists():
        raise RuntimeError(f"RC2 ZIP not found: {RC2_ZIP}")
    extract = OUT / "rc2_extract"
    shutil.rmtree(extract, ignore_errors=True)
    extract.mkdir(parents=True)
    with zipfile.ZipFile(RC2_ZIP) as archive:
        archive.extractall(extract)

    source_start = extract / "START.html"
    html = source_start.read_text(encoding="utf-8")
    html = html.replace("0.9.0-rc1", "1.0.0").replace("0.9.0-rc2", "1.0.0")
    html = html.replace("v0.9-rc1", "v1.0").replace("v0.9-rc2", "v1.0")
    html = html.replace("кандидат v1.0", "зафиксированный эталон v1.0")
    html = html.replace("Кандидат функционального эталона", "Функциональный эталон")
    html = html.replace("кандидат функционального эталона", "функциональный эталон")

    shutil.rmtree(FUNCTIONAL_DIR, ignore_errors=True)
    FUNCTIONAL_DIR.mkdir(parents=True)
    start = FUNCTIONAL_DIR / "START.html"
    template = FUNCTIONAL_DIR / "FUNCTIONAL_CORE_TEMPLATE_v1.0.html"
    write_text(start, html)
    write_text(template, html)

    manifest = {
        "functional_core_id": "trajectory-functional-core",
        "version": "1.0.0",
        "created_at": NOW,
        "immutable_core_sha256": core_sha256(html),
        "reference_start_sha256": sha256_file(start),
        "template_sha256": sha256_file(template),
        "allowed_subject_data_constants": ALLOWED_CONSTANTS,
        "allowed_changes": [
            "replace JavaScript literals assigned to allowed subject-data constants",
            "change program labels through PROFILE"
        ],
        "forbidden_changes_without_new_core_version": [
            "active competency state model",
            "competency-only mode",
            "discipline focus and line semantics",
            "issue accordion and status lifecycle",
            "status JSON schema",
            "theme mechanics",
            "DOM ids used by conformance tests"
        ],
        "verification": "replace each allowed literal with __SUBJECT_DATA_<NAME>__ and compare SHA-256"
    }
    write_json(FUNCTIONAL_DIR / "FUNCTIONAL_CORE_MANIFEST.json", manifest)

    readme = f"""# TRAJECTORY_FUNCTIONAL_REFERENCE v1.0

Зафиксированный исполняемый эталон механики визуализации образовательной траектории.

## Запуск

1. Полностью распакуйте архив.
2. Откройте `START.html` из корня.
3. Интернет и сервер не требуются.

## Перенос на другую специальность

Используйте `FUNCTIONAL_CORE_TEMPLATE_v1.0.html`. Заменяйте только константы, перечисленные в `FUNCTIONAL_CORE_MANIFEST.json`. После замены обязательно проверьте SHA-256 неизменяемого ядра.

Дата фиксации: {NOW}
"""
    write_text(FUNCTIONAL_DIR / "README.md", readme)

    functional_contract = json.loads((TEMPLATES / "01_STANDARD_SPEC_v1.1.json").read_text(encoding="utf-8"))
    write_json(FUNCTIONAL_DIR / "FUNCTIONAL_CONTRACT.json", functional_contract)
    shutil.copy2(TEMPLATES / "19_ISSUE_TAXONOMY_v1.1.json", FUNCTIONAL_DIR / "ISSUE_TAXONOMY.json")
    shutil.copy2(TEMPLATES / "20_FEATURE_PROFILE_v1.1.json", FUNCTIONAL_DIR / "FEATURE_PROFILE.json")
    return start, manifest


def inject_preload(html: str, theme: str, scenario: bool) -> str:
    first_script = html.find("<script>")
    preload = f"<script>localStorage.setItem('trajectory-reference-theme','{theme}');</script>\n"
    result = html[:first_script] + preload + html[first_script:]
    if scenario:
        scenario_js = r'''
<script>
setTimeout(() => {
  const checks = {};
  const set = (name, value) => checks[name] = Boolean(value);
  try {
    state.activeCompIds = new Set(['H-NET']);
    state.focusedNodeId = null;
    state.selectedIssueId = null;
    renderAll();
    setTimeout(() => {
      set('competency_only_no_lines', document.querySelectorAll('.line-competency').length === 0);
      set('competency_only_dims', document.querySelectorAll('.discipline.filtered-out').length > 0);
      const node = nodeByKey('cyber','s3-networks');
      state.focusedNodeId = node.id;
      renderAll();
      setTimeout(() => {
        set('focus_lines', document.querySelectorAll('.line-competency').length > 0);
        set('focus_related', document.querySelectorAll('.discipline.related-focus').length > 0);
        set('focus_dim', document.querySelectorAll('.discipline.focus-dim').length > 0);
        focusIssue('MAP-001');
        setTimeout(() => {
          set('issue_accordion', Boolean(document.querySelector('.issue-card.rc2-item.expanded .issue-body')));
          const ok = Object.values(checks).every(Boolean);
          document.documentElement.dataset.standardScenario = ok ? 'ok' : 'failed';
          document.documentElement.dataset.standardScenarioResults = encodeURIComponent(JSON.stringify(checks));
        }, 700);
      }, 700);
    }, 700);
  } catch (error) {
    document.documentElement.dataset.standardScenario = 'failed';
    document.documentElement.dataset.standardScenarioError = encodeURIComponent(error.stack || error.message);
  }
}, 1200);
</script>
'''
        result = result.replace("</body>", scenario_js + "</body>")
    return result


def verify_reference(start: Path, manifest: dict) -> dict:
    shutil.rmtree(TEST_DIR, ignore_errors=True)
    TEST_DIR.mkdir(parents=True)
    html = start.read_text(encoding="utf-8")

    if re.search(r"<script[^>]+src=", html, flags=re.IGNORECASE):
        raise RuntimeError("External script dependency found")
    if re.search(r"\bfetch\s*\(", html):
        raise RuntimeError("fetch() call found")
    if core_sha256(html) != manifest["immutable_core_sha256"]:
        raise RuntimeError("Functional core hash mismatch")

    for index, script in enumerate(executable_scripts(html)):
        path = TEST_DIR / f"app-{index}.js"
        write_text(path, script)
        run(["node", "--check", str(path)])

    chrome = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    if not chrome:
        raise RuntimeError("Chrome/Chromium not found")
    chrome_version = run([chrome, "--version"]).stdout.strip()
    results = []
    for mode in ("light", "dark", "scenario"):
        test_file = TEST_DIR / f"{mode}.html"
        write_text(test_file, inject_preload(html, "dark" if mode == "dark" else "light", mode == "scenario"))
        passed = False
        attempts = []
        for attempt in range(1, 4):
            profile = TEST_DIR / f"profile-{mode}-{attempt}"
            profile.mkdir()
            dom = TEST_DIR / f"dom-{mode}-{attempt}.html"
            cmd = [
                chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-first-run",
                "--no-default-browser-check", "--disable-background-networking", "--disable-sync",
                "--disable-extensions", "--allow-file-access-from-files", f"--user-data-dir={profile}",
                "--virtual-time-budget=20000", "--dump-dom", f"file://{test_file.resolve()}"
            ]
            run(cmd, timeout=100, stdout_path=dom)
            text = dom.read_text(encoding="utf-8", errors="replace")
            checks = {
                "runtime_ready": 'data-runtime-ready="1"' in text,
                "base_self_test": 'data-self-test="ok"' in text,
                "fixed_core_ready": 'data-rc2-ready="1"' in text,
                "fixed_core_self_test": 'data-rc2-self-test="ok"' in text
            }
            if mode == "light":
                checks["theme_light"] = 'data-theme="light"' in text
            if mode == "dark":
                checks["theme_dark"] = 'data-theme="dark"' in text
            if mode == "scenario":
                checks["behavioral_scenario"] = 'data-standard-scenario="ok"' in text
            passed = all(checks.values())
            attempts.append({"attempt": attempt, "pass": passed, "checks": checks})
            if passed:
                break
        results.append({"mode": mode, "pass": passed, "attempts": attempts})
        if not passed:
            raise RuntimeError(f"Browser verification failed for {mode}: {attempts}")

    return {
        "version": "1.0.0",
        "created_at": NOW,
        "chrome": chrome_version,
        "start_sha256": sha256_file(start),
        "core_sha256": manifest["immutable_core_sha256"],
        "javascript_syntax": "PASS",
        "external_dependencies": "PASS",
        "browser_results": results,
        "all_pass": True
    }


def add_verification(start: Path, manifest: dict, tests: dict) -> None:
    write_json(FUNCTIONAL_DIR / "AUTOTEST_RESULTS_v1.0.json", tests)
    write_text(FUNCTIONAL_DIR / "VERIFICATION_REPORT_v1.0.md", f"""# Отчёт проверки функционального эталона v1.0

- JavaScript syntax: PASS
- external JS/JSON/fetch: отсутствуют
- immutable core SHA-256: `{tests['core_sha256']}`
- light theme browser smoke: PASS
- dark theme browser smoke: PASS
- competency-only mode without lines: PASS
- discipline focus lines/highlight/dim: PASS
- issue accordion: PASS
- autonomous START.html: PASS

Chrome: {tests['chrome']}
Дата: {NOW}
""")
    write_json(FUNCTIONAL_DIR / "PACKAGE_MANIFEST.json", package_manifest(FUNCTIONAL_DIR, "TRAJECTORY_FUNCTIONAL_REFERENCE", "1.0.0", NOW, "START.html"))


def build_standard(start: Path, manifest: dict, tests: dict) -> None:
    shutil.rmtree(STANDARD_DIR, ignore_errors=True)
    STANDARD_DIR.mkdir(parents=True)
    for path in sorted(TEMPLATES.iterdir()):
        if path.is_file():
            shutil.copy2(path, STANDARD_DIR / path.name)
    shutil.copy2(start, STANDARD_DIR / "FUNCTIONAL_CORE_TEMPLATE_v1.0.html")
    write_json(STANDARD_DIR / "18_FUNCTIONAL_CORE_MANIFEST_v1.0.json", manifest)

    theme = json.loads((STANDARD_DIR / "10_THEME_AND_CONTRAST_v1.1.json").read_text(encoding="utf-8"))
    pairs = [
        ("light.text/panel", theme["light"]["text"], theme["light"]["panel"], 4.5),
        ("light.muted/panel", theme["light"]["muted"], theme["light"]["panel"], 4.5),
        ("dark.text/panel", theme["dark"]["text"], theme["dark"]["panel"], 4.5),
        ("dark.muted/panel", theme["dark"]["muted"], theme["dark"]["panel"], 4.5),
        ("dark.normalized/panel", theme["dark"]["normalized_text"], theme["dark"]["normalized_bg"], 4.5)
    ]
    contrast = []
    for name, first, second, minimum in pairs:
        ratio = contrast_ratio(first, second)
        contrast.append({"pair": name, "ratio": round(ratio, 3), "minimum": minimum, "pass": ratio >= minimum})
    if not all(item["pass"] for item in contrast):
        raise RuntimeError(f"Contrast test failed: {contrast}")
    write_json(STANDARD_DIR / "10_CONTRAST_TEST_RESULTS_v1.1.json", {"version": "1.1.0", "results": contrast, "all_pass": True})
    write_json(STANDARD_DIR / "AUTOTEST_RESULTS_v1.1.json", tests)
    write_text(STANDARD_DIR / "VERIFICATION_REPORT_v1.1.md", f"""# Отчёт проверки стандарта v1.1

Функциональный шаблон проверен как автономный HTML. Пройдены синтаксис JavaScript, отсутствие внешних зависимостей, хеш ядра, светлая и тёмная темы, режим компетенции без линий, фокус дисциплины и аккордеон проблем.

Core SHA-256: `{tests['core_sha256']}`
START SHA-256: `{tests['start_sha256']}`
Chrome: {tests['chrome']}
Дата: {NOW}
""")
    write_json(STANDARD_DIR / "00_MANIFEST.json", {
        "standard_id": "trajectory-visualization-standard",
        "version": "1.1.0",
        "functional_core_version": "1.0.0",
        "created_at": NOW,
        "key_files": [
            "01_STANDARD_SPEC_v1.1.json",
            "02_FULL_GENERATION_PROMPT_RU_v1.1.md",
            "03_SHORT_LAUNCH_PROMPT_RU_v1.1.txt",
            "10_THEME_AND_CONTRAST_v1.1.json",
            "11_FINAL_PACKAGE_CONTRACT_v1.1.json",
            "18_FUNCTIONAL_CORE_MANIFEST_v1.0.json",
            "FUNCTIONAL_CORE_TEMPLATE_v1.0.html"
        ]
    })
    write_json(STANDARD_DIR / "PACKAGE_MANIFEST.json", package_manifest(STANDARD_DIR, "STANDARD_TRAJECTORY_VISUALIZATION", "1.1.0", NOW))


def package_all(tests: dict) -> dict:
    safe_zip(FUNCTIONAL_DIR, FUNCTIONAL_ZIP)
    safe_zip(STANDARD_DIR, STANDARD_ZIP)

    shutil.rmtree(SYSTEM_DIR, ignore_errors=True)
    SYSTEM_DIR.mkdir(parents=True)
    shutil.copy2(FUNCTIONAL_ZIP, SYSTEM_DIR / FUNCTIONAL_ZIP.name)
    shutil.copy2(STANDARD_ZIP, SYSTEM_DIR / STANDARD_ZIP.name)
    key_files = [
        "01_STANDARD_SPEC_v1.1.json",
        "02_FULL_GENERATION_PROMPT_RU_v1.1.md",
        "03_SHORT_LAUNCH_PROMPT_RU_v1.1.txt",
        "10_THEME_AND_CONTRAST_v1.1.json",
        "11_FINAL_PACKAGE_CONTRACT_v1.1.json",
        "18_FUNCTIONAL_CORE_MANIFEST_v1.0.json",
        "FUNCTIONAL_CORE_TEMPLATE_v1.0.html",
        "VERIFICATION_REPORT_v1.1.md"
    ]
    for name in key_files:
        shutil.copy2(STANDARD_DIR / name, SYSTEM_DIR / name)
    write_text(SYSTEM_DIR / "README_FIRST.txt", """Системный комплект v1.1.

Архивы внутри — резервные комплекты. Отдельные ключевые файлы прикрепите в корень проекта, чтобы новые чаты читали их напрямую. В новый чат прикладывайте документы только одной специальности и используйте SHORT_LAUNCH_PROMPT_RU_v1.1.txt.
""")
    write_json(SYSTEM_DIR / "PACKAGE_MANIFEST.json", package_manifest(SYSTEM_DIR, "TRAJECTORY_VISUALIZATION_SYSTEM", "1.1.0", NOW))
    safe_zip(SYSTEM_DIR, SYSTEM_ZIP)

    result = {
        "status": "success",
        "created_at": NOW,
        "all_tests_pass": tests["all_pass"],
        "functional_reference": {"file": FUNCTIONAL_ZIP.name, "size": FUNCTIONAL_ZIP.stat().st_size, "sha256": sha256_file(FUNCTIONAL_ZIP)},
        "standard": {"file": STANDARD_ZIP.name, "size": STANDARD_ZIP.stat().st_size, "sha256": sha256_file(STANDARD_ZIP)},
        "system": {"file": SYSTEM_ZIP.name, "size": SYSTEM_ZIP.stat().st_size, "sha256": sha256_file(SYSTEM_ZIP)},
        "functional_start_sha256": tests["start_sha256"],
        "functional_core_sha256": tests["core_sha256"]
    }
    write_json(OUT / "BUILD_RESULT.json", result)
    write_text(OUT / "PACKAGE_SHA256_v1.1.txt", "\n".join([
        f"{result['functional_reference']['sha256']}  {FUNCTIONAL_ZIP.name}",
        f"{result['standard']['sha256']}  {STANDARD_ZIP.name}",
        f"{result['system']['sha256']}  {SYSTEM_ZIP.name}"
    ]))
    return result


def main() -> None:
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    start, manifest = build_reference_html()
    tests = verify_reference(start, manifest)
    add_verification(start, manifest, tests)
    build_standard(start, manifest, tests)
    result = package_all(tests)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
