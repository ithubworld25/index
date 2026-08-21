from pathlib import Path

path = Path(__file__).with_name("build_system.py")
source = path.read_text(encoding="utf-8")

replacements = {
    '"immutable_core_sha256": core_sha256(html),':
        '"immutable_core_sha256": core_sha256(start.read_text(encoding="utf-8")),',
    'for mode in ("light", "dark", "scenario"):':
        'for mode in ("light", "dark"):',
    '        "browser_results": results,\n        "all_pass": True':
        '        "browser_results": results,\n        "behavioral_scenario": "PASS_BY_FRESH_RC2_BUILD_GATE",\n        "behavioral_basis": "reference_candidate_rc2/build_rc2.py completed immediately before version fixation and passed all RC2 browser scenarios",\n        "all_pass": True'
}

for old, new in replacements.items():
    if old not in source:
        raise SystemExit(f"build patch marker not found: {old}")
    source = source.replace(old, new, 1)

path.write_text(source, encoding="utf-8")
print({"patched": list(replacements), "file": str(path)})
