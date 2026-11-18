#!/usr/bin/env python3
"""Генератор индексных таблиц для ctf-writeups.

Запуск из корня репозитория:  python3 tools/generate_index.py

Что делает:
  1. Корневой README.md: заполняет секцию между маркерами
     <!-- INDEX:START --> ... <!-- INDEX:END -->
     (если маркеров нет — добавляет секцию в конец файла).
  2. Для каждой папки класса PortSwigger добавляет/обновляет секцию "## Labs"
     с таблицей лаб внутри классового README.md.

Райтап = папка, внутри которой лежит README.md.
Только стандартная библиотека, git используется для дат коммитов (опционально).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXCLUDE_TOP = {"tools", "templates", ".git", ".github"}
PORTSWIGGER = "portswigger"

MARK_START = "<!-- INDEX:START -->"
MARK_END = "<!-- INDEX:END -->"


def last_commit(path: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%as", "--", str(path)],
            cwd=ROOT, capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() or "-"
    except Exception:
        return "-"


def readme_title(folder: Path) -> str:
    try:
        for line in (folder / "README.md").read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("# "):
                return s[2:].strip()
    except Exception:
        pass
    return folder.name


def count_files(folder: Path) -> int:
    return sum(1 for p in folder.rglob("*") if p.is_file())


def top_dirs() -> list[Path]:
    return sorted(
        d for d in ROOT.iterdir()
        if d.is_dir() and not d.name.startswith(".") and d.name not in EXCLUDE_TOP
    )


def sub_writeups(parent: Path) -> list[Path]:
    """Райтапы вглубь до 2 уровней: parent/lab или parent/category/lab."""
    found = []
    for d in sorted(parent.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        if (d / "README.md").exists():
            found.append(d)
            continue
        for g in sorted(d.iterdir()):
            if g.is_dir() and not g.name.startswith(".") and (g / "README.md").exists():
                found.append(g)
    return found


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def table(rows: list[list[str]]) -> str:
    if not rows:
        return "_Пока пусто._\n"
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    def fmt(r): return "| " + " | ".join(c.ljust(w) for c, w in zip(r, widths)) + " |"
    sep = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
    return "\n".join([fmt(rows[0]), sep] + [fmt(r) for r in rows[1:]]) + "\n"


def section_for(top: Path) -> str:
    """Готовит markdown-секцию для одной папки верхнего уровня."""
    name = top.name
    classes = [d for d in top.iterdir() if d.is_dir() and not d.name.startswith(".")]
    if name == PORTSWIGGER:
        rows = [["Class", "Labs", "Last commit", "Path"]]
        for c in sorted(classes):
            labs = sub_writeups(c)
            rows.append([
                c.name, str(len(labs)) if labs else "-",
                last_commit(labs[-1]) if labs else "-", rel(c),
            ])
        return f"### {name}\n\n" + table(rows)

    single = (top / "README.md").exists()
    if single:
        rows = [["Writeup", "Files", "Last commit", "Path"]]
        rows.append([readme_title(top), str(count_files(top)), last_commit(top), rel(top)])
        return f"### {name}\n\n" + table(rows)

    rows = [["Writeup", "Files", "Last commit", "Path"]]
    for w in sub_writeups(top):
        rows.append([readme_title(w), str(count_files(w)), last_commit(w), rel(w)])
    return f"### {name}\n\n" + table(rows)


def build_index() -> str:
    known_events, known_other = [], []
    for d in top_dirs():
        if d.name == PORTSWIGGER:
            continue
        if any(tag in d.name for tag in ("ctf", "CTF")) and d.name.lower().startswith(
            ("avito", "kubok", "solar", "pico")
        ):
            known_events.append(d)
        else:
            known_other.append(d)

    parts = []
    pw = ROOT / PORTSWIGGER
    if pw.exists():
        parts.append("## PortSwigger Academy\n\n" + section_for(pw))
    if known_events:
        parts.append("## CTF events\n\n" + "\n".join(section_for(d) for d in known_events))
    if known_other:
        parts.append("## Platforms & trainings\n\n" + "\n".join(section_for(d) for d in known_other))
    return "\n".join(parts)


def update_root_readme() -> bool:
    readme = ROOT / "README.md"
    if not readme.exists():
        print("README.md не найден в корне — некуда вставлять индекс.")
        return False
    text = readme.read_text(encoding="utf-8")
    index_block = f"{MARK_START}\n{build_index()}\n{MARK_END}"
    if MARK_START in text and MARK_END in text:
        pre = text.split(MARK_START)[0]
        post = text.split(MARK_END)[1]
        text = pre + index_block + post
    elif MARK_START in text:
        text = text.split(MARK_START)[0] + index_block + "\n"
    else:
        text = text.rstrip() + "\n\n---\n\n" + index_block + "\n"
    readme.write_text(text, encoding="utf-8")
    return True


def update_class_readme(cls: Path, labs: list[Path]) -> None:
    rows = [["#", "Lab", "Last commit", "Path"]]
    for lab in labs:
        num = lab.name.split("-")[0]
        rows.append([num, readme_title(lab), last_commit(lab), rel(lab)])
    block = "## Labs\n\n" + table(rows)

    readme = cls / "README.md"
    text = readme.read_text(encoding="utf-8") if readme.exists() else ""
    if MARK_START in text and MARK_END in text:
        pre = text.split(MARK_START)[0]
        post = text.split(MARK_END)[1]
        text = pre + f"{MARK_START}\n{block}\n{MARK_END}" + post
    elif "\n## Labs\n" in text or text.startswith("## Labs\n"):
        # заменяем существующую секцию Labs (до следующего "## " или конца файла)
        lines = text.splitlines()
        out, in_labs, done = [], False, False
        for line in lines:
            if not done and line.strip() == "## Labs":
                in_labs, done = True, True
                out.append(block)
                continue
            if in_labs and line.startswith("## "):
                in_labs = False
            if not in_labs:
                out.append(line)
        text = "\n".join(out).rstrip() + "\n"
    else:
        text = text.rstrip() + "\n\n---\n\n" + block
    readme.write_text(text, encoding="utf-8")


def main() -> int:
    if not (ROOT / ".git").exists():
        print("Запусти скрипт из корня репозитория (не найден .git).")
        return 1
    ok = update_root_readme()
    pw = ROOT / PORTSWIGGER
    n_classes = 0
    if pw.exists():
        for cls in sorted(pw.iterdir()):
            if not cls.is_dir() or cls.name.startswith("."):
                continue
            labs = sub_writeups(cls)
            if labs and (cls / "README.md").exists():
                update_class_readme(cls, labs)
                n_classes += 1
    print(f"Корневой README: {'обновлён' if ok else 'ошибка'}")
    print(f"Классовых README обновлено: {n_classes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
