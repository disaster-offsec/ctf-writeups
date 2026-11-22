#!/usr/bin/env python3
"""Проставить шапку райтапа легаси-README, у которых её нет.

Зачем: README, написанные до внедрения шаблона (hackthebox, bootcamp,
portswigger, solarctf, kubok...), начинаются сразу с «# Заголовок» —
без таблицы «Платформа / Категория / Статус / Дата». Из-за этого:
  - папки выглядят по-разному (где-то шапка, где-то нет);
  - tools/typ2readme.py --mark-done не находит строку «Статус».

Что делает скрипт для каждого README без строки «Статус»:
  - если в файле уже есть таблица с «Платформа / Событие» — вставляет
    в неё одну строку «| **Статус** | X |» (после «Сложность»);
  - иначе — добавляет полную шапку-таблицу сразу после первого
    заголовка «# ...» (или в начало файла, если заголовка нет).
    Событие берётся из имени корневой папки (generate_index.event_title),
    категория — из второй папки пути, если глубина >= 3.

README со строкой «Статус» не трогаются. Дашборды (INDEX:START) и
tools/templates пропускаются. Только стандартная библиотека.

Примеры:
  python3 tools/ensure_header.py --list
  python3 tools/ensure_header.py                      # статус draft
  python3 tools/ensure_header.py "portswigger/**" --status done
  python3 tools/ensure_header.py "hackthebox/*" --status done --date "2026-11-20"
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXCLUDE = {"tools", "templates", ".git", ".github", "node_modules"}
INDEX_MARK = "<!-- INDEX:START -->"

STATUS_CELL = re.compile(r"^\s*\|\s*\**\s*Статус\s*\**\s*\|", re.M)
EVENT_CELL = re.compile(r"^\s*\|\s*\**\s*Платформа / Событие\s*\**\s*\|", re.M)
DIFF_CELL = re.compile(r"^(\|\s*\**\s*Сложность\s*\**\s*\|[^\n]*$)", re.M)
CAT_CELL = re.compile(r"^(\|\s*\**\s*Категория\s*\**\s*\|[^\n]*$)", re.M)
H1_RE = re.compile(r"^# [^\n]+$", re.M)


def event_title(name: str) -> str:
    """Имя корневой папки -> красивое название события."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from generate_index import event_title as gt
        return gt(name)
    except Exception:
        m = re.match(r"^(.*?)-(\d{4})$", name)
        base, year = (m.group(1), m.group(2)) if m else (name, "")
        title = " ".join("CTF" if w.lower() == "ctf" else w.capitalize()
                         for w in base.split("-"))
        return f"{title} {year}".strip()


def header_table(rel: Path, status: str, date: str) -> str:
    parts = rel.parts[:-1]  # без README.md
    event = event_title(parts[0]) if parts else "—"
    # категория — вторая папка, только если таск глубже (portswigger/sqli/lab),
    # у двухуровневых путей (hackthebox/meow) второй папки-категории нет
    category = parts[1] if len(parts) >= 3 else "—"
    return (
        "| | |\n"
        "|---|---|\n"
        f"| **Платформа / Событие** | {event} |\n"
        f"| **Категория** | {category} |\n"
        f"| **Сложность** | — |\n"
        f"| **Статус** | {status} |\n"
        f"| **Дата решения** | {date} |\n"
        "| **Ссылка на таск** | — |\n"
    )


def patch(text: str, rel: Path, status: str, date: str) -> str:
    """Новый текст README: либо +строка статуса, либо +полная шапка."""
    if EVENT_CELL.search(text):
        m = DIFF_CELL.search(text) or CAT_CELL.search(text)
        if m:  # вставить после Сложности/Категории
            return text[:m.end()] + f"\n| **Статус** | {status} |" + text[m.end():]
        m = re.search(r"^\|[-: |]+\|[^\n]*\n", text, re.M)  # после |---| строки
        if m:
            return text[:m.end()] + f"| **Статус** | {status} |\n" + text[m.end():]
        return f"| **Статус** | {status} |\n\n" + text
    table = header_table(rel, status, date)
    m = H1_RE.search(text)
    if m:  # шапка после первого «# Заголовок»
        return text[:m.end()] + "\n\n" + table + "\n" + text[m.end():].lstrip("\n")
    return table + "\n" + text


def find_readmes(pattern: str | None) -> list[Path]:
    out = []
    for rp in sorted(ROOT.rglob("README.md")):
        rel = rp.relative_to(ROOT)
        if len(rel.parts) == 1:
            continue  # корневой дашборд
        if any(p in EXCLUDE or p.startswith(".") for p in rel.parts):
            continue
        try:
            text = rp.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if INDEX_MARK in text:
            continue  # папка-индекс/классовый README
        if pattern and not fnmatch.fnmatch(rel.as_posix(), pattern):
            continue
        out.append(rp)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Добавить шапку со статусом в README без неё")
    ap.add_argument("pattern", nargs="?", default=None,
                    help="маска пути README, напр. \"portswigger/**\"")
    ap.add_argument("--status", default="draft", choices=["draft", "done"],
                    help="что писать в «Статус» (по умолчанию draft)")
    ap.add_argument("--date", default="—", help="значение «Дата решения»")
    ap.add_argument("--list", action="store_true",
                    help="показать, что будет изменено, без записи")
    ap.add_argument("--dry-run", action="store_true", help="не писать файлы")
    args = ap.parse_args()

    files = find_readmes(args.pattern)
    n_new = n_cell = n_skip = 0
    for rp in files:
        rel = rp.relative_to(ROOT).as_posix()
        text = rp.read_text(encoding="utf-8", errors="replace")
        if STATUS_CELL.search(text):
            n_skip += 1
            continue
        if EVENT_CELL.search(text):
            n_cell += 1
            act = f"добавлю строку Статус | {args.status}"
        else:
            n_new += 1
            act = f"добавлю шапку (Статус | {args.status})"
        print(f"  [{act}] {rel}")
        if not (args.list or args.dry_run):
            rp.write_text(patch(text, rp.relative_to(ROOT), args.status,
                                args.date), encoding="utf-8", newline="\n")
    if not (args.list or args.dry_run):
        pass
    word = "внесу изменения" if (args.list or args.dry_run) else "изменено"
    print(f"\n{word}: шапок {n_new}, строк статуса {n_cell}, "
          f"уже есть статус: {n_skip}")
    if not (args.list or args.dry_run):
        print("Дальше: python tools/generate_index.py — пересчитает дашборд.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
