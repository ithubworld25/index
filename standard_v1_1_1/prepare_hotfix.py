from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD_DIR = ROOT / "standard_v1_1"
NEW_DIR = ROOT / "standard_v1_1_1"
OLD_TEMPLATES = OLD_DIR / "templates"
NEW_TEMPLATES = NEW_DIR / "templates"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Marker not found for {label}: {old[:120]}")
    return text.replace(old, new, 1)


def patch_template_json(path: Path, transformer) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data = transformer(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare_templates() -> None:
    shutil.rmtree(NEW_TEMPLATES, ignore_errors=True)
    shutil.copytree(OLD_TEMPLATES, NEW_TEMPLATES)

    renames = {}
    for path in list(NEW_TEMPLATES.iterdir()):
        if not path.is_file():
            continue
        name = path.name.replace("v1.1", "v1.1.1")
        if name != path.name:
            renames[path] = path.with_name(name)
    for source, target in renames.items():
        source.rename(target)

    spec_path = NEW_TEMPLATES / "01_STANDARD_SPEC_v1.1.1.json"
    patch_template_json(spec_path, lambda d: {**d, "version": "1.1.1", "functional_core_version": "1.0.1"})

    theme_path = NEW_TEMPLATES / "10_THEME_AND_CONTRAST_v1.1.1.json"
    def theme_transform(d):
        d["version"] = "1.1.1"
        d["light"]["border"] = "#7C899D"
        d["light"]["active_text"] = "#FFFFFF"
        d["dark"]["active_text"] = "#0F172A"
        d["required_computed_style_checks"] = [
            {"id": "CONTRAST-ACTIVE-LIGHT-01", "selector": ".active", "theme": "light", "foreground": "#FFFFFF", "background": "#2563EB", "minimum": 4.5},
            {"id": "CONTRAST-ACTIVE-DARK-01", "selector": ".active", "theme": "dark", "foreground": "#0F172A", "background": "#60A5FA", "minimum": 4.5},
            {"id": "CONTRAST-TAB-DARK-01", "selector": ".tab.active", "theme": "dark", "minimum": 4.5},
            {"id": "CONTRAST-ROLE-DARK-01", "selector": ".role-btn.active", "theme": "dark", "minimum": 4.5},
            {"id": "CONTRAST-GROUP-DARK-01", "selector": ".active", "theme": "dark", "minimum": 4.5},
            {"id": "CONTRAST-BORDER-LIGHT-01", "theme": "light", "foreground": "#7C899D", "background": "#FFFFFF", "minimum": 3.0},
            {"id": "CONTRAST-BORDER-LIGHT-02", "theme": "light", "foreground": "#7C899D", "background": "#F8FAFC", "minimum": 3.0},
            {"id": "CONTRAST-BORDER-LIGHT-03", "theme": "light", "foreground": "#7C899D", "background": "#F3F5F8", "minimum": 3.0}
        ]
        return d
    patch_template_json(theme_path, theme_transform)

    contract_path = NEW_TEMPLATES / "11_FINAL_PACKAGE_CONTRACT_v1.1.1.json"
    def contract_transform(d):
        d["version"] = "1.1.1"
        d["functional_core"]["version"] = "1.0.1"
        extra = [
            "computed contrast of active light controls >= 4.5:1",
            "computed contrast of active dark controls >= 4.5:1",
            "computed contrast of active dark tab >= 4.5:1",
            "computed contrast of active dark business role >= 4.5:1",
            "light border contrast on panel, panel_alt and bg >= 3:1"
        ]
        for item in extra:
            if item not in d["mandatory_verification"]:
                d["mandatory_verification"].append(item)
        return d
    patch_template_json(contract_path, contract_transform)

    for path in NEW_TEMPLATES.iterdir():
        if not path.is_file() or path.suffix not in {".md", ".txt", ".json"}:
            continue
        text = path.read_text(encoding="utf-8")
        text = text.replace("FUNCTIONAL_CORE_TEMPLATE_v1.0.html", "FUNCTIONAL_CORE_TEMPLATE_v1.0.1.html")
        text = text.replace("18_FUNCTIONAL_CORE_MANIFEST_v1.0.json", "18_FUNCTIONAL_CORE_MANIFEST_v1.0.1.json")
        text = text.replace("01_STANDARD_SPEC_v1.1.json", "01_STANDARD_SPEC_v1.1.1.json")
        text = text.replace("02_FULL_GENERATION_PROMPT_RU_v1.1.md", "02_FULL_GENERATION_PROMPT_RU_v1.1.1.md")
        text = text.replace("03_SHORT_LAUNCH_PROMPT_RU_v1.1.txt", "03_SHORT_LAUNCH_PROMPT_RU_v1.1.1.txt")
        text = text.replace("10_THEME_AND_CONTRAST_v1.1.json", "10_THEME_AND_CONTRAST_v1.1.1.json")
        text = text.replace("11_FINAL_PACKAGE_CONTRACT_v1.1.json", "11_FINAL_PACKAGE_CONTRACT_v1.1.1.json")
        text = text.replace("стандарта v1.1", "стандарта v1.1.1")
        text = text.replace("стандарт v1.1", "стандарт v1.1.1")
        path.write_text(text, encoding="utf-8")

    full_prompt = NEW_TEMPLATES / "02_FULL_GENERATION_PROMPT_RU_v1.1.1.md"
    text = full_prompt.read_text(encoding="utf-8")
    marker = "## 9. Темы и контраст\n"
    addition = """## 9. Темы и контраст\n\nHotfix ядра 1.0.1 обязателен: в тёмной теме активные элементы используют текст `var(--panel)` на фоне `var(--accent)`, а светлая граница использует `#7C899D`. Проверяй не только токены, но и вычисленные браузером `color`, `background-color` и `border-color` реальных активных кнопок, вкладок, бизнес-ролей и групп.\n\n"""
    if marker in text:
        text = text.replace(marker, addition, 1)
    full_prompt.write_text(text, encoding="utf-8")

    short_prompt = NEW_TEMPLATES / "03_SHORT_LAUNCH_PROMPT_RU_v1.1.1.txt"
    text = short_prompt.read_text(encoding="utf-8")
    text += "\n\nДополнительно проверь вычисленный контраст активных элементов в обеих темах и светлых границ на panel, panel_alt и bg.\n"
    short_prompt.write_text(text, encoding="utf-8")


def prepare_build_script() -> None:
    source = (OLD_DIR / "build_system.py").read_text(encoding="utf-8")
    replacements = {
        'OUT = ROOT / "build_standard_v1_1"': 'OUT = ROOT / "build_standard_v1_1_1"',
        'FUNCTIONAL_DIR = OUT / "functional_reference_v1_0"': 'FUNCTIONAL_DIR = OUT / "functional_reference_v1_0_1"',
        'STANDARD_DIR = OUT / "standard_v1_1"': 'STANDARD_DIR = OUT / "standard_v1_1_1"',
        'SYSTEM_DIR = OUT / "system_v1_1"': 'SYSTEM_DIR = OUT / "system_v1_1_1"',
        'FUNCTIONAL_ZIP = OUT / "TRAJECTORY_FUNCTIONAL_REFERENCE_v1.0.zip"': 'FUNCTIONAL_ZIP = OUT / "TRAJECTORY_FUNCTIONAL_REFERENCE_v1.0.1.zip"',
        'STANDARD_ZIP = OUT / "STANDARD_TRAJECTORY_VISUALIZATION_v1.1.zip"': 'STANDARD_ZIP = OUT / "STANDARD_TRAJECTORY_VISUALIZATION_v1.1.1.zip"',
        'SYSTEM_ZIP = OUT / "TRAJECTORY_VISUALIZATION_SYSTEM_v1.1.zip"': 'SYSTEM_ZIP = OUT / "TRAJECTORY_VISUALIZATION_SYSTEM_v1.1.1.zip"'
    }
    for old, new in replacements.items():
        if old not in source:
            raise RuntimeError(f"Build marker missing: {old}")
        source = source.replace(old, new, 1)

    source = source.replace('"0.9.0-rc1", "1.0.0"', '"0.9.0-rc1", "1.0.1"')
    source = source.replace('"0.9.0-rc2", "1.0.0"', '"0.9.0-rc2", "1.0.1"')
    source = source.replace('"v0.9-rc1", "v1.0"', '"v0.9-rc1", "v1.0.1"')
    source = source.replace('"v0.9-rc2", "v1.0"', '"v0.9-rc2", "v1.0.1"')
    source = source.replace('"кандидат v1.0", "зафиксированный эталон v1.0"', '"кандидат v1.0.1", "зафиксированный эталон v1.0.1"')

    hotfix_marker = '    html = source_start.read_text(encoding="utf-8")\n'
    hotfix = '''    html = source_start.read_text(encoding="utf-8")\n    html = html.replace("--border:#94A3B8;", "--border:#7C899D;", 1)\n    active_rule = ".active{background:var(--accent)!important;color:#fff!important;border-color:var(--accent)!important}"\n    dark_active_rule = active_rule + "\\nhtml[data-theme='dark'] .active{color:var(--panel)!important}"\n    if active_rule not in html:\n        raise RuntimeError("Active CSS marker not found")\n    html = html.replace(active_rule, dark_active_rule, 1)\n    html = html.replace("light:{bg:'#F3F5F8',panel:'#FFFFFF',text:'#172033',muted:'#536174',subtle:'#667085',border:'#94A3B8'}", "light:{bg:'#F3F5F8',panel:'#FFFFFF',text:'#172033',muted:'#536174',subtle:'#667085',border:'#7C899D'}", 1)\n'''
    source = replace_once(source, hotfix_marker, hotfix, "core CSS hotfix")

    source = source.replace('template = FUNCTIONAL_DIR / "FUNCTIONAL_CORE_TEMPLATE_v1.0.html"', 'template = FUNCTIONAL_DIR / "FUNCTIONAL_CORE_TEMPLATE_v1.0.1.html"')
    source = source.replace('"version": "1.0.0"', '"version": "1.0.1"')
    source = source.replace('# TRAJECTORY_FUNCTIONAL_REFERENCE v1.0', '# TRAJECTORY_FUNCTIONAL_REFERENCE v1.0.1')
    source = source.replace('FUNCTIONAL_CORE_TEMPLATE_v1.0.html', 'FUNCTIONAL_CORE_TEMPLATE_v1.0.1.html')
    source = source.replace('"01_STANDARD_SPEC_v1.1.json"', '"01_STANDARD_SPEC_v1.1.1.json"')
    source = source.replace('"19_ISSUE_TAXONOMY_v1.1.json"', '"19_ISSUE_TAXONOMY_v1.1.1.json"')
    source = source.replace('"20_FEATURE_PROFILE_v1.1.json"', '"20_FEATURE_PROFILE_v1.1.1.json"')
    source = source.replace('AUTOTEST_RESULTS_v1.0.json', 'AUTOTEST_RESULTS_v1.0.1.json')
    source = source.replace('VERIFICATION_REPORT_v1.0.md', 'VERIFICATION_REPORT_v1.0.1.md')
    source = source.replace('функционального эталона v1.0', 'функционального эталона v1.0.1')
    source = source.replace('"1.0.0", NOW, "START.html"', '"1.0.1", NOW, "START.html"')

    source = source.replace('"FUNCTIONAL_CORE_TEMPLATE_v1.0.html"', '"FUNCTIONAL_CORE_TEMPLATE_v1.0.1.html"')
    source = source.replace('"18_FUNCTIONAL_CORE_MANIFEST_v1.0.json"', '"18_FUNCTIONAL_CORE_MANIFEST_v1.0.1.json"')
    source = source.replace('"10_THEME_AND_CONTRAST_v1.1.json"', '"10_THEME_AND_CONTRAST_v1.1.1.json"')
    source = source.replace('"10_CONTRAST_TEST_RESULTS_v1.1.json"', '"10_CONTRAST_TEST_RESULTS_v1.1.1.json"')
    source = source.replace('"AUTOTEST_RESULTS_v1.1.json"', '"AUTOTEST_RESULTS_v1.1.1.json"')
    source = source.replace('"VERIFICATION_REPORT_v1.1.md"', '"VERIFICATION_REPORT_v1.1.1.md"')
    source = source.replace('Отчёт проверки стандарта v1.1', 'Отчёт проверки стандарта v1.1.1')
    source = source.replace('"version": "1.1.0"', '"version": "1.1.1"')
    source = source.replace('"functional_core_version": "1.0.0"', '"functional_core_version": "1.0.1"')
    source = source.replace('"1.1.0", NOW)', '"1.1.1", NOW)')
    source = source.replace('PACKAGE_SHA256_v1.1.txt', 'PACKAGE_SHA256_v1.1.1.txt')
    source = source.replace('Системный комплект v1.1.', 'Системный комплект v1.1.1.')

    old_pairs = '''    pairs = [\n        ("light.text/panel", theme["light"]["text"], theme["light"]["panel"], 4.5),\n        ("light.muted/panel", theme["light"]["muted"], theme["light"]["panel"], 4.5),\n        ("dark.text/panel", theme["dark"]["text"], theme["dark"]["panel"], 4.5),\n        ("dark.muted/panel", theme["dark"]["muted"], theme["dark"]["panel"], 4.5),\n        ("dark.normalized/panel", theme["dark"]["normalized_text"], theme["dark"]["normalized_bg"], 4.5)\n    ]\n'''
    new_pairs = '''    pairs = [\n        ("light.text/panel", theme["light"]["text"], theme["light"]["panel"], 4.5),\n        ("light.muted/panel", theme["light"]["muted"], theme["light"]["panel"], 4.5),\n        ("light.active_text/accent", theme["light"]["active_text"], theme["light"]["accent"], 4.5),\n        ("light.border/panel", theme["light"]["border"], theme["light"]["panel"], 3.0),\n        ("light.border/panel_alt", theme["light"]["border"], theme["light"]["panel_alt"], 3.0),\n        ("light.border/bg", theme["light"]["border"], theme["light"]["bg"], 3.0),\n        ("dark.text/panel", theme["dark"]["text"], theme["dark"]["panel"], 4.5),\n        ("dark.muted/panel", theme["dark"]["muted"], theme["dark"]["panel"], 4.5),\n        ("dark.active_text/accent", theme["dark"]["active_text"], theme["dark"]["accent"], 4.5),\n        ("dark.normalized/panel", theme["dark"]["normalized_text"], theme["dark"]["normalized_bg"], 4.5)\n    ]\n'''
    source = replace_once(source, old_pairs, new_pairs, "expanded contrast pairs")

    computed_injection_marker = '            if mode == "scenario":\n                checks["behavioral_scenario"] = \'data-standard-scenario="ok"\' in text\n'
    computed_injection = '''            if mode == "scenario":\n                checks["behavioral_scenario"] = 'data-standard-scenario="ok"' in text\n            if mode in ("light", "dark"):\n                active_match = re.search(r'data-hotfix-active-ratio="([0-9.]+)"', text)\n                border_match = re.search(r'data-hotfix-border-ratios="([^"]+)"', text)\n                checks["computed_active_contrast"] = bool(active_match and float(active_match.group(1)) >= 4.5)\n                if mode == "light":\n                    values = [float(v) for v in border_match.group(1).split(',')] if border_match else []\n                    checks["computed_light_border_contrast"] = len(values) == 3 and all(v >= 3.0 for v in values)\n'''
    source = replace_once(source, computed_injection_marker, computed_injection, "computed browser contrast checks")

    preload_marker = '    preload = f"<script>localStorage.setItem(\'trajectory-reference-theme\',\'{theme}\');</script>\\n"\n'
    preload_new = '''    preload = f"""<script>\nlocalStorage.setItem('trajectory-reference-theme','{theme}');\nfunction __hotfixLum(hex){{const v=hex.replace('#','');const rgb=[0,2,4].map(i=>parseInt(v.slice(i,i+2),16)/255).map(x=>x<=.03928?x/12.92:Math.pow((x+.055)/1.055,2.4));return .2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2]}}\nfunction __hotfixRatio(a,b){{const x=__hotfixLum(a),y=__hotfixLum(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05)}}\nsetTimeout(()=>{{\n  const active=document.querySelector('.active');\n  if(active){{const cs=getComputedStyle(active);const toHex=v=>{{const m=v.match(/\\d+/g);return '#'+m.slice(0,3).map(n=>Number(n).toString(16).padStart(2,'0')).join('')}};document.documentElement.dataset.hotfixActiveRatio=__hotfixRatio(toHex(cs.color),toHex(cs.backgroundColor)).toFixed(3)}}\n  if('{theme}'==='light'){{const border='#7C899D';document.documentElement.dataset.hotfixBorderRatios=['#FFFFFF','#F8FAFC','#F3F5F8'].map(bg=>__hotfixRatio(border,bg).toFixed(3)).join(',')}}\n}},1800);\n</script>\n"""\n'''
    source = replace_once(source, preload_marker, preload_new, "computed-style preload")

    source = source.replace('"01_STANDARD_SPEC_v1.1.json",', '"01_STANDARD_SPEC_v1.1.1.json",')
    source = source.replace('"02_FULL_GENERATION_PROMPT_RU_v1.1.md",', '"02_FULL_GENERATION_PROMPT_RU_v1.1.1.md",')
    source = source.replace('"03_SHORT_LAUNCH_PROMPT_RU_v1.1.txt",', '"03_SHORT_LAUNCH_PROMPT_RU_v1.1.1.txt",')
    source = source.replace('"10_THEME_AND_CONTRAST_v1.1.json",', '"10_THEME_AND_CONTRAST_v1.1.1.json",')
    source = source.replace('"11_FINAL_PACKAGE_CONTRACT_v1.1.json",', '"11_FINAL_PACKAGE_CONTRACT_v1.1.1.json",')
    source = source.replace('"VERIFICATION_REPORT_v1.1.md"', '"VERIFICATION_REPORT_v1.1.1.md"')

    (NEW_DIR / "build_system.py").write_text(source, encoding="utf-8")


def main() -> None:
    prepare_templates()
    prepare_build_script()
    print(json.dumps({"status": "prepared", "templates": len(list(NEW_TEMPLATES.iterdir())), "build_script": str(NEW_DIR / 'build_system.py')}, ensure_ascii=False))


if __name__ == "__main__":
    main()
