#!/usr/bin/env python3
"""Проверка заголовков райтапов: ищет безликие имена и незаполненные заглушки.

Запуск из корня репозитория:  python3 tools/check_titles.py

Что считает проблемой:
  A. Папка с файлами, но без README.md
  B. В README.md нет заголовка "# ..."
  C. Безликий заголовок в README:  lab1, Lab 2, задача 3 ...
  D. Безликое имя папки:           lab1, task-2, writeup_3 ...
  E. Заглушка: в README есть маркер черновика (draft / черновик / TODO / TBD)
  F. Код-блок без языка подсветки: открывающая ограда ``` без ```python/bash/...

Печатает готовый todo-лист. Порядок чинить: C/D (сразу видно в индексе на
главной) -> A/B -> E (заглушки, план "по одному в день").
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXCLUDE_TOP = {"tools", "templates", ".git", ".github"}
DEPTH = 4

MARK_START = "<!-- INDEX:START -->"
MARK_END = "<!-- INDEX:END -->"

GENERIC_TITLE = re.compile(
    r"^(?:lab|task|задача|writeup|райтап)[\s_\-]*(?:\d+)?$", re.I)
GENERIC_DIR = re.compile(r"^(?:lab|task|writeup)[\-_]?\d+$", re.I)
DRAFT_MARK = re.compile(r"\b(?:draft|черновик|черновая|в работе|todo|tbd)\b", re.I)


def strip_index(text: str) -> str:
    """Вырезать автосекции между маркерами INDEX: там живут таблицы со
    словами draft/— — это статусы райтапов, а не черновые пометки."""
    while MARK_START in text and MARK_END in text:
        pre, rest = text.split(MARK_START, 1)
        text = pre + rest.split(MARK_END, 1)[1]
    return text


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def readme_heading(folder: Path) -> str:
    try:
        for line in (folder / "README.md").read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("# "):
                return s[2:].strip()
    except Exception:
        pass
    return ""


def unlanged_blocks(folder: Path) -> list[int]:
    """Номера строк открытых оград ``` без языка подсветки.

    Закрывающие ограды пусты по определению: считаем только те,
    которые открывают блок (чётное чередование).
    """
    try:
        text = strip_index((folder / "README.md").read_text(encoding="utf-8"))
    except Exception:
        return []
    out, inb = [], False
    for i, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s.startswith("```"):
            continue
        if not inb:
            if s == "```":
                out.append(i)  # открытие без языка
            inb = True
        else:
            inb = False
    return out


def is_draft(folder: Path) -> bool:
    try:
        text = (folder / "README.md").read_text(encoding="utf-8")
    except Exception:
        return False
    return bool(DRAFT_MARK.search(strip_index(text)))


def check_dir(d: Path, problems: dict[str, list[str]]) -> None:
    title = readme_heading(d)
    if not title:
        problems["B. в README нет заголовка «# ...»"].append(rel(d))
    elif GENERIC_TITLE.match(title):
        problems["C. безликий заголовок"].append(f"{rel(d)} — «{title}»")
    if GENERIC_DIR.match(d.name):
        problems["D. безликое имя папки"].append(rel(d))
    if is_draft(d):
        problems["E. заглушка (черновик)"].append(rel(d))
    lines = unlanged_blocks(d)
    if lines:
        problems["F. код-блок без языка"].append(
            f"{rel(d)} — строки {', '.join(map(str, lines[:8]))}"
            + ("..." if len(lines) > 8 else ""))


def visit(d: Path, problems: dict[str, list[str]], depth: int = DEPTH) -> None:
    """Обход как в generate_index.walk_tasks: папка с README = райтап.

    Папка-контейнер (README с маркерами INDEX — автосгенерированный индекс
    события/класса) райтапом не считается: её дети без README — это
    дорешка, а не ассеты."""
    if depth < 0:
        return
    has_readme = (d / "README.md").exists()
    is_container = False
    if has_readme:
        try:
            is_container = MARK_START in (d / "README.md").read_text(encoding="utf-8")
        except Exception:
            pass
        check_dir(d, problems)
    elif any(p.is_file() for p in d.iterdir()):
        problems["A. файлы есть, README.md нет"].append(rel(d))
        return
    # внутри райтапа пропускаем папки-ассеты (fig/, img/); в контейнерах и
    # структурных папках идём глубже — там могут быть задачи без README
    for sub in sorted(d.iterdir()):
        if not sub.is_dir() or sub.name.startswith("."):
            continue
        if (has_readme and not is_container
                and not (sub / "README.md").exists()
                and any(p.is_file() for p in sub.iterdir())):
            continue  # ассеты
        visit(sub, problems, depth - 1)


def main() -> int:
    if not (ROOT / ".git").exists():
        print("Запусти скрипт из корня репозитория (не найден .git).")
        return 1
    problems: dict[str, list[str]] = defaultdict(list)
    for top in sorted(ROOT.iterdir()):
        if not top.is_dir() or top.name.startswith(".") or top.name in EXCLUDE_TOP:
            continue
        visit(top, problems)
    for group in sorted(problems):
        items = problems[group]
        print(f"\n{group} — {len(items)}:")
        for item in items:
            print(f"  - {item}")
    total = sum(len(v) for v in problems.values())
    print(f"\nИтого замечаний: {total}")
    if total == 0:
        print("Все заголовки осмысленные, заглушек нет. Огонь.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
