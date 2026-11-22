#!/usr/bin/env python3
"""Проверка райтапов на соответствие шаблону: шапка, секции, ссылки, артефакты.

Запуск из корня репозитория:  python3 tools/check_writeups.py

Дополняет tools/check_titles.py (там — заголовки A–G и код-блоки F/G).
Здесь — соответствие структуре templates/writeup-README.md.

Блокирующие (чинить до push):
  H. Шапки нет или она неполная: нет таблицы «Платформа / Событие»
     или строк Категория / Статус / Дата решения
  I. Статус противоречив: в шапке «done», а в тексте маркеры черновика
     (TODO / черновик / stub-комментарий)
  K. Пустая секция: заголовок есть, контента до следующего заголовка нет
  L. Остался текст-заглушка из шаблона (для done; в draft'ах это норма)
  M. Битые внутренние ссылки/картинки: цель ](...) не существует на диске

Предупреждения (не блокируют, но их стоит видеть):
  J. Секции канона «TL;DR → Steps → Why it works → Defense» отсутствуют
     (для done; синонимы вроде «Кратко»/«Решение»/«Почему это сработало»
     засчитываются — см. SECTION_SYNONYMS)
  W1. Artifacts перечисляет файлы, которых нет в папке задачи
  W2. EXPLANATION.md нет (канон: README + EXPLANATION + figN.png)
  W3. Рекомендованные секции не заполнены (Recon/Artifacts/References)
  N. Флаг живого CTF не замаскирован (хвост без ...REDACTED);
     для PortSwigger/HTB/picoCTF/others не проверяется — учебные платформы

Папки-контейнеры (индексы событий, классовые README с маркером INDEX) не
проверяются. В others/ чужие райтапы: проверяются только шапка, пустые
секции и ссылки — содержание чужого текста не нормируем. Логика общая
с generate_index/check_titles: те же walk_tasks, маркеры INDEX, ограды.
Только стандартная библиотека.

Выход: 0 — всегда (принт todo-листа, как у check_titles);
       с --strict — 1, если есть блокирующие пункты (H, I, K, L, M).
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_titles  # noqa: E402  (strip_index, DRAFT_MARK, FENCE_RE)
import generate_index  # noqa: E402  (tasks_of, top_dirs, MARK_START)

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "writeup-README.md"

# Платформы-тренажёры и свалка чужих райтапов: ответы можно не маскировать,
# секции чужих текстов не нормируем (только шапка/пустоты/ссылки).
LENIENT_ROOTS = {"portswigger", "hackthebox", "picoctf", "picoctf-trainings",
                 "others", "tryhackme", "vulnlab"}

REQUIRED_SECTIONS = ["TL;DR", "Steps", "Why it works", "Defense"]
RECOMMENDED_SECTIONS = ["Recon", "Artifacts", "References"]
HEADER_ROWS = ["Платформа / Событие", "Категория", "Статус", "Дата решения"]

# Синонимы заголовков: канон шаблона, но легаси-райтапы писались своими
# словами. Нормализованный заголовок считается секцией, если содержит
# один из синонимов (substring по нижнему регистру без пунктуации).
SECTION_SYNONYMS = {
    "TL;DR": ("tl;dr", "tldr", "кратко", "коротко", "summary", "суть",
              "итог", "резюме"),
    "Steps": ("steps", "step", "решение", "шаг", "walkthrough",
              "solution", "эксплуатация", "ход работы"),
    "Why it works": ("why it works", "почему это работает",
                     "почему это сработало", "почему работает", "why"),
    "Defense": ("defense", "защит", "как закрыть", "как защититься",
                "mitigation", "рекомендац"),
    "Recon": ("recon", "разведк", "триаж", "осмотр"),
    "Artifacts": ("artifact", "артефакт", "файлы"),
    "References": ("reference", "ссылк", "источник"),
}

H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.M)
# Строки шапки: «| **Категория** | web |» и легаси «| Категория | Web |» —
# болд опционален, имя ячейки нормализуем при сравнении.
TABLE_ROW_RE = re.compile(r"^\|\s*(\*\*)?(.+?)(\*\*)?\s*\|\s*(.*?)\s*\|$", re.M)
LINK_RE = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)\)")
IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
STUB_COMMENT_RE = re.compile(r"<!--\s*stub", re.I)
FLAG_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9_]{2,20}\{([^{}]{8,})\}")
ARTIFACT_RE = re.compile(r"^- `([^`]+)`", re.M)
DONE_STATUS_RE = re.compile(
    r"^(?:done|решено|готово|закрыто|.*(?:флаг|флаги)\s+получен.*)$", re.I)

SKIP_SCHEME = re.compile(r"^(?:https?://|mailto:|ftp://|#|tel:)", re.I)


def fenced_lines(text: str) -> set[int]:
    """Номера строк внутри код-блоков (правила закрытия — как в check_titles).

    Блок закрывает только голая ограда не короче открывавшей; ```lang
    внутри блока — контент, а не закрытие."""
    inside: set[int] = set()
    inb, olen = False, 3
    for i, line in enumerate(text.splitlines(), 1):
        m = check_titles.FENCE_RE.match(line)
        if m:
            marker, ticks, info = m.group(2), m.group(3), (m.group(4) or "").strip()
            if not inb:
                inb, olen = True, len(ticks)
                inside.add(i)
            elif not marker and not info and len(ticks) >= olen:
                inb = False
            else:
                inside.add(i)
        elif inb:
            inside.add(i)
    return inside


def readable(text: str) -> str:
    """Текст без INDEX-секций, код-блоков и инлайн-кода — то, что рендер
    считает контентом (ссылки и заголовки внутри ``` не считаются)."""
    text = check_titles.strip_index(text)
    lines = text.splitlines()
    body = "\n".join(l for i, l in enumerate(lines, 1)
                     if i not in fenced_lines(text))
    return INLINE_CODE_RE.sub("", body)


def parse_header(text: str) -> dict[str, str]:
    """Таблица шапки: {«Платформа / Событие»: ..., «Статус»: ...}.

    Болд в имени ячейки опционален (легаси-таблицы его не ставят)."""
    rows = {}
    for m in TABLE_ROW_RE.finditer(text):
        name = (m.group(2) or "").strip()
        if name and name not in ("—", "-"):
            rows[name] = (m.group(4) or "").strip()
    return rows


def norm_title(s: str) -> str:
    return re.sub(r"[^\wа-яё]+", " ", s.lower(), flags=re.UNICODE).strip()


def sections(text: str) -> dict[str, str]:
    """Заголовки H2 -> текст секции (до следующего заголовка любого уровня)."""
    out: dict[str, str] = {}
    heads = [(m.start(), m.group(1).strip(), m.end()) for m in H2_RE.finditer(text)]
    for idx, (start, title, end) in enumerate(heads):
        nxt = heads[idx + 1][0] if idx + 1 < len(heads) else len(text)
        out.setdefault(title, text[end:nxt])
    return out


def find_sections(secs: dict[str, str], wanted: str) -> str | None:
    """Текст секции по каноническому имени с учётом синонимов.

    Синонимы нормализуются так же, как заголовки: «TL;DR» и «TL DR»
    должны совпадать."""
    syns = [norm_title(s) for s in SECTION_SYNONYMS.get(wanted, (wanted.lower(),))]
    for title, body in secs.items():
        t = norm_title(title)
        if any(s and s in t for s in syns):
            return body
    return None


def is_empty(body: str) -> bool:
    """Секция без контента: только пустые строки до следующего заголовка."""
    return not any(l.strip() for l in body.splitlines())


def template_stub_lines() -> list[str]:
    """Фразы-заглушки из шаблона: содержательные строки без таблиц и оград."""
    stubs = []
    try:
        for line in TEMPLATE.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if (len(s) >= 25 and not s.startswith(("#", "|", "```", "###"))
                    and not s.startswith("<!--")):
                stubs.append(s)
    except Exception:
        pass
    return stubs


def link_targets(text: str, base: Path) -> list[str]:
    """Относительные цели ссылок/картинок, которых нет на диске."""
    bad = []
    for rx in (IMG_RE, LINK_RE):
        for m in rx.finditer(text):
            target = unquote(m.group(1)).strip()
            if SKIP_SCHEME.match(target):
                continue
            path = target.split("#", 1)[0].rstrip("/")
            if not path:
                continue  # якорь внутри страницы
            if not (base / path).exists():
                bad.append(target)
    return sorted(set(bad))


def check_task(d: Path, problems: dict[str, list[str]],
               warnings: dict[str, list[str]], stubs: list[str]) -> None:
    rel = d.relative_to(ROOT).as_posix()
    top = d.relative_to(ROOT).parts[0]
    try:
        text = (d / "README.md").read_text(encoding="utf-8")
    except Exception:
        return
    if generate_index.MARK_START in text:
        return  # контейнер: индекс события/класса, не райтап
    body = readable(text)
    header = parse_header(body)
    status_raw = header.get("Статус", "")
    done = bool(DONE_STATUS_RE.match(status_raw))

    # H. шапка
    missing_rows = [r for r in HEADER_ROWS if r not in header]
    if missing_rows:
        problems["H. шапка неполная (нет строки в таблице)"].append(
            f"{rel} — нет: {', '.join(missing_rows)}")

    # I. статус противоречив
    draftish = bool(check_titles.DRAFT_MARK.search(body))
    if done and draftish:
        problems["I. статус противоречив (в шапке done, в тексте черновик)"].append(rel)
    if done and STUB_COMMENT_RE.search(body):
        problems["I. статус противоречив (в шапке done, в тексте stub-комментарий)"].append(rel)

    own = top not in LENIENT_ROOTS
    secs = sections(body) if own else {}

    # J. канонические секции (для своих done; синонимы засчитываются)
    if own and done:
        missing = [s for s in REQUIRED_SECTIONS
                   if find_sections(secs, s) is None]
        if missing:
            warnings["J. нет секции канона TL;DR → Steps → Why it works → Defense"].append(
                f"{rel} — нет: {', '.join(missing)}")

    # K. пустые секции
    for title, sec in secs.items():
        if is_empty(sec):
            problems["K. пустая секция (заголовок без контента)"].append(
                f"{rel} — «{title}»")

    # L. текст-заглушка из шаблона (для своих done)
    if own and done:
        hits = [s for s in stubs if s in body]
        if hits:
            first = hits[0]
            shown = f"«{first[:60]}…»" if len(first) > 60 else f"«{first}»"
            problems["L. остался текст-заглушка из шаблона"].append(f"{rel} — {shown}")

    # M. битые внутренние ссылки/картинки
    bad = link_targets(body, d)
    if bad:
        problems["M. ссылка/картинка на несуществующий файл"].append(
            f"{rel} — {', '.join(bad[:5])}" + ("..." if len(bad) > 5 else ""))

    # --- предупреждения ---
    if own and done:
        rec_missing = [s for s in RECOMMENDED_SECTIONS
                       if find_sections(secs, s) is None]
        if rec_missing:
            warnings["W3. рекомендованные секции не заполнены"].append(
                f"{rel} — {', '.join(rec_missing)}")
        if not (d / "EXPLANATION.md").exists():
            warnings["W2. EXPLANATION.md нет"].append(rel)
        art = find_sections(secs, "Artifacts") or ""
        missing_files = []
        for m in ARTIFACT_RE.finditer(art):
            name = m.group(1)
            if name.startswith(("http", "fig")) or "*" in name:
                continue
            if not (d / name).exists() and not (d / "files" / name).exists():
                missing_files.append(name)
        if missing_files:
            warnings["W1. Artifacts: файлов нет в папке задачи"].append(
                f"{rel} — {', '.join(missing_files[:6])}"
                + ("..." if len(missing_files) > 6 else ""))

    if top not in LENIENT_ROOTS:
        for m in FLAG_RE.finditer(body):
            tail = m.group(1)
            if "REDACTED" in tail or "\\" in tail:
                continue  # LaTeX-нотация (pmod{\varphi(N)}) — не флаг
            shown = f"{m.group(0)[:44]}..." if len(m.group(0)) > 44 else m.group(0)
            warnings["N. флаг не замаскирован (живой CTF?)"].append(f"{rel} — {shown}")
            break


def main() -> int:
    if not (ROOT / ".git").exists():
        print("Запусти скрипт из корня репозитория (не найден .git).")
        return 1
    strict = "--strict" in sys.argv
    stubs = template_stub_lines()

    problems: dict[str, list[str]] = defaultdict(list)
    warnings: dict[str, list[str]] = defaultdict(list)
    for d in generate_index.top_dirs():
        for task in generate_index.tasks_of(d):
            if (task / "README.md").exists():
                check_task(task, problems, warnings, stubs)

    for group, items in problems.items():
        print(f"\n{group} — {len(items)}:")
        for item in sorted(items):
            print(f"  - {item}")
    for group, items in warnings.items():
        print(f"\n{group} — {len(items)} (предупреждение):")
        for item in sorted(items):
            print(f"  - {item}")

    blocking = sum(len(v) for v in problems.values())
    print(f"\nБлокирующие замечания: {blocking}, предупреждений: "
          f"{sum(len(v) for v in warnings.values())}")
    if blocking == 0:
        print("Структура по шаблону. Огонь.")
    if strict and blocking:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
