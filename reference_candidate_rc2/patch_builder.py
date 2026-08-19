from pathlib import Path

path = Path(__file__).with_name('build_rc2.py')
source = path.read_text(encoding='utf-8')
replacements = {
    "set('issue_expands_in_place',Boolean(document.querySelector(`#issue-item-${safeId('MAP-001')}.expanded .issue-body`)));": "const issueItemId='MAP-001'.replace(/[^a-zA-Z0-9_-]+/g,'_');\n      set('issue_expands_in_place',Boolean(document.querySelector(`#issue-item-${issueItemId}.expanded .issue-body`)));",
    "set('common_discipline_two_roles',sharedRoleIds(shared).length===2);": "const rc2api=window.__TRAJECTORY_REFERENCE_RC2__;\n      set('common_discipline_two_roles',rc2api.sharedRoleIds(shared).length===2);",
    "set('status_payload_compatible',issueStatusPayloadCompatible(issueStatusPayload()));": "set('status_payload_compatible',rc2api.issueStatusPayloadCompatible(rc2api.issueStatusPayload()));",
    "if mode == \"scenario\": checks[\"behavioral_scenario\"] = 'data-rc2-scenario=\"ok\"' in text\n        ok = all(checks.values())": "if mode == \"scenario\":\n            checks[\"behavioral_scenario\"] = 'data-rc2-scenario=\"ok\"' in text\n            result_match = re.search(r'data-rc2-scenario-results=\"([^\"]*)\"', text)\n            error_match = re.search(r'data-rc2-scenario-error=\"([^\"]*)\"', text)\n            print({'scenario_results': result_match.group(1) if result_match else None, 'scenario_error': error_match.group(1) if error_match else None})\n        ok = all(checks.values())",
    """      const soft=allIssues().find(issue=>issue.rule_id==='SOFT_DISTRIBUTION');
      if(soft){focusIssue(soft.issue_id);state.onlyIssues=true;renderAll();}
      set('semester_issue_context',Boolean(document.querySelector('.semester.sem-issue'))&&Boolean(document.querySelector('.discipline.issue-existing,.discipline.issue-candidate')));

      set('editing_controls_hidden',['editBtn','saveSessionBtn','loadSessionBtn','snapshotBtn','changesBtn'].every(id=>byId(id)?.classList.contains('rc2-hidden')));
      set('rc2_builtin_self_test',document.documentElement.dataset.rc2SelfTest==='ok');
      const ok=Object.values(checks).every(Boolean);
      document.documentElement.dataset.rc2Scenario=ok?'ok':'failed';
      document.documentElement.dataset.rc2ScenarioResults=encodeURIComponent(JSON.stringify(checks));
      window.__RC2_SCENARIO_RESULTS__=checks;
      console.log('RC2_SCENARIO',JSON.stringify(checks));""": """      const soft=allIssues().find(issue=>issue.rule_id==='SOFT_DISTRIBUTION');
      if(soft){focusIssue(soft.issue_id);state.onlyIssues=true;renderAll();}
      setTimeout(()=>{
        set('semester_issue_context',Boolean(document.querySelector('.semester.sem-issue'))&&Boolean(document.querySelector('.discipline.issue-existing,.discipline.issue-candidate')));
        set('editing_controls_hidden',['editBtn','saveSessionBtn','loadSessionBtn','snapshotBtn','changesBtn'].every(id=>byId(id)?.classList.contains('rc2-hidden')));
        set('rc2_builtin_self_test',document.documentElement.dataset.rc2SelfTest==='ok');
        const ok=Object.values(checks).every(Boolean);
        document.documentElement.dataset.rc2Scenario=ok?'ok':'failed';
        document.documentElement.dataset.rc2ScenarioResults=encodeURIComponent(JSON.stringify(checks));
        window.__RC2_SCENARIO_RESULTS__=checks;
        console.log('RC2_SCENARIO',JSON.stringify(checks));
      },700);""",
}
for old, new in replacements.items():
    if old not in source:
        raise SystemExit(f'patch marker not found: {old}')
    source = source.replace(old, new, 1)
path.write_text(source, encoding='utf-8')
print({'patched': len(replacements), 'file': str(path)})
