#!/usr/bin/env python3
"""Генератор дашборда и индексов для ctf-writeups.

Запуск из корня репозитория:  python3 tools/generate_index.py

Что делает:
  1. Корневой README.md — дашборд: одна строка на каждую папку первого
     уровня (ссылка, решено/всего, черновики, последний коммит). Больше
     в корне никаких таблиц категорий — вся детализация в README самих
     папок. Секция между <!-- INDEX:START --> и <!-- INDEX:END -->.
  2. Каждая папка первого уровня (portswigger, solarctf-2026, bootcamp,
     hackthebox, others...) получает свой README.md: строка прогресса
     (Solved: n/total) + разбивка по категориям и таскам со статусом
     каждого райтапа. Нет README — создаст заготовку.
  3. Классы PortSwigger: таблица лаб в классовом README (со статусами),
     заготовка конспекта класса, если README ещё нет.
  4. Чинит ссылки во всех README: GitHub blob/tree-URL и корневые
     абсолютные пути переписывает в относительные (как папки лежат
     на диске). Ссылки на чужие репо и внешние сайты не трогает.

Статусы райтапа:
  done    — README заполнен, маркеров черновика нет;
  draft   — в README есть маркер: draft / черновик / в работе / TODO / TBD
            (райтап из шаблона создаётся со строкой «Статус | draft»);
  —       — папка есть (скрипты, файлы), README ещё нет — на дорешке.

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

# Папки-платформы (не CTF-события): попадают в "Platforms & trainings".
# События — отдельный список не нужен: всё, что оканчивается на год
# (flare-on-2014, solarctf-2026), — событие (см. is_event).
PLATFORM_DIRS = {
    PORTSWIGGER, "hackthebox", "picoctf", "picoctf-trainings",
    "bootcamp", "standoff-bootcamp", "tryhackme", "vulnlab", "others",
}

# Названия для заголовков README (ключ — имя папки без года). Если папка
# называется нестандартно — просто добавь сюда строку; иначе заголовок
# соберётся автоматически из имени папки.
EVENT_TITLES = {
    "portswigger": "PortSwigger Web Security Academy",
    "picoctf": "picoCTF",
    "picoctf-trainings": "picoCTF Trainings",
    "solarctf": "Solar CTF",
    "solar": "Solar CTF",
    "ligactf": "Лига CTF",
    "liga-ctf": "Лига CTF",
    "liga-ctf-r1": "Лига CTF (раунд 1)",
    "avitoctf": "AvitoCTF",
    "kubok-ctf": "Кубок CTF",
    "bootcamp": "Standoff Bootcamp",
    "flare-on": "Flare-On",
    "hackthebox": "Hack The Box",
    "others": "Разные задачи",
}

YEAR_RE = re.compile(r"^(.*?)-(\d{4})$")
SEASON_RE = re.compile(r"^(.*?)-(\d{1,2})$")
DRAFT_MARK = re.compile(
    r"\b(?:draft|черновик|черновая|в работе|todo|tbd)(?![\w/\-]|\.\w)", re.I)
WALK_DEPTH = 3  # райтапы ищем вглубь до 3 уровней (категория/уровень/таск)

STATUS_DONE = "done"
STATUS_DRAFT = "draft"
STATUS_MISSING = "—"


def is_event(name: str) -> bool:
    """CTF-событие vs платформа.

    Событие — всё, что оканчивается на год: flare-on-2014, solarctf-2026,
    liga-ctf-r1-2026 (год в имени — чек-лист п.14). Платформы перечислены
    в PLATFORM_DIRS; остальное — эвристики по префиксу.
    """
    low = name.lower()
    if low in PLATFORM_DIRS:
        return False
    if YEAR_RE.match(low):
        return True
    return (low.startswith(("avito", "kubok", "solar", "liga"))
            or "ctf" in low)


def event_title(name: str) -> str:
    """solarctf-2026 -> «Solar CTF 2026», standoff-bootcamp-7 ->
    «Standoff Bootcamp 7», bootcamp -> «Standoff Bootcamp»."""
    m = YEAR_RE.match(name)
    if m:
        base, year = m.group(1), m.group(2)
    else:
        m = SEASON_RE.match(name)
        base = m.group(1) if m else name
        year = m.group(2) if m else ""
    title = EVENT_TITLES.get(base.lower())
    if title is None:
        title = " ".join("CTF" if w.lower() == "ctf" else w.capitalize()
                         for w in base.split("-"))
    return f"{title} {year}".strip()

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
    """Заголовок из README райтапа; без README — имя папки."""
    try:
        for line in (folder / "README.md").read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("# "):
                return s[2:].strip()
    except Exception:
        pass
    return folder.name


def _norm_title(s: str) -> str:
    return re.sub(r"[^a-zа-я0-9]+", " ", s.lower()).strip()


def task_title(d: Path) -> str:
    """Заголовок таска для индекса.

    Обычно H1 из README, но если H1 совпадает с названием события или
    платформы (так бывает, когда корневой README события перенесён в
    папку таска целиком — как flare-on-2014/C1) — показываем имя папки,
    иначе в таблице будут две одинаковые ссылки."""
    title = readme_title(d)
    top = d.relative_to(ROOT).parts[0]
    if _norm_title(title) in {_norm_title(event_title(top)), _norm_title(top)}:
        return d.name
    return title


def top_dirs() -> list[Path]:
    return sorted(
        d for d in ROOT.iterdir()
        if d.is_dir() and not d.name.startswith(".") and d.name not in EXCLUDE_TOP
    )


def walk_tasks(parent: Path, depth: int = WALK_DEPTH) -> list[Path]:
    """Все таски вглубь до depth уровней — ВКЛЮЧАЯ папки без README.

    Таск = папка с README.md, ИЛИ папка без README, у которой прямо внутри
    лежат файлы (решается, райтап не написан; вложенные подпапки — это
    ассеты типа img/, files/ и отдельно не разворачиваются). Папка без
    README и без своих файлов — категория-контейнер: идём внутрь."""
    found = []
    for d in sorted(parent.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        if (d / "README.md").exists():
            found.append(d)
            continue
        if any(p.is_file() for p in d.iterdir()):
            found.append(d)  # файлы прямо здесь — таск, а не категория
            continue
        inner = walk_tasks(d, depth - 1) if depth > 1 else []
        found.extend(inner)
    return found


def tasks_of(d: Path) -> list[Path]:
    """Таски папки верхнего уровня; portswigger — лабы всех классов."""
    if d.name == PORTSWIGGER:
        out = []
        for cls in pw_classes():
            out.extend(walk_tasks(cls))
        return out
    return walk_tasks(d)


# --- статусы и прогресс ---

def task_status(d: Path) -> str:
    """done / draft (маркер черновика в README) / — (README нет)."""
    rp = d / "README.md"
    if not rp.exists():
        return STATUS_MISSING
    try:
        text = rp.read_text(encoding="utf-8")
    except Exception:
        return STATUS_MISSING
    return STATUS_DRAFT if DRAFT_MARK.search(text) else STATUS_DONE


def stats(tasks: list[Path]) -> tuple[int, int, int]:
    """(готово, черновиков, без райтапа)."""
    st = [task_status(t) for t in tasks]
    return (st.count(STATUS_DONE), st.count(STATUS_DRAFT),
            st.count(STATUS_MISSING))


def stats_line(tasks: list[Path]) -> str:
    done, draft, missing = stats(tasks)
    if not tasks:
        return "Nothing here yet."
    line = f"Solved: {done}/{len(tasks)}"
    extra = []
    if draft:
        extra.append(f"drafts: {draft}")
    if missing:
        extra.append(f"no writeup: {missing}")
    return line + (" · " + " · ".join(extra) if extra else "")


def done_total(tasks: list[Path]) -> str:
    done, _, _ = stats(tasks)
    return f"{done}/{len(tasks)}"


# --- markdown-хелперы ---

def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def md_url(path: str) -> str:
    """URL для ссылки: экранируем то, что ломает markdown-ссылку."""
    return path.replace(" ", "%20").replace("(", "%28").replace(")", "%29")


def md_link(text: str, path: str) -> str:
    """Кликабельная ячейка таблицы: [текст](путь)."""
    text = (text.replace("\\", "\\\\")
                .replace("[", "\\[")
                .replace("]", "\\]")
                .replace("|", "\\|"))
    return f"[{text}]({md_url(path)})"


def table(rows: list[list[str]]) -> str:
    if len(rows) <= 1:  # нет ни одной строки данных
        return "_Пока пусто._\n"
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    def fmt(r): return "| " + " | ".join(c.ljust(w) for c, w in zip(r, widths)) + " |"
    sep = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
    return "\n".join([fmt(rows[0]), sep] + [fmt(r) for r in rows[1:]]) + "\n"


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


# --- корневой README: дашборд, одна строка на папку ---

def dashboard_row(d: Path, tasks: list[Path]) -> list[str]:
    done, draft, _ = stats(tasks)
    return [
        md_link(d.name, d.name + "/"),
        f"{done}/{len(tasks)}",
        str(draft) if draft else "—",
        last_commit(d),
    ]


def dashboard(items: list[tuple[Path, list[Path]]]) -> str:
    """Строка прогресса секции + таблица «одна строка на папку»."""
    rows = [["Folder", "Done", "Draft", "Last commit"]]
    all_tasks: list[Path] = []
    for d, t in items:
        rows.append(dashboard_row(d, t))
        all_tasks.extend(t)
    return (stats_line(all_tasks) + "\n\n" + table(rows)).rstrip()


def build_index() -> str:
    events, platforms = [], []
    for d in top_dirs():
        if d.name == PORTSWIGGER:
            continue
        (events if is_event(d.name) else platforms).append(d)

    parts = []
    pw = ROOT / PORTSWIGGER
    if pw.exists():
        pw_tasks = tasks_of(pw)
        if pw_tasks:
            parts.append("## PortSwigger Academy\n\n" + dashboard([(pw, pw_tasks)]))
    ev = [(d, tasks_of(d)) for d in events]
    ev = [(d, t) for d, t in ev if t]
    if ev:
        parts.append("## CTF events\n\n" + dashboard(ev))
    pl = [(d, tasks_of(d)) for d in platforms]
    pl = [(d, t) for d, t in pl if t]
    if pl:
        parts.append("## Platforms & trainings\n\n" + dashboard(pl))
    return "\n\n".join(p.rstrip() for p in parts)


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


# --- README каждой папки первого уровня ---

def create_folder_readme(folder: Path) -> None:
    """Заготовка README папки; индекс внутри заполнит update_folder_readme."""
    if folder.name == PORTSWIGGER:
        intro = ("Конспекты классов: теория, типовые атаки и защита. Лабы — "
                 "отдельные папки с райтапами (TL;DR → Steps → Why it works → "
                 "Defense). Индекс ниже ведётся скриптом `tools/generate_index.py`"
                 " — между маркерами руками не править.")
    else:
        intro = ("Райтапы: TL;DR → Steps → Why it works → Defense. Индекс ниже "
                 "ведётся скриптом `tools/generate_index.py` — между маркерами "
                 "руками не править.")
    text = (
        f"# {event_title(folder.name)}\n\n"
        f"{intro}\n\n"
        f"{MARK_START}\n{MARK_END}\n"
    )
    (folder / "README.md").write_text(text, encoding="utf-8")


def task_table(tasks: list[Path], base: Path) -> str:
    """Таблица тасков: Task | Status | Last commit; пути от base (папки README)."""
    rows = [["Task", "Status", "Last commit"]]
    for t in tasks:
        local = t.relative_to(base).as_posix() + "/"
        rows.append([
            md_link(task_title(t), local),
            task_status(t),
            last_commit(t),
        ])
    return table(rows)


def outline(parent: Path, base: Path, depth: int = WALK_DEPTH) -> str:
    """Разбивка папки на категории: заголовок «### [cat](cat/) — n/total»
    (плюс черновики/дорешка, если есть) и таблица тасков. Вложенные
    категории — рекурсией, пути считаются от base (папки README)."""
    tasks = walk_tasks(parent, depth)
    parts = []
    direct = [t for t in tasks if t.parent == parent]
    if direct:
        parts.append(task_table(direct, base))
    groups: dict[str, list[Path]] = {}
    for t in tasks:
        rp = t.relative_to(parent).parts
        if len(rp) > 1:
            groups.setdefault(rp[0], []).append(t)
    for gname, gtasks in sorted(groups.items()):
        gdir = parent / gname
        _, draft, missing = stats(gtasks)
        head = f"### {md_link(gname, md_url(gdir.relative_to(base).as_posix()) + '/')} — {done_total(gtasks)}"
        if draft:
            head += f" · {draft} draft"
        if missing:
            head += f" · {missing} no writeup"
        parts.append(head + "\n\n" + outline(gdir, base, depth - 1))
    return "\n\n".join(p.rstrip() for p in parts)


def folder_index_block(folder: Path) -> str:
    tasks = walk_tasks(folder)
    if not tasks:
        return "Nothing here yet."
    return (stats_line(tasks) + "\n\n" + outline(folder, folder)).rstrip()


def update_folder_readme(folder: Path, block: str) -> None:
    rp = folder / "README.md"
    text = rp.read_text(encoding="utf-8")
    if MARK_START in text and MARK_END in text:
        pre = text.split(MARK_START)[0]
        post = text.split(MARK_END)[1]
        text = pre + f"{MARK_START}\n{block}\n{MARK_END}" + post
    else:
        # ручной README без маркеров: дописываем блок С маркерами,
        # чтобы следующие прогоны обновляли его на месте
        text = (text.rstrip() + "\n\n---\n\n"
                + f"{MARK_START}\n{block}\n{MARK_END}" + "\n")
    rp.write_text(text, encoding="utf-8")


# --- классы PortSwigger ---

def pw_classes() -> list[Path]:
    pw = ROOT / PORTSWIGGER
    if not pw.exists():
        return []
    return sorted(d for d in pw.iterdir()
                  if d.is_dir() and not d.name.startswith("."))


def pw_index_block() -> str:
    """Индекс для portswigger/README.md: прогресс + таблица классов."""
    tasks = tasks_of(ROOT / PORTSWIGGER)
    if not tasks:
        return "Nothing here yet."
    rows = [["Class", "Done", "Draft", "Last commit"]]
    for cls in pw_classes():
        t = walk_tasks(cls)
        if t:
            rows.append(dashboard_row(cls, t))
    return (stats_line(tasks) + "\n\n" + table(rows)).rstrip()


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
    rows = [["Lab", "Status", "Last commit"]]
    for lab in labs:
        local = lab.relative_to(cls).as_posix()
        rows.append([
            md_link(task_title(lab), local + "/"),
            task_status(lab),
            last_commit(lab),
        ])
    block = f"{MARK_START}\n## Labs\n\n{table(rows)}\n{MARK_END}"

    readme = cls / "README.md"
    text = readme.read_text(encoding="utf-8") if readme.exists() else ""
    if MARK_START in text and MARK_END in text:
        pre = text.split(MARK_START)[0]
        post = text.split(MARK_END)[1]
        text = pre + block + post
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


# --- отчёт в консоль ---

def print_coverage() -> None:
    """Прогресс по папкам первого уровня — объём и статусы, для планирования."""
    print("\nПрогресс:")
    printed = False
    for d in top_dirs():
        tasks = tasks_of(d)
        if not tasks:
            continue
        done, draft, missing = stats(tasks)
        line = f"  {d.name}: {done}/{len(tasks)} done"
        if draft:
            line += f", draft: {draft}"
        if missing:
            line += f", без райтапа: {missing}"
        if d.name == PORTSWIGGER:
            per = []
            for cls in pw_classes():
                t = walk_tasks(cls)
                if t:
                    per.append(f"{cls.name}: {done_total(t)}")
            if per:
                line += " (" + ", ".join(per) + ")"
        else:
            groups: dict[str, list[Path]] = {}
            for t in tasks:
                rp = t.relative_to(d).parts
                if len(rp) > 1:
                    groups.setdefault(rp[0], []).append(t)
            if groups:
                per = ", ".join(f"{g}: {done_total(gt)}"
                                for g, gt in sorted(groups.items()))
                line += " (" + per + ")"
        print(line)
        printed = True
    if not printed:
        print("  пока пусто")


def main() -> int:
    if not (ROOT / ".git").exists():
        print("Запусти скрипт из корня репозитория (не найден .git).")
        return 1
    ok = update_root_readme()

    n_updated = n_created = 0
    created: list[str] = []
    if (ROOT / PORTSWIGGER).exists():
        for cls in pw_classes():
            labs = walk_tasks(cls)
            if not labs:
                continue
            if not (cls / "README.md").exists():
                create_class_readme(cls)
                n_created += 1
                created.append(cls.name)
            update_class_readme(cls, labs)
            n_updated += 1

    ev_updated = ev_new = 0
    folders_created: list[str] = []
    for d in top_dirs():
        if not tasks_of(d):
            continue  # пустая папка или одиночный райтап — индекс не нужен
        if not (d / "README.md").exists():
            create_folder_readme(d)
            ev_new += 1
            folders_created.append(d.name)
        block = (pw_index_block() if d.name == PORTSWIGGER
                 else folder_index_block(d))
        update_folder_readme(d, block)
        ev_updated += 1

    n_fixed = normalize_all_readmes()
    print(f"Корневой README (дашборд): {'обновлён' if ok else 'ошибка'}")
    print(f"Классовых README обновлено: {n_updated}, создано: {n_created}"
          + (f" ({', '.join(created)})" if created else ""))
    print(f"README папок: обновлено {ev_updated}, создано: {ev_new}"
          + (f" ({', '.join(folders_created)})" if folders_created else ""))
    print(f"Ссылок переведено на относительные пути: {n_fixed}")
    print_coverage()
    return 0


if __name__ == "__main__":
    sys.exit(main())
