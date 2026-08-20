from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "reference_candidate"
BUILD = ROOT / "build_rc1"
PACKAGE = BUILD / "package"
TEST = BUILD / "test"
ZIP = BUILD / "TRAJECTORY_FUNCTIONAL_REFERENCE_v0.9-rc1.zip"


def run(args: list[str], *, timeout: int = 120, stdout: Path | None = None) -> None:
    print("+", " ".join(args), flush=True)
    if stdout:
        with stdout.open("wb") as fh:
            subprocess.run(args, cwd=ROOT, check=True, timeout=timeout, stdout=fh)
    else:
        subprocess.run(args, cwd=ROOT, check=True, timeout=timeout)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assemble() -> str:
    shutil.rmtree(BUILD, ignore_errors=True)
    PACKAGE.mkdir(parents=True)
    TEST.mkdir(parents=True)
    for path in SRC.iterdir():
        if path.is_file() and path.name not in {"START_REFERENCE.html", "build_rc1.py"}:
            shutil.copy2(path, PACKAGE / path.name)
    shutil.copy2(SRC / "START_REFERENCE.html", PACKAGE / "START.html")
    path = PACKAGE / "START.html"
    source = path.read_text(encoding="utf-8")

    replacements = {
        "['s5-foreign','s2-foreign']": "['s2-foreign','s5-foreign']",
        "byId('applyEditBtn').onclick=applyEdit;": "byId('applyEditBtn').onclick=()=>{try{applyEdit()}catch(e){toast(e.message)}};",
        "dynamic:true})}}});return out}": "dynamic:true});}});}});return out}",
    }
    for old, new in replacements.items():
        if old not in source:
            raise RuntimeError(f"Required patch marker not found: {old[:70]}")
        source = source.replace(old, new, 1)

    pattern = re.compile(
        r"<div class='issue-filters'>\$\{Object\.keys\(TYPE_META\)\.map\(type=>`<label><input type='checkbox' data-type-filter='\$\{type\}' \$\{type==='import_technical'&&!state\.showTechnical\?'':'checked'\}> \$\{TYPE_META\[type\]\.icon\} \$\{TYPE_META\[type\]\.label\}</label>`\)\.join\(''\)\}</div>"
    )
    replacement = "<div class='issue-filters'>${Object.keys(TYPE_META).map(type=>`<span class='type-pill'>${TYPE_META[type].icon} ${TYPE_META[type].label}</span>`).join('')}</div>"
    source, count = pattern.subn(replacement, source)
    if count != 1:
        raise RuntimeError(f"Issue legend patch count={count}")
    path.write_text(source, encoding="utf-8")
    return source


def static_validate(source: str) -> None:
    for path in PACKAGE.glob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))
    if "<script src=" in source:
        raise RuntimeError("External script found")
    if re.search(r"\bfetch\s*\(", source):
        raise RuntimeError("fetch() call found")
    scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", source, flags=re.S | re.I)
    if not scripts:
        raise RuntimeError("Inline script not found")
    app = TEST / "app.js"
    app.write_text(scripts[-1], encoding="utf-8")
    required = [
        "activeCompIds", "computeFocusEdges", "buildHardIssues", "buildSoftIssues",
        "targetsForScope", "sessionCompatible", "runConformanceTests",
    ]
    missing = [name for name in required if name not in source]
    if missing:
        raise RuntimeError("Missing required mechanics: " + ", ".join(missing))
    run(["node", "--check", str(app.relative_to(ROOT))])


def build_fixtures(source: str) -> None:
    theme_marker = "state.theme=localStorage.getItem('trajectory-reference-theme')||'system';"
    if theme_marker not in source:
        raise RuntimeError("Theme marker not found")
    (TEST / "light.html").write_text(source.replace(theme_marker, "state.theme='light';", 1), encoding="utf-8")
    (TEST / "dark.html").write_text(source.replace(theme_marker, "state.theme='dark';", 1), encoding="utf-8")
    injection = r'''
document.addEventListener('DOMContentLoaded',()=>setTimeout(()=>{
  let ok=true;
  try{
    byId('clearAllComps').click();
    document.querySelector("[data-group-on='hard']").click();
    document.querySelector("[data-group-on='soft_skills']").click();
    ok=ok&&state.activeCompIds.has('H-NET')&&state.activeCompIds.has('S-CRIT');
    document.querySelector("[data-group-off='hard']").click();
    ok=ok&&!state.activeCompIds.has('H-NET')&&state.activeCompIds.has('S-CRIT');
    state.activeCompIds.clear();renderAll();
    const node=nodeByKey('cyber','s3-networks');
    state.focusedNodeId=node.id;renderAll();
    ok=ok&&computeFocusEdges(node,new Set()).length>0;
    state.activeCompIds=new Set(['H-NET']);renderAll();
    const filtered=computeFocusEdges(node,state.activeCompIds);
    ok=ok&&filtered.length>0&&filtered.every(x=>x.compId==='H-NET');
    focusIssue('SRC-001');
    ok=ok&&state.selectedIssueId==='SRC-001'&&state.roleId==='cyber';
    ok=ok&&!statusChangeAllowed('fixed','');
    ok=ok&&targetsForScope(nodeByKey('cyber','s1-rus'),'shared_realization').length===2;
    const schemas=[sessionPayload().session_schema,snapshotPayload().schema,'trajectory-change-log-v1',getIssueExport('SRC-001').schema];
    ok=ok&&new Set(schemas).size===4;
  }catch(e){console.error(e);ok=false}
  document.documentElement.dataset.uiScenario=ok?'ok':'failed';
},1200));
'''
    anchor = "window.__RUN_CONFORMANCE_TESTS__=runConformanceTests;"
    if anchor not in source:
        raise RuntimeError("Scenario injection marker not found")
    (TEST / "scenario.html").write_text(source.replace(anchor, injection + anchor, 1), encoding="utf-8")


