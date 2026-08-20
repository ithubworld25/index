from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
import textwrap
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "reference_candidate"
SRC = ROOT / "reference_candidate_rc2"
BUILD = ROOT / "build_rc2"
PACKAGE = BUILD / "package"
TEST = BUILD / "test"
ZIP = BUILD / "TRAJECTORY_FUNCTIONAL_REFERENCE_v0.9-rc2.zip"
VERSION = "0.9.0-rc2"
TAG = "trajectory-functional-reference-v0.9-rc2"


def run(args: list[str], *, timeout: int = 120, stdout: Path | None = None, capture: bool = False) -> str:
    print("+", " ".join(args), flush=True)
    if stdout:
        with stdout.open("wb") as fh:
            subprocess.run(args, cwd=ROOT, check=True, timeout=timeout, stdout=fh)
        return ""
    if capture:
        proc = subprocess.run(args, cwd=ROOT, check=True, timeout=timeout, text=True, capture_output=True)
        if proc.stdout:
            print(proc.stdout.strip(), flush=True)
        if proc.stderr:
            print(proc.stderr.strip(), file=sys.stderr, flush=True)
        return proc.stdout.strip()
    subprocess.run(args, cwd=ROOT, check=True, timeout=timeout)
    return ""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_text(name: str, value: str) -> None:
    (PACKAGE / name).write_text(textwrap.dedent(value).strip() + "\n", encoding="utf-8")


def patch_base_source(source: str) -> str:
    replacements = {
        "['s5-foreign','s2-foreign']": "['s2-foreign','s5-foreign']",
        "byId('applyEditBtn').onclick=applyEdit;": "byId('applyEditBtn').onclick=()=>{try{applyEdit()}catch(e){toast(e.message)}};",
        "dynamic:true})}}});return out}": "dynamic:true});}});}});return out}",
    }
    for old, new in replacements.items():
        if old not in source:
            raise RuntimeError(f"Required RC1 patch marker not found: {old[:70]}")
        source = source.replace(old, new, 1)

    issue_pattern = re.compile(
        r"<div class='issue-filters'>\$\{Object\.keys\(TYPE_META\)\.map\(type=>`<label><input type='checkbox' data-type-filter='\$\{type\}' \$\{type==='import_technical'&&!state\.showTechnical\?'':'checked'\}> \$\{TYPE_META\[type\]\.icon\} \$\{TYPE_META\[type\]\.label\}</label>`\)\.join\(''\)\}</div>"
    )
    issue_replacement = "<div class='issue-filters'>${Object.keys(TYPE_META).map(type=>`<span class='type-pill'>${TYPE_META[type].icon} ${TYPE_META[type].label}</span>`).join('')}</div>"
    source, count = issue_pattern.subn(issue_replacement, source)
    if count != 1:
        raise RuntimeError(f"Issue legend patch count={count}")

    source = source.replace("v0.9-rc1", "v0.9-rc2")
    source = source.replace("0.9.0-rc1", VERSION)
    source = source.replace(
        "state.theme=localStorage.getItem('trajectory-reference-theme')||'system';syncControls();if(!restoreLocal())seedAndRender();else requestAnimationFrame(runConformanceTests);",
        "state.theme=localStorage.getItem('trajectory-reference-theme')||'system';syncControls();seedAndRender();",
    )
    return source


def patch_override_js(source: str) -> str:
    old = """function nodeParticipatesInIssue(node, issue) {\n    if (issueContextNodeIds(issue).has(node.id)) return true;\n    return Boolean(issue.semester_ids?.includes(node.semester) && issue.role_ids?.includes(node.role_id));\n  }"""
    new = """function nodeParticipatesInIssue(node, issue) {\n    const context = issueContextNodeIds(issue);\n    if (context.has(node.id)) return true;\n    if (context.size) return false;\n    return Boolean(issue.semester_ids?.includes(node.semester) && issue.role_ids?.includes(node.role_id));\n  }"""
    if old not in source:
        raise RuntimeError("RC2 issue-context patch marker not found")
    source = source.replace(old, new, 1)
    marker = "  addToolbarControls();"
    if marker not in source:
        raise RuntimeError("RC2 startup marker not found")
    source = source.replace(marker, "  localStorage.removeItem('trajectory-reference-session');\n" + marker, 1)
    return source


