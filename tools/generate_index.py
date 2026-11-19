#!/usr/bin/env python3
"""Генератор индексных таблиц для ctf-writeups.

Запуск из корня репозитория:  python3 tools/generate_index.py

Что делает:
  1. Корневой README.md: заполняет секцию между маркерами
     <!-- INDEX:START --> ... <!-- INDEX:END -->
     (если маркеров нет — добавляет секцию в конец файла).
     Все названия в таблицах — кликабельные ссылки на папку райтапа.
  2. Для каждой папки класса PortSwigger добавляет/обновляет секцию "## Labs"
     с таблицей лаб внутри классового README.md. Если README нет — создаёт
     заготовку конспекта класса.
  3. Чинит ссылки во всех README репозитория: GitHub blob/tree-URL и корневые
     абсолютные пути переписывает в относительные (как папки лежат на диске).

Райтап = папка, внутри которой лежит README.md.
Только стандартная библиотека, git используется для дат коммитов (опционально).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

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


def sub_writeups(parent: Path, depth: int = 3) -> list[Path]:
    """Райтапы вглубь до 3 уровней:
    parent/lab, parent/category/lab, parent/category/level/lab."""
    found = []
    for d in sorted(parent.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        if (d / "README.md").exists():
            found.append(d)
        elif depth > 1:
            found.extend(sub_writeups(d, depth - 1))
    return found


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def md_url(path: str) -> str:
    """URL для ссылки: экранируем то, что ломает markdown-ссылку."""
    return path.replace(" ", "%20").replace("(", "%28").replace(")", "%29")


def md_link(text: str, path: str) -> str:
    """Кликабельная ячейка таблицы: [текст](папка/)."""
    text = (text.replace("\\", "\\\\")
                .replace("[", "\\[")
                .replace("]", "\\]")
                .replace("|", "\\|"))
    return f"[{text}]({md_url(path)})"


def section_header(name: str) -> str:
    return f"### [{name}]({md_url(name)}/)"


# --- починка ссылок: blob/tree-URL и корневые пути -> относительные ---

TARGET_RE = re.compile(r"\]\(([^)\s]+)\)")
GH_LINK = re.compile(
    r"^https?://github\.com/([^/]+)/([^/]+)/(?:blob|tree)/[^/]+/(.+)$", re.I
)

_origin_cache: str | None = None
_origin_done = False


def origin_slug() -> str | None:
    """owner/repo из git remote origin — чтобы не трогать ссылки на чужие репо."""
    global _origin_cache, _origin_done
    if not _origin_done:
        _origin_done = True
        try:
            out = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=ROOT, capture_output=True, text=True, timeout=10,
            )
            m = re.search(r"[:/]([^/]+/[^/.]+?)(?:\.git)?$", out.stdout.strip())
            _origin_cache = m.group(1).lower() if m else None
        except Exception:
            _origin_cache = None
    return _origin_cache


def fixed_target(target: str, base: Path) -> str | None:
    """Пересчитать ссылку относительно папки README (base) — или None."""
    decoded = unquote(target)
    if decoded.startswith(("#", "..")):
        return None  # якоря и уже-относительные ../ не трогаем
    m = GH_LINK.match(decoded)
    if m:
        owner_repo = (m.group(1) + "/" + m.group(2)).lower()
        if origin_slug() is not None and owner_repo != origin_slug():
            return None  # ссылка на другой репозиторий
        cand = m.group(3)
    elif decoded.startswith(("http://", "https://")):
        return None  # внешний сайт — не трогаем
    else:
        cand = decoded.lstrip("/")
    cand = cand.rstrip("/")
    if not cand:
        return None
    path, _, anchor = cand.partition("#")
    abs_root = ROOT / path if path else None
    if abs_root is None or not abs_root.exists():
        return None  # цель не существует — не знаем, как чинить
    if (base / path).exists():
        return None  # ссылка и так работает относительно этого README
    new = os.path.relpath(str(abs_root), str(base)).replace(os.sep, "/")
    if abs_root.is_dir() and not anchor:
        new += "/"
    return md_url(new + ("#" + anchor if anchor else ""))


def normalize_links(text: str, base: Path) -> tuple[str, int]:
    """GitHub blob/tree и корневые абсолютные ссылки -> относительные пути."""
    n = 0

    def repl(m: re.Match) -> str:
        nonlocal n
        new = fixed_target(m.group(1), base)
        if new is None:
            return m.group(0)
        n += 1
        return f"]({new})"

    return TARGET_RE.sub(repl, text), n


def normalize_all_readmes() -> int:
    """Пройти по всем README репозитория и починить битые ссылки."""
    total = 0
    for rp in sorted(ROOT.rglob("README.md")):
        top = rp.relative_to(ROOT).parts[0]
        if top in EXCLUDE_TOP or top.startswith("."):
            continue
        text = rp.read_text(encoding="utf-8")
        new, n = normalize_links(text, rp.parent)
        if n:
            rp.write_text(new, encoding="utf-8")
            print(f"  исправлено ссылок: {n} — {rp.relative_to(ROOT).as_posix()}")
            total += n
    return total


def table(rows: list[list[str]]) -> str:
    if len(rows) <= 1:  # нет ни одной строки данных
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
        rows = [["Class", "Labs", "Last commit"]]
        for c in sorted(classes):
            labs = sub_writeups(c)
            rows.append([
                md_link(c.name, rel(c) + "/"),
                str(len(labs)) if labs else "-",
                last_commit(labs[-1]) if labs else "-",
            ])
        return section_header(name) + "\n\n" + table(rows)

    subs = sub_writeups(top)
    # README в папке-контейнере (описание раздела) не делает папку райтапом:
    # если внутри есть вложенные райтапы — перечисляем их построчно
    single = (top / "README.md").exists() and not subs
    if single:
        rows = [["Writeup", "Files", "Last commit"]]
        rows.append([md_link(readme_title(top), rel(top) + "/"),
                     str(count_files(top)), last_commit(top)])
        return section_header(name) + "\n\n" + table(rows)

    rows = [["Writeup", "Files", "Last commit"]]
    for w in subs:
        rows.append([md_link(readme_title(w), rel(w) + "/"),
                     str(count_files(w)), last_commit(w)])
    return section_header(name) + "\n\n" + table(rows)


def build_index() -> str:
    known_events, known_other = [], []
    for d in top_dirs():
        if d.name == PORTSWIGGER:
            continue
        if d.name.lower().startswith(("avito", "kubok", "solar")):
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


CLASS_TITLES = {
    "sqli": "SQL injection",
    "xss": "XSS",
    "csrf": "CSRF",
    "ssrf": "SSRF",
    "xxe": "XXE",
    "idor": "IDOR",
    "ssti": "SSTI",
    "jwt": "JWT",
    "oauth": "OAuth",
    "cors": "CORS",
    "access-control": "Access control",
    "path-traversal": "Path traversal",
}


def class_title(name: str) -> str:
    return CLASS_TITLES.get(name, name.replace("-", " ").capitalize())


def create_class_readme(cls: Path) -> None:
    """Заготовка README для класса без конспекта; Labs заполнит update_class_readme."""
    text = (
        f"# {class_title(cls.name)}\n\n"
        "Конспект класса из PortSwigger Web Security Academy: теория, типовые "
        "атаки и защита. Лабы — отдельные папки с райтапами "
        "(TL;DR → Steps → Why it works → Defense).\n\n"
        f"{MARK_START}\n{MARK_END}\n"
    )
    (cls / "README.md").write_text(text, encoding="utf-8")


def update_class_readme(cls: Path, labs: list[Path]) -> None:
    # Ссылки относительно папки класса: README лежит в portswigger/<класс>/,
    # поэтому путь к лабе — просто <NN-slug>/ (как в папке и лежит).
    rows = [["#", "Lab", "Last commit"]]
    for lab in labs:
        m = re.match(r"\d+", lab.name)
        num = m.group(0) if m else "-"
        local = lab.relative_to(cls).as_posix()
        rows.append([num, md_link(readme_title(lab), local + "/"), last_commit(lab)])
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
    n_updated = n_created = 0
    created: list[str] = []
    if pw.exists():
        for cls in sorted(pw.iterdir()):
            if not cls.is_dir() or cls.name.startswith("."):
                continue
            labs = sub_writeups(cls)
            if not labs:
                continue
            if not (cls / "README.md").exists():
                create_class_readme(cls)
                n_created += 1
                created.append(cls.name)
            update_class_readme(cls, labs)
            n_updated += 1
    n_fixed = normalize_all_readmes()
    print(f"Корневой README: {'обновлён' if ok else 'ошибка'}")
    print(f"Классовых README обновлено: {n_updated}, создано: {n_created}"
          + (f" ({', '.join(created)})" if created else ""))
    print(f"Ссылок переведено на относительные пути: {n_fixed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