def browser_validate() -> None:
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if not chrome:
        raise RuntimeError("Chrome/Chromium not found")
    run([chrome, "--version"])
    for mode in ("light", "dark", "scenario"):
        profile = TEST / f"profile-{mode}"
        profile.mkdir()
        dom = TEST / f"{mode}-dom.html"
        url = f"file://{(TEST / f'{mode}.html').resolve()}"
        run([
            chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
            "--allow-file-access-from-files", f"--user-data-dir={profile.resolve()}",
            "--virtual-time-budget=10000", "--dump-dom", url,
        ], timeout=75, stdout=dom)
        text = dom.read_text(encoding="utf-8", errors="replace")
        if 'data-runtime-ready="1"' not in text or 'data-self-test="ok"' not in text:
            raise RuntimeError(f"Built-in browser self-test failed for {mode}")
    light = (TEST / "light-dom.html").read_text(encoding="utf-8", errors="replace")
    dark = (TEST / "dark-dom.html").read_text(encoding="utf-8", errors="replace")
    scenario = (TEST / "scenario-dom.html").read_text(encoding="utf-8", errors="replace")
    if 'data-theme="light"' not in light:
        raise RuntimeError("Light theme not applied")
    if 'data-theme="dark"' not in dark:
        raise RuntimeError("Dark theme not applied")
    if 'data-ui-scenario="ok"' not in scenario:
        raise RuntimeError("Behavioral scenario failed")
    for mode in ("light", "dark"):
        run([
            chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
            "--allow-file-access-from-files", "--window-size=1920,1080",
            f"--screenshot={str((TEST / f'{mode}.png').resolve())}",
            f"file://{(TEST / f'{mode}.html').resolve()}",
        ], timeout=75)


def package() -> dict[str, object]:
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    protocol = [
        "TRAJECTORY_FUNCTIONAL_REFERENCE v0.9-rc1",
        f"created_at={now}",
        "PASS: autonomous START.html; no external scripts or fetch calls",
        "PASS: inline JavaScript syntax (node --check)",
        "PASS: all JSON contracts parse",
        "PASS: Chrome light-theme smoke test",
        "PASS: Chrome dark-theme smoke test",
        "PASS: built-in conformance tests",
        "PASS: behavioral scenario for cumulative filters, F-02 focus, issue navigation, comment guard, shared editing and distinct exports",
        "NOTE: candidate contains representative data only and requires team acceptance before v1.0",
    ]
    (PACKAGE / "VERIFICATION_PROTOCOL.txt").write_text("\n".join(protocol) + "\n", encoding="utf-8")
    shutil.copy2(TEST / "light.png", PACKAGE / "PREVIEW_LIGHT.png")
    shutil.copy2(TEST / "dark.png", PACKAGE / "PREVIEW_DARK.png")
    manifest: dict[str, object] = {
        "package": "TRAJECTORY_FUNCTIONAL_REFERENCE",
        "version": "0.9.0-rc1",
        "created_at": now,
        "start_file": "START.html",
        "candidate_only": True,
        "files": [],
    }
    files: list[dict[str, object]] = []
    for path in sorted(p for p in PACKAGE.iterdir() if p.is_file() and p.name != "PACKAGE_MANIFEST.json"):
        files.append({"name": path.name, "size": path.stat().st_size, "sha256": sha256(path)})
    manifest["files"] = files
    (PACKAGE / "PACKAGE_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(PACKAGE.iterdir()):
            if path.is_file():
                archive.write(path, path.name)
    with zipfile.ZipFile(ZIP) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("ZIP integrity failed")
        names = archive.namelist()
        if "START.html" not in names or any("/" in name.strip("/") for name in names):
            raise RuntimeError("START.html is not at ZIP root or nested paths found")
    result = {"zip": str(ZIP), "size": ZIP.stat().st_size, "sha256": sha256(ZIP), "files": len(names)}
    (BUILD / "PACKAGE_SHA256.txt").write_text(f"{result['sha256']}  {ZIP.name}\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return result


def main() -> None:
    source = assemble()
    static_validate(source)
    build_fixtures((PACKAGE / "START.html").read_text(encoding="utf-8"))
    browser_validate()
    package()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        raise
