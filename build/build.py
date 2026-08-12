#!/usr/bin/env python3
from __future__ import annotations

import difflib
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "build" / "input"
OUT = ROOT / "package"
TEMPLATE = ROOT / "build" / "template.html"
YEAR = "2026–2027"
VERSION = "v0.3"


def comp(idx: int, code: str, name: str, group: str) -> dict[str, Any]:
    palettes = {
        "internal": [205, 220, 236, 252, 268, 284, 300, 316, 332, 348, 8, 24, 40],
        "soft": [330, 275, 170, 25, 95],
        "ok": [48, 58, 68, 78, 88, 98, 108, 118, 128],
        "pk": [190, 202, 214, 226, 238, 250, 262, 274, 286, 298, 310, 322, 334, 346, 358, 10],
    }
    gidx = {
        "internal": idx,
        "soft": idx - 13,
        "ok": idx - 18,
        "pk": idx - 27,
    }[group]
    hue = palettes[group][gidx]
    sat = 70 if group != "ok" else 62
    light = 44 if group != "soft" else 46
    return {"idx": idx, "id": f"c{idx}", "code": code, "name": name, "group": group, "color": f"hsl({hue} {sat}% {light}%)"}


CATALOG = [
    comp(0, "ПК 1.1–1.3", "Эксплуатация информационных систем", "internal"),
    comp(1, "ПК 1.4", "Техобслуживание и текущий ремонт", "internal"),
    comp(2, "ПК 2.3", "Тестирование средств защиты", "internal"),
    comp(3, "ПК 2.6", "Регистрация событий в системах", "internal"),
    comp(4, "ПК 2.1, 2.2, 2.4, 2.5", "Безопасность работы с информацией", "internal"),
    comp(5, "ПК 3.1–3.2", "Работа с техническими средствами защиты", "internal"),
    comp(6, "ПК 3.3–3.5", "Физическая защита информатизации", "internal"),
    comp(7, "ПКС 1.1", "Оценка рисков и кризисных индикаторов", "internal"),
    comp(8, "ПКС 1.2", "Расследование инцидентов ИБ", "internal"),
    comp(9, "ПКС 1.4", "Противодействие злоумышленникам", "internal"),
    comp(10, "ПКС 1.5", "Противодействие инцидентам ИБ", "internal"),
    comp(11, "ПКС 1.6", "Тестирование на проникновение", "internal"),
    comp(12, "ПКС 1.7", "Правовое обеспечение ИБ", "internal"),
    comp(13, "ОКS.1", "Креативное мышление", "soft"),
    comp(14, "ОКS.2", "Критическое мышление", "soft"),
    comp(15, "ОКS.3", "Эффективные коммуникации", "soft"),
    comp(16, "ОКS.4", "Самопрезентация", "soft"),
    comp(17, "ОКS.5", "Командная работа", "soft"),
    comp(18, "ОК 01", "Выбирать способы решения задач профессиональной деятельности применительно к различным контекстам", "ok"),
    comp(19, "ОК 02", "Использовать современные средства поиска, анализа и интерпретации информации и информационные технологии", "ok"),
    comp(20, "ОК 03", "Планировать и реализовывать собственное профессиональное и личностное развитие, предпринимательскую деятельность и финансовую грамотность", "ok"),
    comp(21, "ОК 04", "Эффективно взаимодействовать и работать в коллективе и команде", "ok"),
    comp(22, "ОК 05", "Осуществлять устную и письменную коммуникацию на государственном языке Российской Федерации", "ok"),
    comp(23, "ОК 06", "Проявлять гражданско-патриотическую позицию, соблюдать духовно-нравственные ценности и антикоррупционное поведение", "ok"),
    comp(24, "ОК 07", "Содействовать сохранению окружающей среды, ресурсосбережению и действовать в чрезвычайных ситуациях", "ok"),
    comp(25, "ОК 08", "Использовать средства физической культуры для сохранения и укрепления здоровья", "ok"),
    comp(26, "ОК 09", "Пользоваться профессиональной документацией на государственном и иностранном языках", "ok"),
    comp(27, "ПК 1.1", "Производить установку и настройку компонентов автоматизированных систем в защищённом исполнении", "pk"),
    comp(28, "ПК 1.2", "Администрировать компоненты автоматизированной системы в защищённом исполнении", "pk"),
    comp(29, "ПК 1.3", "Обеспечивать бесперебойную работу автоматизированных систем в защищённом исполнении", "pk"),
    comp(30, "ПК 2.1", "Осуществлять установку и настройку программных и программно-аппаратных средств защиты", "pk"),
    comp(31, "ПК 2.2", "Обеспечивать защиту информации программными и программно-аппаратными средствами", "pk"),
    comp(32, "ПК 2.4", "Осуществлять обработку, хранение и передачу информации ограниченного доступа", "pk"),
    comp(33, "ПК 2.5", "Уничтожать информацию и носители информации с использованием средств защиты", "pk"),
    comp(34, "ПК 3.1", "Устанавливать, настраивать и обслуживать технические средства защиты информации", "pk"),
    comp(35, "ПК 3.2", "Эксплуатировать технические средства защиты информации", "pk"),
    comp(36, "ПК 3.3", "Измерять параметры побочных электромагнитных излучений и наводок", "pk"),
    comp(37, "ПК 3.4", "Измерять параметры фоновых шумов и физических полей", "pk"),
    comp(38, "ПК 3.5", "Организовывать работы по физической защите объектов информатизации", "pk"),
    comp(39, "ПК 4.1", "Подготавливать оборудование компьютерной системы и обслуживать программное обеспечение", "pk"),
    comp(40, "ПК 4.2", "Создавать документы, таблицы, презентации, базы данных и работать в графических редакторах", "pk"),
    comp(41, "ПК 4.3", "Использовать ресурсы локальных сетей, Интернета и сервисов", "pk"),
    comp(42, "ПК 4.4", "Обеспечивать применение средств защиты информации в компьютерной системе", "pk"),
]

