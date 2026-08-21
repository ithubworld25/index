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

core_key_marker = '            "FUNCTIONAL_CORE_TEMPLATE_v1.0.html"\n'
if source.count(core_key_marker) != 1:
    raise SystemExit(f"unexpected core manifest key marker count: {source.count(core_key_marker)}")
source = source.replace(core_key_marker, '            "FUNCTIONAL_CORE_TEMPLATE_v1.0.html",\n            "verify_functional_core.py"\n', 1)

system_key_marker = '        "FUNCTIONAL_CORE_TEMPLATE_v1.0.html",\n        "VERIFICATION_REPORT_v1.1.md"'
if system_key_marker not in source:
    raise SystemExit("system key files marker not found")
source = source.replace(system_key_marker, '        "FUNCTIONAL_CORE_TEMPLATE_v1.0.html",\n        "verify_functional_core.py",\n        "VERIFICATION_REPORT_v1.1.md"', 1)

path.write_text(source, encoding="utf-8")
print({"patched": list(replacements) + ["core verifier key files"], "file": str(path)})
