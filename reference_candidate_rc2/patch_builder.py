from pathlib import Path

path = Path(__file__).with_name('build_rc2.py')
source = path.read_text(encoding='utf-8')
replacements = {
    "set('issue_expands_in_place',Boolean(document.querySelector(`#issue-item-${safeId('MAP-001')}.expanded .issue-body`)));": "const issueItemId='MAP-001'.replace(/[^a-zA-Z0-9_-]+/g,'_');\n      set('issue_expands_in_place',Boolean(document.querySelector(`#issue-item-${issueItemId}.expanded .issue-body`)));",
    "set('common_discipline_two_roles',sharedRoleIds(shared).length===2);": "const rc2api=window.__TRAJECTORY_REFERENCE_RC2__;\n      set('common_discipline_two_roles',rc2api.sharedRoleIds(shared).length===2);",
    "set('status_payload_compatible',issueStatusPayloadCompatible(issueStatusPayload()));": "set('status_payload_compatible',rc2api.issueStatusPayloadCompatible(rc2api.issueStatusPayload()));",
}
for old, new in replacements.items():
    if old not in source:
        raise SystemExit(f'patch marker not found: {old}')
    source = source.replace(old, new, 1)
path.write_text(source, encoding='utf-8')
print({'patched': len(replacements), 'file': str(path)})