GROUPS = {
    "internal": {"label": "Внутренние hard", "indices": list(range(0, 13)), "line_mode": "solid"},
    "soft": {"label": "Soft Skills · места оценивания", "indices": list(range(13, 18)), "line_mode": "dashed"},
    "ok": {"label": "ОК ФГОС", "indices": list(range(18, 27)), "line_mode": "solid"},
    "pk": {"label": "ПК ФГОС", "indices": list(range(27, 43)), "line_mode": "solid"},
}


def norm(value: str) -> str:
    s = (value or "").lower().replace("ё", "е").replace("\xa0", " ")
    s = s.replace("профессионной", "профессиональной").replace("0п.", "оп.")
    s = re.sub(r"\bадаптивная\b", "", s)
    s = re.sub(r"\bочный\b", "", s)
    s = s.replace("*", "")
    s = re.sub(r"[^0-9a-zа-я]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def number(value: str | None) -> int:
    if value is None:
        return 0
    s = str(value).strip().replace(",", ".")
    if not s:
        return 0
    try:
        return int(round(float(s)))
    except ValueError:
        return 0


def is_physical(name: str) -> bool:
    return "физическ" in norm(name) and "культур" in norm(name)


def parse_matrix(path: Path, branch: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source_line, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        parts = raw.split("¦")
        if len(parts) < 6:
            continue
        try:
            sem = int(parts[1].strip())
        except ValueError:
            continue
        if not 1 <= sem <= 8:
            continue
        comps: dict[str, int] = {}
        invalid: list[str] = []
        for token in parts[5].split(","):
            token = token.strip()
            if not token or ":" not in token:
                continue
            left, right = token.split(":", 1)
            try:
                idx, coef = int(left), int(float(right))
            except ValueError:
                invalid.append(token)
                continue
            if 0 <= idx < len(CATALOG) and 1 <= coef <= 4:
                comps[str(idx)] = coef
            else:
                invalid.append(token)
        rows.append({
            "source_line": source_line,
            "branch": branch,
            "matrix_role": parts[0].strip(),
            "semester": sem,
            "matrix_hours": number(parts[2]),
            "matrix_code": parts[3].strip(),
            "matrix_name": parts[4].strip(),
            "competencies": comps,
            "invalid_competencies": invalid,
        })
    return rows


def parse_up(path: Path, branch: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source_line, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        parts = raw.split("¦")
        if len(parts) < 5:
            continue
        try:
            sem = int(parts[0].strip())
        except ValueError:
            continue
        if not 1 <= sem <= 8:
            continue
        name = "¦".join(parts[4:]).strip()
        if not name or "самостоятельные часы" in norm(name):
            continue
        rows.append({
            "uid": f"{branch}-up-{source_line}",
            "source_line": source_line,
            "branch": branch,
            "semester": sem,
            "actual_hours": number(parts[1]),
            "fgos_hours": number(parts[2]),
            "code": parts[3].strip(),
            "name": name,
            "norm": norm(name),
            "used_by": [],
        })
    return rows


def is_event_without_explicit_comp(name: str) -> bool:
    n = norm(name)
    return any(x in n for x in ["student camp", "проектная деятельность", "модуль дп"])


def approved_equivalence(matrix_name: str, up_name: str) -> bool:
    a, b = norm(matrix_name), norm(up_name)
    if a == b:
        return True
    pairs = [
        ("русский язык коммуникативные практики", "русский язык коммуникативные практики"),
        ("литература сторителлинг и самопрезентация", "литература сторителлинг и самопрезентация"),
        ("автоматизация разработки программного обеспечения ci cd", "автоматизация разработки программного обеспечения ci cd"),
        ("windows server безопасность", "windows server безопасность"),
    ]
    if (a, b) in pairs or (b, a) in pairs:
        return True
    if a and b and (a in b or b in a) and min(len(a), len(b)) >= 10:
        return True
    if is_physical(matrix_name) and is_physical(up_name):
        return True
    return False


def manual_match(matrix_row: dict[str, Any], up: dict[str, Any]) -> bool:
    mn, un = norm(matrix_row["matrix_name"]), up["norm"]
    sem = matrix_row["semester"]
    code = matrix_row["matrix_code"].replace(" ", "")
    if "информационные технологии в современном мире" in mn and "информатика" in un and up["code"].replace(" ", "") == "ОУП.05у":
        return True
    if "основы информационной безопасности" in mn and "основы информационной безопасности" in un:
        return True
    if sem == 1 and code == "ДУП.02" and "введение в программирование" in un:
        return True
    if sem == 2 and ("основы компьютерных сетей" in mn or "введение в операционные системы" in mn) and "основы компьютерных сетей" in un and "введение в операционные системы" in un:
        return True
    if sem == 4 and matrix_row["matrix_code"].strip() == "МДК.03.03" and mn in un:
        return True
    return False


def choose_up(matrix_row: dict[str, Any], candidates: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    mn = norm(matrix_row["matrix_name"])
    exact = [u for u in candidates if u["norm"] == mn]
    if len(exact) == 1:
        return exact[0], "exact"
    manual = [u for u in candidates if manual_match(matrix_row, u)]
    if len(manual) == 1:
        return manual[0], "manual"
    components = [u for u in candidates if mn and u["norm"] and (mn in u["norm"] or u["norm"] in mn)]
    if len(components) == 1:
        return components[0], "component"
    code = matrix_row["matrix_code"].replace(" ", "")
    if code and code != "-":
        same_code = [u for u in candidates if u["code"].replace(" ", "") == code]
        if len(same_code) == 1:
            return same_code[0], "code"
        if same_code:
            scored = sorted(((difflib.SequenceMatcher(None, mn, u["norm"]).ratio(), u) for u in same_code), reverse=True, key=lambda x: x[0])
            if scored[0][0] >= 0.45 and (len(scored) == 1 or scored[0][0] - scored[1][0] >= 0.10):
                return scored[0][1], "code_fuzzy"
    scored = sorted(((difflib.SequenceMatcher(None, mn, u["norm"]).ratio(), u) for u in candidates), reverse=True, key=lambda x: x[0])
    if scored and scored[0][0] >= 0.84 and (len(scored) == 1 or scored[0][0] - scored[1][0] >= 0.08):
        return scored[0][1], "fuzzy"
    return None, "unattached"


def is_composite(up_name: str) -> bool:
    n = up_name.lower()
    return "/" in n or "./" in n or n.count("/") >= 1


def build_branch(branch: str, label: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    matrix_rows = parse_matrix(INPUT / f"{branch}_matrix.txt", branch)
    up_rows = parse_up(INPUT / f"{branch}_up.txt", branch)
    up_by_sem: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for u in up_rows:
        up_by_sem[u["semester"]].append(u)

    nodes: list[dict[str, Any]] = []
    source_errors: list[dict[str, Any]] = []
    for seq, m in enumerate(matrix_rows, start=1):
        match, match_type = choose_up(m, up_by_sem[m["semester"]])
        if match:
            match["used_by"].append(seq)
        split = bool(match and (match_type == "component" or (is_composite(match["name"]) and not approved_equivalence(m["matrix_name"], match["name"]))))
        if match and split:
            display_name = m["matrix_name"].strip()
            display_hours = m["matrix_hours"]
            display_code = m["matrix_code"] or match["code"]
            source_mode = "split_from_up"
        elif match:
            display_name = match["name"].strip().rstrip("*").strip()
            display_hours = match["actual_hours"]
            display_code = match["code"] or m["matrix_code"]
            source_mode = "up"
        else:
            display_name = m["matrix_name"].strip()
            display_hours = m["matrix_hours"]
            display_code = m["matrix_code"]
            source_mode = "matrix_unattached"
        node_id = f"{branch}-s{m['semester']}-m{m['source_line']}"
        node = {
            "id": node_id,
            "role": branch,
            "role_label": label,
            "semester": m["semester"],
            "course": (m["semester"] + 1) // 2,
            "name": display_name,
            "code": display_code,
            "hours": display_hours,
            "fgos_hours": match["fgos_hours"] if match else None,
            "matrix_name": m["matrix_name"],
            "matrix_code": m["matrix_code"],
            "matrix_hours": m["matrix_hours"],
            "up_name": match["name"] if match else None,
            "up_code": match["code"] if match else None,
            "up_hours": match["actual_hours"] if match else None,
            "match_type": match_type,
            "source_mode": source_mode,
            "matrix_source_line": m["source_line"],
            "up_source_line": match["source_line"] if match else None,
            "competencies": m["competencies"],
            "invalid_competencies": m["invalid_competencies"],
            "canonical_key": f"s{m['semester']}::{norm(display_name)}",
            "shared_key": None,
            "physical_exception": is_physical(display_name),
            "zero_hours": display_hours == 0,
        }
        nodes.append(node)
        if not match:
            source_errors.append({
                "rule": "MATRIX_UNATTACHED",
                "severity": "warning",
                "title": "Строка матрицы не прикреплена к дисциплине стыковочного УП",
                "summary": f"{m['matrix_name']} · {m['semester']} семестр",
                "semester": m["semester"],
                "roles": [branch],
                "node_ids": {branch: [node_id]},
                "current": m["matrix_name"],
                "expected": "Выбрать дисциплину из стыковочного УП или зарегистрировать правило разбиения/переименования",
                "source": f"Матрица, компактная строка {m['source_line']}",
                "details": "Визуальный узел временно создан по строке матрицы. Это точечная проблема сопоставления, а не отсутствие дисциплины в УП.",
                "action": "Сопоставить строку с реализацией стыковочного УП.",
                "dynamic": False,
            })
        else:
            if match_type not in {"exact", "component"} and not approved_equivalence(m["matrix_name"], match["name"]):
                source_errors.append({
                    "rule": "SOURCE_NAME_MISMATCH",
                    "severity": "warning",
                    "title": "Название в матрице отличается от стыковочного УП",
                    "summary": f"{display_name} · {m['semester']} семестр",
                    "semester": m["semester"],
                    "roles": [branch],
                    "node_ids": {branch: [node_id]},
                    "current": m["matrix_name"],
                    "expected": match["name"],
                    "source": f"УП: строка {match['source_line']}; матрица: строка {m['source_line']}",
                    "details": "На карте используется название стыковочного УП. Матричное название сохранено для исправления источника.",
                    "action": "Исправить название в матрице либо подтвердить алиас/разбиение.",
                    "dynamic": False,
                })
            if not split and match["actual_hours"] != m["matrix_hours"]:
                source_errors.append({
                    "rule": "SOURCE_HOURS_MISMATCH",
                    "severity": "warning",
                    "title": "Количество часов в матрице отличается от стыковочного УП",
                    "summary": f"{display_name} · {m['semester']} семестр",
                    "semester": m["semester"],
                    "roles": [branch],
                    "node_ids": {branch: [node_id]},
                    "current": f"Матрица: {m['matrix_hours']} ч.",
                    "expected": f"Стыковочный УП: {match['actual_hours']} ч.",
                    "source": f"УП: строка {match['source_line']}; матрица: строка {m['source_line']}",
                    "details": "В карточке используется объём стыковочного УП. Расхождение оставлено как задача РБР.",
                    "action": "Проверить и исправить часы в матрице компетенций.",
                    "dynamic": False,
                })
        if m["invalid_competencies"]:
            source_errors.append({
                "rule": "INVALID_COEFFICIENT",
                "severity": "error",
                "title": "Некорректный коэффициент компетенции",
                "summary": f"{display_name} · {m['semester']} семестр",
                "semester": m["semester"],
                "roles": [branch],
                "node_ids": {branch: [node_id]},
                "current": ", ".join(m["invalid_competencies"]),
                "expected": "Целое значение от 1 до 4",
                "source": f"Матрица, строка {m['source_line']}",
                "details": "Некорректные значения не включены в связи и проверки.",
                "action": "Исправить коэффициент в матрице.",
                "dynamic": False,
            })

    used_up = {u["uid"] for u in up_rows if u["used_by"]}
    for u in up_rows:
        if u["uid"] in used_up or is_event_without_explicit_comp(u["name"]):
            continue
        node_id = f"{branch}-s{u['semester']}-u{u['source_line']}"
        node = {
            "id": node_id,
            "role": branch,
            "role_label": label,
            "semester": u["semester"],
            "course": (u["semester"] + 1) // 2,
            "name": u["name"].rstrip("*").strip(),
            "code": u["code"],
            "hours": u["actual_hours"],
            "fgos_hours": u["fgos_hours"],
            "matrix_name": None,
            "matrix_code": None,
            "matrix_hours": None,
            "up_name": u["name"],
            "up_code": u["code"],
            "up_hours": u["actual_hours"],
            "match_type": "up_without_matrix",
            "source_mode": "up",
            "matrix_source_line": None,
            "up_source_line": u["source_line"],
            "competencies": {},
            "invalid_competencies": [],
            "canonical_key": f"s{u['semester']}::{norm(u['name'])}",
            "shared_key": None,
            "physical_exception": is_physical(u["name"]),
            "zero_hours": u["actual_hours"] == 0,
        }
        nodes.append(node)
        source_errors.append({
            "rule": "UP_WITHOUT_MATRIX_COMPETENCIES",
            "severity": "warning",
            "title": "Для дисциплины стыковочного УП не найдена строка матрицы компетенций",
            "summary": f"{node['name']} · {u['semester']} семестр",
            "semester": u["semester"],
            "roles": [branch],
            "node_ids": {branch: [node_id]},
            "current": "Компетенции не назначены",
            "expected": "Привязать строку матрицы или подтвердить отсутствие компетенций",
            "source": f"Стыковочный УП, строка {u['source_line']}",
            "details": "Узел создан по стыковочному УП и отображается на карте. Это точечная задача наполнения матрицы.",
            "action": "Добавить компетенции или зарегистрировать исключение.",
            "dynamic": False,
        })

    for u in up_rows:
        if len(u["used_by"]) > 1 and not is_composite(u["name"]):
            mapped = [nodes[i - 1] for i in u["used_by"] if 0 < i <= len(nodes)]
            source_errors.append({
                "rule": "DUPLICATE_MAPPING",
                "severity": "warning",
                "title": "Несколько строк матрицы претендуют на одну дисциплину УП",
                "summary": f"{u['name']} · {u['semester']} семестр",
                "semester": u["semester"],
                "roles": [branch],
                "node_ids": {branch: [n["id"] for n in mapped]},
                "current": ", ".join(n["matrix_name"] or n["name"] for n in mapped),
                "expected": "Подтвердить объединение или выбрать одну корректную строку",
                "source": f"Стыковочный УП, строка {u['source_line']}",
                "details": "Автоматическое объединение не выполнялось.",
                "action": "Проверить дублирование строк матрицы.",
                "dynamic": False,
            })

    nodes.sort(key=lambda n: (n["semester"], n["up_source_line"] or 10_000, n["matrix_source_line"] or 10_000, n["name"]))
    return {"id": branch, "label": label, "nodes": nodes}, source_errors


def family_key(node: dict[str, Any]) -> str:
    n = norm(node["name"])
    if "иностранный язык" in n:
        return "foreign-language"
    if is_physical(node["name"]):
        return "physical-culture"
    if "компьютерные сети" in n:
        return "computer-networks"
    if "devsecops" in n or "безопасность разработки и администрирования" in n:
        return "devsecops"
    if "использование ии в информационной безопасности" in n:
        return "ai-security"
    if "защита конфиденциальной информации" in n:
        return "confidential-information"
    if "документационное обеспечение профессиональной деятельности" in n:
        return "documentation"
    if "linux" in n and "администрирование" not in n:
        return "linux-course"
    if "windows server" in n:
        return "windows-server"
    n = re.sub(r"\b(базовый|продвинутый|уровень|часть|ii|i)\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def continuation_links(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for n in nodes:
        key = family_key(n)
        if key:
            groups[key].append(n)
    links: list[dict[str, Any]] = []
    for key, group in groups.items():
        group = sorted(group, key=lambda n: (n["semester"], n["name"]))
        sems = sorted(set(n["semester"] for n in group))
        if len(sems) < 2:
            continue
        for left_sem, right_sem in zip(sems, sems[1:]):
            left = [n for n in group if n["semester"] == left_sem]
            right = [n for n in group if n["semester"] == right_sem]
            for a in left:
                scored = sorted(((difflib.SequenceMatcher(None, norm(a["name"]), norm(b["name"])).ratio(), b) for b in right), reverse=True, key=lambda x: x[0])
                if scored:
                    links.append({"from": a["id"], "to": scored[0][1]["id"], "family": key, "type": "continuation"})
    unique = {(x["from"], x["to"]): x for x in links}
    return list(unique.values())


def dynamic_errors_for_roles(roles: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for role, payload in roles.items():
        nodes = payload["nodes"]
        for node in nodes:
            hard_count = sum(1 for idx in range(13) if str(idx) in node["competencies"])
            if node["hours"] > 0 and not node["physical_exception"] and hard_count == 0:
                errors.append({
                    "rule": "HARD_MISSING",
                    "severity": "error",
                    "title": "В дисциплине отсутствует hard-компетенция",
                    "summary": f"{node['name']} · {node['semester']} семестр",
                    "semester": node["semester"],
                    "roles": [role],
                    "node_ids": {role: [node["id"]]},
                    "current": "0 внутренних hard-компетенций",
                    "expected": "Не менее 1 внутренней hard-компетенции",
                    "source": "Правило методической проверки HARD-01",
                    "details": "Исключения: дисциплины с 0 часов и физическая культура.",
                    "action": "Назначить hard-компетенцию или оформить подтверждённое исключение.",
                    "dynamic": True,
                })
        for sem in range(1, 7):
            sem_nodes = [n for n in nodes if n["semester"] == sem and n["hours"] > 0]
            for idx in range(13, 18):
                assessed = [n for n in sem_nodes if str(idx) in n["competencies"]]
                if len(assessed) < 3:
                    errors.append({
                        "rule": "SOFT_DEFICIT",
                        "severity": "error",
                        "title": "Недостаточно мест оценивания Soft Skill",
                        "summary": f"{CATALOG[idx]['name']} · {sem} семестр · {len(assessed)}/3",
                        "semester": sem,
                        "roles": [role],
                        "node_ids": {role: []},
                        "existing_node_ids": {role: [n["id"] for n in assessed]},
                        "candidate_node_ids": {role: [n["id"] for n in sem_nodes if str(idx) not in n["competencies"]]},
                        "comp_idx": idx,
                        "current": f"{len(assessed)} дисциплины из 3",
                        "expected": "Не менее 3 дисциплин в семестре",
                        "source": "Правило методической проверки SOFT-01",
                        "details": "Soft Skill показывает места оценивания, а не наследуемую траекторию. Для 4 курса (7–8 семестры) правило не применяется.",
                        "action": f"Рассмотреть добавление места оценивания ещё минимум в {3-len(assessed)} дисциплинах.",
                        "dynamic": True,
                    })
    return errors


def merge_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[Any, ...], dict[str, Any]] = {}
    for e in errors:
        node_name = norm(e.get("summary", "").split(" · ")[0])
        key = (e["rule"], e.get("semester"), e.get("comp_idx"), node_name, e.get("current"), e.get("expected"))
        if key not in merged:
            merged[key] = json.loads(json.dumps(e, ensure_ascii=False))
        else:
            target = merged[key]
            for role in e.get("roles", []):
                if role not in target["roles"]:
                    target["roles"].append(role)
            for field in ["node_ids", "existing_node_ids", "candidate_node_ids"]:
                if field in e:
                    target.setdefault(field, {})
                    for role, ids in e[field].items():
                        target[field].setdefault(role, [])
                        for item in ids:
                            if item not in target[field][role]:
                                target[field][role].append(item)
    severity_order = {"error": 0, "warning": 1, "info": 2}
    result = list(merged.values())
    result.sort(key=lambda e: (severity_order.get(e["severity"], 9), e.get("semester") or 99, e["rule"], e["summary"]))
    for i, e in enumerate(result, start=1):
        e["id"] = f"ERR-{i:03d}"
    return result


def assign_shared_keys(roles: dict[str, dict[str, Any]]) -> None:
    indexes: dict[str, dict[tuple[Any, ...], list[dict[str, Any]]]] = {}
    for role, payload in roles.items():
        idx: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
        for n in payload["nodes"]:
            sig = (n["semester"], norm(n["name"]), n["hours"], json.dumps(n["competencies"], sort_keys=True, ensure_ascii=False))
            idx[sig].append(n)
        indexes[role] = idx
    for sig, left in indexes["kiber"].items():
        right = indexes["devops"].get(sig, [])
        if len(left) == 1 and len(right) == 1:
            key = "shared::" + hashlib.sha1(repr(sig).encode("utf-8")).hexdigest()[:12]
            left[0]["shared_key"] = key
            right[0]["shared_key"] = key


def source_summary(roles: dict[str, dict[str, Any]], errors: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "roles": {role: {"nodes": len(p["nodes"]), "semesters": sorted(set(n["semester"] for n in p["nodes"]))} for role, p in roles.items()},
        "errors": {
            "total": len(errors),
            "blocking": sum(1 for e in errors if e["severity"] == "error"),
            "warnings": sum(1 for e in errors if e["severity"] == "warning"),
            "by_rule": {rule: sum(1 for e in errors if e["rule"] == rule) for rule in sorted(set(e["rule"] for e in errors))},
        },
    }


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    kiber, kiber_errors = build_branch("kiber", "Кибер")
    devops, devops_errors = build_branch("devops", "DevOps")
    roles = {"kiber": kiber, "devops": devops}
    assign_shared_keys(roles)
    for payload in roles.values():
        payload["continuations"] = continuation_links(payload["nodes"])

    rules = {
        "version": VERSION,
        "year": YEAR,
        "source_priority": [
            "Стыковочный УП — узлы, названия, семестры, часы и внутренняя структура реализации",
            "Матрица компетенций — компетенции, коэффициенты и места оценивания Soft Skills",
            "ФГОС-контур — официальная основа и подтверждение продолжения дисциплин между семестрами",
        ],
        "coefficients": {"min": 1, "max": 4, "meaning": "Глубина проработки компетенции в конкретной реализации дисциплины"},
        "hard": {"required": 1, "indices": list(range(13)), "exceptions": ["0 часов", "физическая культура"]},
        "soft": {"indices": list(range(13, 18)), "minimum_disciplines_per_semester": 3, "checked_semesters": list(range(1, 7)), "line_semantics": "места оценивания, не наследование"},
        "codes": "Информационный атрибут; не создаёт обязательную связь автоматически на текущей итерации",
        "display": "Все назначенные компетенции постоянно видны на карточках; линии включаются группами или по отдельности",
    }

    source_errors = kiber_errors + devops_errors
    dynamic_errors = dynamic_errors_for_roles(roles)
    errors = merge_errors(source_errors + dynamic_errors)
    data = {
        "meta": {
            "title": "Траектория обучения · Информационная безопасность",
            "specialty_code": "10.02.05",
            "specialty": "Обеспечение информационной безопасности автоматизированных систем",
            "direction": "Информационная безопасность",
            "year": YEAR,
            "version": VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "semesters": 8,
            "roles_order": ["kiber", "devops"],
        },
        "catalog": CATALOG,
        "groups": GROUPS,
        "roles": roles,
        "source_errors": [e for e in errors if not e.get("dynamic")],
        "initial_errors": errors,
        "rules": rules,
        "summary": source_summary(roles, errors),
    }

    template = TEMPLATE.read_text(encoding="utf-8")
    embedded = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = template.replace("__TRAJECTORY_DATA_JSON__", embedded)
    if "__TRAJECTORY_DATA_JSON__" in html:
        raise RuntimeError("Data placeholder was not replaced")
    (OUT / "START.html").write_text(html, encoding="utf-8")
    write_json(OUT / "НОРМАЛИЗОВАННЫЕ_ДАННЫЕ.json", data)
    write_json(OUT / "ПРИМЕНЁННЫЕ_ПРАВИЛА.json", rules)
    write_json(OUT / "РЕЕСТР_ОШИБОК.json", errors)
    write_json(OUT / "РЕЕСТР_ИСПРАВЛЕНИЙ.json", [])
    profile = {
        "specialty_code": data["meta"]["specialty_code"],
        "specialty": data["meta"]["specialty"],
        "direction": data["meta"]["direction"],
        "business_roles": [{"id": "kiber", "label": "Кибер"}, {"id": "devops", "label": "DevOps"}],
        "academic_year": YEAR,
        "semesters": 8,
        "competency_groups": {k: v["indices"] for k, v in GROUPS.items()},
    }
    write_json(OUT / "ПРОФИЛЬ_ПРОГРАММЫ.json", profile)

    readme = f"""# Визуализация траектории ИБ · {YEAR} · {VERSION}

## Запуск

1. Полностью распакуйте архив.
2. Откройте `START.html` двойным щелчком в Chrome, Edge, Firefox или Safari.
3. Интернет, сервер и дополнительные файлы для запуска не требуются: данные встроены в HTML.

## Реализовано

- переключение БР «Кибер» / DevOps;
- 8 семестров слева направо;
- карточки по стыковочному УП;
- постоянные метки всех компетенций;
- групповые и индивидуальные переключатели внутренних hard, ОК, ПК и Soft Skills;
- Soft Skills отображаются пунктирными линиями мест оценивания;
- цветные линии каждой общей компетенции при выборе дисциплины;
- прямые связи продолжения дисциплин;
- кликабельный реестр ошибок с переходом к точке на карте;
- развернутая диагностика, локальное редактирование и экспорт изменений.

## Источники

Стыковочный УП формирует карту. Матрица задаёт компетенции. ФГОС-контур используется для официальной основы и связей продолжения. Расхождения не исправляются молча и доступны в реестре ошибок.

## Ограничение

Изменения сохраняются только в открытой странице. Для передачи результата используйте кнопку «Экспорт изменений».
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")

    audit = f"""# Аудит источников · ИБ {YEAR} · {VERSION}

## Контур

- Карточки создаются на основании стыковочных УП «Кибер» и DevOps за 2026–2027.
- Компетенции и коэффициенты присоединяются из соответствующих матриц.
- Код не используется как безусловный глобальный идентификатор.
- Составные строки УП могут быть разложены на внутренние реализации только при явном совпадении компонента или зарегистрированном правиле.

## Объём

- Кибер: {len(roles['kiber']['nodes'])} узлов.
- DevOps: {len(roles['devops']['nodes'])} узлов.
- Компетенции: {len(CATALOG)} (13 внутренних hard, 5 Soft Skills, 9 ОК, 16 ПК).
- Реестр: {len(errors)} уникальных записей после дедупликации общих частей.

## Важные диагностические принципы

Фраза «Не найдено однозначное соответствие в стыковочном УП» как массовое предупреждение удалена. Вместо неё используются точные типы: строка матрицы без привязки, дисциплина УП без матрицы, конфликт названия/часов, дублирующее сопоставление.

Для ДУП.02 первого семестра на карте используется название стыковочного УП «Введение в программирование»; матричное «Введение в операционные системы» сохранено как диагностическое расхождение.
"""
    (OUT / "АУДИТ_ИСТОЧНИКОВ.md").write_text(audit, encoding="utf-8")

    questions = """# Открытые вопросы для стандартного конвейера

1. Окончательное правило идентификации дисциплины с учётом кода, названия, семестра и ручного словаря.
2. Могут ли ПК ФГОС выполнять правило «хотя бы один hard», или проверка всегда строится только по 13 внутренним hard.
3. Учитывается ли физическая культура при подсчёте трёх мест оценивания Soft Skill. В текущей версии учитывается, если софт явно назначен и часы положительные.
4. Область редактирования по умолчанию: одна реализация, общая реализация обеих БР или все реализации канонической дисциплины.
5. Полные официальные названия бизнес-ролей «Кибер» и DevOps.
6. Целевой источник истины после утверждения изменений: Excel или нормализованная база с экспортом в Excel.
7. Формальные правила включения практик, Student Camp, ГИА и проектных узлов при наличии компетенций.
8. Процесс создания версии 2027–2028 на основе утверждённой 2026–2027.
"""
    (OUT / "ОТКРЫТЫЕ_ВОПРОСЫ.md").write_text(questions, encoding="utf-8")

    # Static integrity checks.
    checks: list[str] = []
    start = OUT / "START.html"
    if not start.exists() or start.stat().st_size == 0:
        raise RuntimeError("START.html missing or empty")
    checks.append(f"PASS: START.html exists, {start.stat().st_size} bytes")
    text = start.read_text(encoding="utf-8")
    required_markers = ["window.__TRAJECTORY_DATA__", "data-runtime-ready", "SOFT_DEFICIT", "show-group", "error-card"]
    for marker in required_markers:
        if marker not in text:
            raise RuntimeError(f"Required marker missing: {marker}")
        checks.append(f"PASS: marker {marker}")
    forbidden = ["<script src=", "fetch(", "http://", "https://"]
    for marker in forbidden:
        if marker in text:
            raise RuntimeError(f"External dependency marker found: {marker}")
        checks.append(f"PASS: no {marker}")
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", text, flags=re.S | re.I)
    js_check = ROOT / "build" / "_inline_check.js"
    js_check.write_text("\n".join(scripts), encoding="utf-8")
    subprocess.run(["node", "--check", str(js_check)], check=True)
    checks.append("PASS: inline JavaScript passed node --check")
    for path in OUT.glob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))
    checks.append("PASS: all JSON files parsed")

    manifest_files = []
    for path in sorted(OUT.iterdir(), key=lambda p: p.name):
        if path.is_file():
            manifest_files.append({"name": path.name, "size": path.stat().st_size, "sha256": sha256(path)})
    manifest = {
        "package": f"ВИЗУАЛИЗАЦИЯ_ИБ_Кибер_DevOps_2026-2027_{VERSION}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "start_file": "START.html",
        "autonomous_start": True,
        "files": manifest_files,
    }
    write_json(OUT / "PACKAGE_MANIFEST.json", manifest)

    test_zip = ROOT / "build" / "_integrity_test.zip"
    with zipfile.ZipFile(test_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in OUT.iterdir():
            if path.is_file():
                zf.write(path, path.name)
    with zipfile.ZipFile(test_zip) as zf:
        if zf.testzip() is not None:
            raise RuntimeError("ZIP integrity test failed")
        names = zf.namelist()
        if "START.html" not in names or any(name.startswith("/") or ".." in Path(name).parts for name in names):
            raise RuntimeError("ZIP root/path validation failed")
    checks.append(f"PASS: local ZIP integrity check, {test_zip.stat().st_size} bytes, START.html at root")
    test_zip.unlink()

    protocol = "ПРОТОКОЛ ПРОВЕРКИ ПАКЕТА\n" + "=" * 32 + "\n" + "\n".join(checks) + "\n"
    (OUT / "ПРОТОКОЛ_ПРОВЕРКИ.txt").write_text(protocol, encoding="utf-8")
    print(json.dumps({"status": "ok", "output": str(OUT), "files": sorted(p.name for p in OUT.iterdir()), "checks": checks}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