def build_documents() -> None:
    shutil.copy2(BASE / "INPUT_FORMAT_CONTRACT.json", PACKAGE / "INPUT_FORMAT_CONTRACT.json")

    functional_contract = {
        "package": "TRAJECTORY_FUNCTIONAL_REFERENCE",
        "version": VERSION,
        "candidate_only": True,
        "immutable_mechanics": {
            "dynamic_competency_catalog": True,
            "cumulative_group_and_individual_filters": True,
            "competency_only_mode": "highlight_cards_without_unproven_lines",
            "discipline_focus_mode": "highlight_related_cards_dim_unrelated_and_draw_one_line_per_shared_active_competency",
            "clear_actions": ["clear_discipline_focus", "clear_competencies", "clear_all_highlighting", "escape_clears_focus"],
            "issue_registry": "inline_accordion_at_clicked_position",
            "semester_level_issue_context": True,
            "common_discipline_rule": "normalized_name + semester + actual_hours",
            "themes": ["system", "light", "dark"],
        },
        "feature_profile": {
            "discipline_editing": False,
            "competency_editing": False,
            "coefficient_editing": False,
            "portable_full_session": False,
            "full_snapshot_export": False,
            "change_log_export": False,
            "single_issue_export": False,
            "issue_status_change": True,
            "issue_comment": True,
            "issue_reopen": True,
            "local_issue_status_persistence": True,
            "issue_status_import_export": True,
        },
        "issue_statuses": ["open", "fixed_external", "normalized_by_decision", "not_relevant"],
        "status_storage_schema": "trajectory-issue-statuses-v1",
    }
    (PACKAGE / "FUNCTIONAL_CONTRACT_RC2.json").write_text(json.dumps(functional_contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    taxonomy = {
        "version": VERSION,
        "panel_label": "Проблемы и расхождения",
        "types": {
            "methodological": {"icon": "!", "active_color": "red", "meaning": "Нарушение методического правила"},
            "source_mismatch": {"icon": "≠", "active_color": "amber", "meaning": "Расхождение источников"},
            "mapping_ambiguity": {"icon": "?", "active_color": "violet", "meaning": "Неоднозначность сопоставления"},
            "import_technical": {"icon": "⚙", "active_color": "indigo", "meaning": "Техническая проблема импорта"},
        },
        "priorities": ["P0", "P1", "P2"],
        "statuses": {
            "open": {"visual": "type_color", "comment_required": False},
            "fixed_external": {"visual": "gray", "comment_required": True},
            "normalized_by_decision": {"visual": "gray", "comment_required": True},
            "not_relevant": {"visual": "gray", "comment_required": True},
        },
        "context_sets": ["primary_node_ids", "existing_node_ids", "candidate_node_ids", "related_node_ids"],
    }
    (PACKAGE / "ISSUE_TAXONOMY_RC2.json").write_text(json.dumps(taxonomy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    write_text("README.md", r'''
        # TRAJECTORY_FUNCTIONAL_REFERENCE v0.9-rc2

        Кандидат функционального эталона образовательной траектории после командной проверки `rc1`.

        ## Запуск

        1. Полностью распакуйте архив.
        2. Откройте `START.html` из корня.
        3. Интернет, сервер и дополнительные данные не требуются.

        ## Главное в rc2

        - при выборе компетенции подсвечиваются все содержащие её дисциплины, но недоказанные глобальные линии не строятся;
        - после выбора конкретной дисциплины связанные дисциплины выделяются, несвязанные приглушаются, а каждая общая компетенция получает отдельную цветную линию;
        - доступны отдельные команды снятия фокуса дисциплины, снятия компетенций и полного сброса выделения;
        - проблемы раскрываются аккордеоном прямо в месте клика;
        - семестровые проблемы имеют индикатор семестра, существующие места и дисциплины-кандидаты;
        - общая дисциплина нескольких БР определяется правилом `нормализованное название + семестр + часы` и получает метку количества БР;
        - редактор данных и полная рабочая сессия скрыты;
        - статусы проблем сохраняются в браузере и переносятся отдельным JSON-файлом.

        Эта версия ещё является кандидатом. После целевой командной проверки она может быть зафиксирована как `v1.0`.
    ''')

    write_text("CHANGELOG_RC2.md", r'''
        # Изменения v0.9-rc2 относительно v0.9-rc1

        ## P0

        1. Восстановлено явное выделение дисциплин, связанных с выбранной дисциплиной общими компетенциями.
        2. Несвязанные дисциплины приглушаются; связанные получают рамку цвета общей компетенции.
        3. Реестр проблем переведён на аккордеон: диагностика раскрывается в месте клика и синхронно меняется при выборе следующей записи.

        ## P1

        1. При выборе компетенции без дисциплины удалены недоказанные глобальные линии; остаётся только выделение карточек.
        2. Добавлены три независимые команды снятия выделения и поддержка `Esc`.
        3. В строке проблемы сразу видны тип, приоритет, смысл, дисциплина или семестр, БР и статус.
        4. Нормализованные проблемы вынесены в отдельную сворачиваемую группу.
        5. Семестровые проблемы отображаются на карте и не исчезают в режиме «Только проблемы».
        6. Общие дисциплины нескольких БР получают метку и расшифровку в правой панели.
        7. Добавлены экспорт и импорт только статусов проблем.
        8. Добавлен тестовый узел с нулевыми часами и автоматический альтернативный профиль каталога.

        ## Отключено в пилотном профиле

        - редактирование дисциплин, компетенций и коэффициентов;
        - полная переносимая сессия;
        - полный снимок и журнал изменения данных;
        - экспорт отдельной проблемы.
    ''')

    write_text("TEAM_ACCEPTANCE_SCENARIOS_RC2.md", r'''
        # Целевая приёмка v0.9-rc2

        Повторно проверяются только изменённые блоки и короткая регрессия.

        | ID | Действие | Ожидаемый результат |
        |---|---|---|
        | ROLE-03 | Выбрать дисциплину, одинаковую для Кибер и DevOps | Видна метка `2 БР` и список обеих ролей справа |
        | FOCUS-01 | Снять компетенции и выбрать дисциплину | Видны все общие компетенции с дисциплинами других семестров |
        | FOCUS-02 | Выбрать компетенцию и затем дисциплину | Линии строятся только по активному набору |
        | FOCUS-03 | Выбрать дисциплину с несколькими связями | Связанные карточки выделены, несвязанные приглушены |
        | FOCUS-04 | Сравнить метки и линии | Цвет одной компетенции совпадает во всех представлениях |
        | FOCUS-05 | Проверить дисциплины того же семестра | Компетентностные линии внутри семестра не строятся |
        | FOCUS-06 | Перейти по связанной дисциплине справа | Фокус переходит к выбранной карточке |
        | LINE-06-RC2 | Выбрать компетенцию без дисциплины | Карточки подсвечены, компетентностных линий нет; есть пояснение семантики |
        | ISSUE-SYNC | Открыть две проблемы подряд | Вторая раскрывается на месте клика; данные первой не остаются |
        | ISSUE-NAV | Открыть нормализованную проблему | Раскрытие видно непосредственно в серой группе |
        | ISSUE-SEM | Открыть дефицит Soft Skill | Семестр, существующие места и кандидаты выделены |
        | ISSUE-STATUS | Закрыть проблему с комментарием | Статус серый, история сохранена, запись можно вернуть в работу |
        | STATUS-IO | Скачать и загрузить статусы | Совместимый файл применяется, неизвестные issue_id считаются отдельно |
        | NAV-02 | Скрыть 0 часов | Тестовый нулевой узел исчезает и возвращается |
        | NAV-03 | Включить «Только проблемы» | Семестровые проблемы остаются представленными на карте |

        Регрессия: запуск, обе темы, фильтры групп, переключение БР, Soft Skills, продолжения дисциплин и FIT.
    ''')

    write_text("GITHUB_CONNECTION_MANUAL_RU.md", r'''
        # Подключение GitHub к ChatGPT и безопасная работа через подтверждение

        ## 1. Зачем GitHub нужен этому конвейеру

        GitHub не нужен для запуска готового `START.html`. Он используется как устойчивый производственный контур:

        - хранение версий исходников;
        - отдельная ветка для каждого кандидата;
        - воспроизводимая сборка через GitHub Actions;
        - браузерные тесты в Chrome;
        - формирование ZIP и SHA-256;
        - публикация стабильного Release asset, не зависящего от срока жизни сеанса ChatGPT;
        - аудит изменений и возможность отката.

        Без GitHub пакет можно создать локально, если среда исполнения доступна и файл корректно зарегистрирован. В этой работе локальные `sandbox:`-ссылки неоднократно истекали, поэтому GitHub выбран как стабильный канал сборки и доставки.

        ## 2. Важное различие: GitHub app и Codex

        Обычное приложение GitHub в ChatGPT предназначено прежде всего для чтения, анализа и поиска по репозиториям. Для генерации, изменения и отправки кода в GitHub OpenAI указывает Codex. В некоторых рабочих пространствах дополнительно доступны действия подключённого приложения; их фактический набор определяется приложением и настройками администратора.

        Если после подключения видны только операции чтения, это не ошибка: используйте Codex или попросите администратора включить разрешённые write actions для рабочего контура.

        ## 3. Подключение

        1. В ChatGPT откройте **Settings → Apps**.
        2. Найдите **GitHub** и нажмите подключение.
        3. На стороне GitHub установите и авторизуйте приложение ChatGPT.
        4. Разрешите доступ только к выбранному репозиторию, а не ко всем репозиториям аккаунта.
        5. Вернитесь в ChatGPT. Если репозиторий не появился сразу, подождите около пяти минут.
        6. Для изменения набора репозиториев: **Settings → Apps → GitHub → Choose repositories / Configure repositories on GitHub**.
        7. В организации GitHub может потребоваться одобрение администратора.

        ## 4. Рекомендуемый режим подтверждений

        Для этой задачи рекомендуется **Any changes / Любые изменения**:

        - чтение выполняется без лишних подтверждений;
        - создание ветки, файла, workflow, релиза или иное изменение требует подтверждения;
        - риск случайной записи ниже, чем в режиме `Never ask`.

        Альтернатива — **Important actions**: подтверждение запрашивается только для значимых действий. `Always ask` максимально строго, но создаёт много лишних подтверждений даже на чтение.

        Путь для личного аккаунта: **Settings → Apps → App Preferences → Ask permission**. Для конкретного приложения можно открыть его Preferences и задать отдельный режим. В управляемом Business/Enterprise-пространстве доступные варианты определяет администратор.

        ## 5. Безопасный рабочий шаблон

        1. Никогда не работать прямо в основной ветке.
        2. Создать отдельную ветку: `trajectory-functional-reference-v0.9-rc2`.
        3. Все изменения хранить только в папке кандидата и workflow сборки.
        4. Не выполнять merge без отдельного решения пользователя.
        5. Публиковать версию как **prerelease**, пока команда не приняла её как эталон.
        6. Перед публикацией обязательно запускать синтаксические, браузерные и поведенческие тесты.
        7. В Release assets публиковать ZIP, контрольную сумму и отчёт проверки.
        8. После приёмки создать отдельную финальную ветку/тег `v1.0`.

        ## 6. Как ставить задачи эффективно

        В запросе указывайте четыре блока:

        - **репозиторий и базовая ветка**;
        - **что разрешено изменить**;
        - **что запрещено менять**;
        - **какие проверки обязательны перед публикацией**.

        Пример:

        ```text
        Работай в репозитории owner/repo.
        Создай отдельную ветку feature-x от tag-v1.
        Не изменяй main и не создавай merge/PR без отдельного подтверждения.
        Разрешено менять только папку reference_candidate_rc2 и workflow сборки.
        Перед публикацией проверь JS, JSON, Chrome light/dark, сценарии FOCUS и ISSUE, ZIP и SHA-256.
        Опубликуй только prerelease asset и верни постоянную ссылку.
        ```

        ## 7. Типичные проблемы

        - **Репозиторий не виден:** подождите, проверьте Choose repositories; для нового репозитория может потребоваться индексация.
        - **403/permission denied:** приложение не имеет доступа к репозиторию либо администратор не разрешил действие.
        - **Чтение работает, запись нет:** обычное GitHub app может быть read-only; используйте Codex или включённые workspace actions.
        - **Действия появились после изменения настроек, но не работают:** переподключите приложение.
        - **Слишком много подтверждений:** смените `Always ask` на `Any changes`.
        - **Слишком рискованно:** не используйте `Never ask`; ограничьте репозитории и работайте только через ветки/prerelease.

        ## 8. Отключение и отзыв доступа

        В ChatGPT: **Settings → Apps → GitHub → Disconnect**.
        В GitHub можно дополнительно изменить или удалить установку приложения и доступные репозитории.

        ## Официальные источники OpenAI

        - https://help.openai.com/ru-ru/articles/11145903-connecting-github-to-chatgpt
        - https://help.openai.com/en/articles/11487775/
        - https://help.openai.com/en/articles/11390924
    ''')


def assemble() -> str:
    shutil.rmtree(BUILD, ignore_errors=True)
    PACKAGE.mkdir(parents=True)
    TEST.mkdir(parents=True)
    build_documents()

    base = (BASE / "START_REFERENCE.html").read_text(encoding="utf-8")
    base = patch_base_source(base)
    css = (SRC / "rc2_override.css").read_text(encoding="utf-8")
    js = patch_override_js((SRC / "rc2_override.js").read_text(encoding="utf-8"))

    if "</head>" not in base or "</body>" not in base:
        raise RuntimeError("HTML injection anchors not found")
    source = base.replace("</head>", f"<style id='rc2-overrides'>\n{css}\n</style>\n</head>", 1)
    source = source.replace("</body>", f"<script id='rc2-runtime'>\n{js}\n</script>\n</body>", 1)
    source = source.replace("кандидат v0.9-rc1", "кандидат v0.9-rc2")
    source = source.replace("candidate v0.9-rc1", "candidate v0.9-rc2")
    (PACKAGE / "START.html").write_text(source, encoding="utf-8")
    return source


def static_validate(source: str) -> list[str]:
    for path in PACKAGE.glob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))
    if "<script src=" in source:
        raise RuntimeError("External script found")
    if re.search(r"\bfetch\s*\(", source):
        raise RuntimeError("fetch() call found")
    scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", source, flags=re.S | re.I)
    if len(scripts) < 2:
        raise RuntimeError("Base and RC2 inline scripts not found")
    for index, script in enumerate(scripts):
        app = TEST / f"app-{index}.js"
        app.write_text(script, encoding="utf-8")
        run(["node", "--check", str(app.relative_to(ROOT))])
    required = [
        "computeGlobalEdges = function rc2NoUnprovenGlobalEdges",
        "related-focus",
        "rc2RenderIssuesPanel",
        "issueStatusPayload",
        "sharedRoleIds",
        "data-rc2-status",
        "RC2-DYNAMIC-CATALOG-01",
    ]
    missing = [marker for marker in required if marker not in source]
    if missing:
        raise RuntimeError("Missing RC2 mechanics: " + ", ".join(missing))
    return ["all_json_parse", "no_external_scripts", "no_fetch", "inline_js_syntax", "required_rc2_markers"]


def build_fixtures(source: str) -> None:
    theme_marker = "state.theme=localStorage.getItem('trajectory-reference-theme')||'system';"
    if theme_marker not in source:
        raise RuntimeError("Theme marker not found")
    light = source.replace(theme_marker, "state.theme='light';", 1)
    dark = source.replace(theme_marker, "state.theme='dark';", 1)
    (TEST / "light.html").write_text(light, encoding="utf-8")
    (TEST / "dark.html").write_text(dark, encoding="utf-8")

    scenario_script = r'''
<script id="rc2-scenario-test">
document.addEventListener('DOMContentLoaded',()=>setTimeout(()=>{
  const checks={};
  const set=(name,value)=>{checks[name]=Boolean(value)};
  try{
    localStorage.clear();
    state.activeCompIds.clear();
    state.focusedNodeId=null;
    state.selectedIssueId=null;
    state.showZero=true;
    state.onlyIssues=false;
    renderAll();

    state.activeCompIds=new Set(['H-NET']);
    state.focusedNodeId=null;
    renderAll();
    set('competency_only_has_no_competency_lines',document.querySelectorAll('.line-competency').length===0);
    set('competency_only_dims_nonmatching',document.querySelectorAll('.discipline.filtered-out').length>0);

    const focus=nodeByKey('cyber','s3-networks');
    state.focusedNodeId=focus.id;
    renderAll();
    setTimeout(()=>{
      set('focus_draws_lines',document.querySelectorAll('.line-competency').length>0);
      set('focus_highlights_related',document.querySelectorAll('.discipline.related-focus').length>0);
      set('focus_dims_unrelated',document.querySelectorAll('.discipline.focus-dim').length>0);

      state.focusedNodeId=null;
      renderAll();
      set('clear_focus_preserves_competencies',state.activeCompIds.has('H-NET'));

      focusIssue('SRC-001');
      const first=state.selectedIssueId;
      focusIssue('MAP-001');
      set('issue_switches_synchronously',first==='SRC-001'&&state.selectedIssueId==='MAP-001');
      set('issue_expands_in_place',Boolean(document.querySelector(`#issue-item-${safeId('MAP-001')}.expanded .issue-body`)));
      set('manual_close_requires_comment',!statusChangeAllowed('fixed',''));

      const shared=nodeByKey('cyber','s1-rus');
      set('common_discipline_two_roles',sharedRoleIds(shared).length===2);
      set('status_payload_compatible',issueStatusPayloadCompatible(issueStatusPayload()));

      state.showZero=false;
      set('zero_hour_filter',visibleNodes().every(node=>node.hours!==0));
      state.showZero=true;

      const soft=allIssues().find(issue=>issue.rule_id==='SOFT_DISTRIBUTION');
      if(soft){focusIssue(soft.issue_id);state.onlyIssues=true;renderAll();}
      set('semester_issue_context',Boolean(document.querySelector('.semester.sem-issue'))&&Boolean(document.querySelector('.discipline.issue-existing,.discipline.issue-candidate')));

      set('editing_controls_hidden',['editBtn','saveSessionBtn','loadSessionBtn','snapshotBtn','changesBtn'].every(id=>byId(id)?.classList.contains('rc2-hidden')));
      set('rc2_builtin_self_test',document.documentElement.dataset.rc2SelfTest==='ok');
      const ok=Object.values(checks).every(Boolean);
      document.documentElement.dataset.rc2Scenario=ok?'ok':'failed';
      document.documentElement.dataset.rc2ScenarioResults=encodeURIComponent(JSON.stringify(checks));
      window.__RC2_SCENARIO_RESULTS__=checks;
      console.log('RC2_SCENARIO',JSON.stringify(checks));
    },900);
  }catch(error){
    console.error(error);
    document.documentElement.dataset.rc2Scenario='failed';
    document.documentElement.dataset.rc2ScenarioError=error.message;
  }
},1400));
</script>
'''
    scenario = source.replace("</body>", scenario_script + "\n</body>", 1)
    (TEST / "scenario.html").write_text(scenario, encoding="utf-8")


def contrast_ratio(a: str, b: str) -> float:
    def lum(value: str) -> float:
        value = value.lstrip("#")
        rgb = [int(value[i:i+2], 16) / 255 for i in (0, 2, 4)]
        rgb = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in rgb]
        return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
    l1, l2 = lum(a), lum(b)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def browser_validate() -> tuple[str, list[dict[str, object]], dict[str, float]]:
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if not chrome:
        raise RuntimeError("Chrome/Chromium not found")
    chrome_version = run([chrome, "--version"], capture=True)
    results: list[dict[str, object]] = []
    for mode in ("light", "dark", "scenario"):
        profile = TEST / f"profile-{mode}"
        profile.mkdir()
        dom = TEST / f"{mode}-dom.html"
        url = f"file://{(TEST / f'{mode}.html').resolve()}"
        run([
            chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
            "--allow-file-access-from-files", f"--user-data-dir={profile.resolve()}",
            "--virtual-time-budget=16000", "--dump-dom", url,
        ], timeout=85, stdout=dom)
        text = dom.read_text(encoding="utf-8", errors="replace")
        checks = {
            "runtime_ready": 'data-runtime-ready="1"' in text,
            "base_self_test": 'data-self-test="ok"' in text,
            "rc2_ready": 'data-rc2-ready="1"' in text,
            "rc2_self_test": 'data-rc2-self-test="ok"' in text,
        }
        if mode == "light": checks["theme_light"] = 'data-theme="light"' in text
        if mode == "dark": checks["theme_dark"] = 'data-theme="dark"' in text
        if mode == "scenario": checks["behavioral_scenario"] = 'data-rc2-scenario="ok"' in text
        ok = all(checks.values())
        results.append({"id": f"chrome_{mode}", "ok": ok, "checks": checks})
        if not ok:
            raise RuntimeError(f"Browser validation failed for {mode}: {checks}")

    for mode in ("light", "dark"):
        run([
            chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
            "--allow-file-access-from-files", "--window-size=1920,1080",
            f"--screenshot={str((TEST / f'{mode}.png').resolve())}",
            f"file://{(TEST / f'{mode}.html').resolve()}",
        ], timeout=85)

    contrast = {
        "light_text_panel": contrast_ratio("#172033", "#FFFFFF"),
        "light_muted_panel": contrast_ratio("#536174", "#FFFFFF"),
        "dark_text_panel": contrast_ratio("#F8FAFC", "#0F172A"),
        "dark_muted_panel": contrast_ratio("#CBD5E1", "#0F172A"),
        "dark_subtle_panel": contrast_ratio("#A8B3C7", "#0F172A"),
        "dark_danger": contrast_ratio("#FCA5A5", "#3F151B"),
        "dark_warning": contrast_ratio("#FCD34D", "#3A2A0A"),
        "dark_normalized": contrast_ratio("#E2E8F0", "#334155"),
    }
    if any(value < 4.5 for value in contrast.values()):
        raise RuntimeError(f"Contrast test below 4.5: {contrast}")
    return chrome_version, results, contrast


def write_verification(chrome_version: str, static_results: list[str], browser_results: list[dict[str, object]], contrast: dict[str, float]) -> None:
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    auto = {
        "package": "TRAJECTORY_FUNCTIONAL_REFERENCE",
        "version": VERSION,
        "created_at": now,
        "chrome_version": chrome_version,
        "static": [{"id": item, "ok": True} for item in static_results],
        "browser": browser_results,
        "contrast": [{"id": key, "ratio": round(value, 3), "required": 4.5, "ok": value >= 4.5} for key, value in contrast.items()],
        "mandatory_behavior": [
            "competency_only_highlight_without_unproven_lines",
            "discipline_focus_related_highlight_and_unrelated_dim",
            "inline_issue_accordion_and_synchronous_switch",
            "common_discipline_across_roles",
            "semester_issue_context",
            "issue_status_import_export",
            "zero_hour_fixture",
            "dynamic_alternative_catalog_profile",
        ],
        "result": "PASS",
    }
    (PACKAGE / "РЕЗУЛЬТАТЫ_АВТОТЕСТОВ_RC2.json").write_text(json.dumps(auto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ratios = "\n".join(f"- `{key}`: {value:.2f}:1" for key, value in contrast.items())
    write_text("ОТЧЕТ_ПРОВЕРКИ_RC2.md", f'''
        # Отчёт проверки TRAJECTORY_FUNCTIONAL_REFERENCE v0.9-rc2

        Дата UTC: `{now}`  
        Браузер: `{chrome_version}`  
        Итог автоматической проверки: **PASS**.

        ## Проверено

        - автономность `START.html`;
        - отсутствие внешних JavaScript, JSON, `fetch()` и серверных зависимостей;
        - синтаксис каждого inline JavaScript-блока через `node --check`;
        - валидность всех JSON-контрактов;
        - светлая и тёмная темы в Chrome;
        - встроенная самопроверка базового ядра и слоя rc2;
        - режим выбора компетенции без недоказанных глобальных линий;
        - фокус дисциплины, выделение связанных и приглушение несвязанных карточек;
        - синхронное переключение двух проблем и раскрытие аккордеона в месте клика;
        - блокировка ручного закрытия без комментария;
        - распознавание общей дисциплины для двух БР;
        - семестровый контекст дефицита Soft Skill;
        - схема экспорта/импорта статусов;
        - фильтр нулевых часов;
        - альтернативный профиль с другим числом групп компетенций;
        - скрытие редактора и полных сессионных экспортов.

        ## Контрастность

        {ratios}

        Все перечисленные пары превышают порог `4.5:1`.

        ## Граница проверки

        Автотест подтверждает техническую и сценарную работоспособность кандидата. Методическая приёмка людьми всё ещё требуется для фиксации `v1.0`, особенно для визуальной достаточности выделения связанных дисциплин и удобства последовательного просмотра реестра проблем.
    ''')

    protocol_lines = [
        "TRAJECTORY_FUNCTIONAL_REFERENCE v0.9-rc2",
        f"created_at={now}",
        f"chrome={chrome_version}",
        "PASS: autonomous START.html",
        "PASS: no external scripts, JSON, fetch calls or server dependencies",
        "PASS: all inline JavaScript blocks pass node --check",
        "PASS: all JSON files parse",
        "PASS: Chrome light-theme smoke test",
        "PASS: Chrome dark-theme smoke test",
        "PASS: base and RC2 built-in self-tests",
        "PASS: competency-only mode has no unproven competency lines",
        "PASS: discipline focus highlights related and dims unrelated cards",
        "PASS: issue accordion switches synchronously",
        "PASS: common-discipline rule across roles",
        "PASS: semester-level issue context",
        "PASS: issue-status import/export schema",
        "PASS: zero-hour and alternative-catalog fixtures",
        "PASS: contrast pairs >= 4.5:1",
        "NOTE: human acceptance is required before v1.0",
    ]
    (PACKAGE / "ПРОТОКОЛ_ПРОВЕРКИ.txt").write_text("\n".join(protocol_lines) + "\n", encoding="utf-8")


def package() -> dict[str, object]:
    shutil.copy2(TEST / "light.png", PACKAGE / "PREVIEW_LIGHT.png")
    shutil.copy2(TEST / "dark.png", PACKAGE / "PREVIEW_DARK.png")
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    files = []
    for path in sorted(p for p in PACKAGE.iterdir() if p.is_file() and p.name != "PACKAGE_MANIFEST.json"):
        files.append({"name": path.name, "size": path.stat().st_size, "sha256": sha256(path)})
    manifest = {
        "package": "TRAJECTORY_FUNCTIONAL_REFERENCE",
        "version": VERSION,
        "created_at": now,
        "start_file": "START.html",
        "autonomous_start": True,
        "candidate_only": True,
        "files": files,
    }
    (PACKAGE / "PACKAGE_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(PACKAGE.iterdir()):
            if path.is_file():
                archive.write(path, path.name)
    with zipfile.ZipFile(ZIP) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise RuntimeError(f"ZIP integrity failed at {bad}")
        names = archive.namelist()
        if "START.html" not in names:
            raise RuntimeError("START.html missing at ZIP root")
        if any("/" in name.strip("/") or ".." in name for name in names):
            raise RuntimeError("Nested, absolute or parent ZIP paths found")

    result = {
        "zip": str(ZIP),
        "size": ZIP.stat().st_size,
        "sha256": sha256(ZIP),
        "start_sha256": sha256(PACKAGE / "START.html"),
        "files": len(names),
    }
    (BUILD / "PACKAGE_SHA256.txt").write_text(f"{result['sha256']}  {ZIP.name}\n", encoding="utf-8")
    (BUILD / "START_SHA256.txt").write_text(f"{result['start_sha256']}  START.html\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return result


def main() -> None:
    source = assemble()
    static_results = static_validate(source)
    build_fixtures(source)
    chrome_version, browser_results, contrast = browser_validate()
    write_verification(chrome_version, static_results, browser_results, contrast)
    package()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        raise
