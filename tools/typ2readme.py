#!/usr/bin/env python3
"""Конвертер конспектов Typst (.typ) -> README.md райтапа.

Запуск из корня репозитория:  python3 tools/typ2readme.py [опции]

Что делает:
  Ищет в репозитории все *.typ (кроме tools/, templates/, скрытых папок,
  корня репо и файлов template*.typ). Для каждого конспекта пишет README.md
  в его же папке: разметка Typst переводится в Markdown (заголовки, жирный/
  курсив, списки, термины, raw-блоки, ссылки, картинки, цитаты, математика),
  сверху добавляется шапка райтапа из шаблона.

  Метаданные берутся из шапки конспекта #align(right)[...] с полями
  *Задание:* / *Категория:* / *Сложность:* / *Дата:* — они попадают в
  шапку README и в заголовок документа. Нет их — событие и категория
  определяются по пути папки.

  Существующий README.md:
  - БЕЗ маркеров черновика (draft / черновик / в работе / TODO / TBD) —
    готовый райтап, не трогается («пропущено»);
  - С маркером черновика (заглушка от скриптов или недописанный) —
    заменяется: источник истины — .typ рядом. Пока в шапке есть draft,
    перегон обновляет README из .typ; пометил done — заморожен.
  - --force — заменить любой README, --no-stubs — ничего не заменять.

Статус в шапке ставится из --status (по умолчанию draft). Пометить
райтапы готовыми: --status done при конвертации, или
«python3 tools/typ2readme.py --mark-done» для уже существующих,
или руками строку «Статус» в шапке README.

Примеры:
  python3 tools/typ2readme.py                  # конвертировать всё новое
  python3 tools/typ2readme.py --list           # что найдено и что сделает
  python3 tools/typ2readme.py --status done    # конверт сразу со статусом done
  python3 tools/typ2readme.py --mark-done      # готовым черновикам draft -> done
  python3 tools/typ2readme.py --force --dry-run
  python3 tools/typ2readme.py "picoctf-trainings/**/*.typ"   # по маске

Только стандартная библиотека. Файл читается как utf-8 (BOM допускается),
README пишется в utf-8 с LF.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXCLUDE = {"tools", "templates", ".git", ".github", "node_modules"}
PROVENANCE = "<!-- конвертировано из {}.typ, tools/typ2readme.py -->"
# Маркеры автогенерированных индексов (generate_index) — README с ними
# это папка-индекс/дашборд, а не райтап: статусы в таблицах чужие.
INDEX_MARK = "<!-- INDEX:START -->"
INDEX_END_MARK = "<!-- INDEX:END -->"


def strip_index_blocks(text: str) -> str:
    """Вырезать автосекции между INDEX-маркерами (там статусы чужих райтапов)."""
    while INDEX_MARK in text and INDEX_END_MARK in text:
        pre, rest = text.split(INDEX_MARK, 1)
        text = pre + rest.split(INDEX_END_MARK, 1)[1]
    return text

# Preamble-функции Typst: вырезаются целиком (вместе с их аргументами).
PREAMBLE = {"import", "include", "set", "show", "let", "outline",
            "pagebreak", "colbreak", "place", "page", "lorem"}

# Свои блочные функции из preamble конспектов (если определены #let-ом,
# то определение вырезается, а вызов конвертируется):
#   #codeblock(lang: "bash")[...] -> ```bash-ограда
#   #resultblock[...]             -> ```text-ограда (вывод команды)
#   #yellowbox[...] / #redbox[...] -> цитата-примечание
BOX_FUNCS = {"codeblock", "resultblock", "yellowbox", "redbox", "terminal"}

# Typst -> LaTeX для GitHub-математики (best-effort, простые случаи).
MATH_SUBS = [
    (r"\\?frac\(([^,()]+),\s*([^()]+)\)", r"\\frac{\1}{\2}"),
    (r"\\?sqrt\(([^()]+)\)", r"\\sqrt{\1}"),
    (r"\\?hat\(([^()]+)\)", r"\\hat{\1}"),
    (r"\\?overline\(([^()]+)\)", r"\\overline{\1}"),
    (r"\\?bold\(([^()]+)\)", r"\\mathbf{\1}"),
    (r"plus\.minus|\bpm\b", r"\\pm"),
    (r"\bmult\b|\bdot\.op\b|\btimes\b", r"\\cdot"),
    (r"->", r"\\rightarrow"),
    (r"=>", r"\\Rightarrow"),
    (r"<=>", r"\\Leftrightarrow"),
    (r"==>", r"\\Longrightarrow"),
    (r"<=", r"\\leq"),
    (r">=", r"\\geq"),
    (r"!=", r"\\neq"),
    (r"\bin\b", r"\\in"),
    (r"\bsubset\.eq\b|\bsubset\b", r"\\subseteq"),
    (r"\bunion\b", r"\\cup"),
    (r"\binter\b", r"\\cap"),
    (r"\bsum\b", r"\\sum"),
    (r"\bproduct\b", r"\\prod"),
    (r"\binfinity\b", r"\\infty"),
    (r"\bequiv\b", r"\\equiv"),
    (r"\bRR\b", r"\\mathbb{R}"),
    (r"\bZZ\b", r"\\mathbb{Z}"),
    (r"\bNN\b", r"\\mathbb{N}"),
    (r"\balpha\b", r"\\alpha"), (r"\bbeta\b", r"\\beta"),
    (r"\bgamma\b", r"\\gamma"), (r"\bdelta\b", r"\\delta"),
    (r"\bepsilon\b", r"\\epsilon"), (r"\btheta\b", r"\\theta"),
    (r"\blambda\b", r"\\lambda"), (r"\bmu\b", r"\\mu"),
    (r"\bpi\b", r"\\pi"), (r"\brho\b", r"\\rho"),
    (r"\bsigma\b", r"\\sigma"), (r"\bphi\b", r"\\phi"),
    (r"\bomega\b", r"\\omega"),
]
KNOWN_MATH_FUNCS = {"frac", "sqrt", "hat", "overline", "bold", "abs", "round",
                    "floor", "ceil", "cases", "mat", "vec", "binom", "limit",
                    "attach", "display", "inline", "op", "overbrace"}

SYM_MAP = {
    "#sym.arrow.r": "→", "#sym.arrow.l": "←", "#sym.arrow": "→",
    "#sym.checkmark": "✓", "#sym.cross": "✗", "#sym.dots.h.c": "…",
    "#sym.plus": "+", "#sym.minus": "−", "#sym.times": "×",
}

WARNINGS: list[str] = []

# Маркер черновика — как в generate_index.DRAFT_MARK: «Статус | draft»,
# TODO-секции и т.п. Черновой README конверт заменяет, готовый не трогает.
DRAFT_MARK_RE = re.compile(r"\b(?:draft|черновик|черновая|в работе|todo|tbd)\b", re.I)

# Строки-заполнители в заглушках (сами по себе контентом не считаются).
PLACEHOLDER_RE = re.compile(
    r"^(?:TODO|TBD|—|–|\.{3}|…|-{1,3}|_+(?:TODO|TBD)_+)$", re.I)

# Подсказки из шаблона templates/writeup-README.md — инструкция, не контент.
STUB_HINT_RE = re.compile(
    r"по шаблону|templates/writeup|перенести в README|Одна-две фразы|"
    r"не хочет читать по шагам|Что было видно на старте|Ментальная модель|"
    r"Как закрыть такую дыру|конкретный механизм|команда / запрос|"
    r"Название (?:следующего )?шага|схема атаки", re.I)


def warn(msg: str) -> None:
    if msg not in WARNINGS:
        WARNINGS.append(msg)


# --- примитивы Typst-синтаксиса ---

def balance_at(text: str, start: int, open_ch: str, close_ch: str) -> int:
    """Индекс символа ЗА закрывающую скобку; -1, если не закрылась."""
    depth, i = 0, start
    while i < len(text):
        c = text[i]
        if c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def depth_of(s: str) -> int:
    """Наивный баланс скобок ()[]{} в строке (строки в кавычках не учитываем)."""
    s = re.sub(r'"[^"]*"', "", s)
    s = re.sub(r"\([^)]*\"[^\"]*$", "", s)  # оборванная кавычка — режем хвост
    for a, b in (("(", ")"), ("[", "]"), ("{", "}")):
        s = s.replace(a, "(").replace(b, ")")
    return s.count("(") - s.count(")")


def strip_labels(s: str) -> str:
    """Убрать метки <label> и ссылки @ref (но не @ внутри URL после «/»)."""
    s = re.sub(r"<[A-Za-z0-9_-]+>", "", s)
    return re.sub(r"(?<![/\w])@[A-Za-z0-9_-]+", "", s)


def typst_math_to_md(m: str) -> str:
    """Содержимое Typst-математики -> приближение LaTeX для GitHub."""
    out = m
    for pat, repl in MATH_SUBS:
        out = re.sub(pat, repl, out)
    out = re.sub(r"\s+", " ", out).strip()
    for f in re.findall(r"([a-zA-Z][\w.]*)\(", out):
        base = f.split(".")[-1]
        if base not in KNOWN_MATH_FUNCS:
            warn(f"математика: не знаю функцию «{f}()» — проверь руками")
    return out


def _outside_code(line: str, fn) -> str:
    """Применить fn к частям строки ВНЕ инлайн-кода `...`."""
    parts = re.split(r"(`[^`]*`)", line)
    for idx in range(0, len(parts), 2):
        parts[idx] = fn(parts[idx])
    return "".join(parts)


def wrap_bold(line: str) -> str:
    """Typst *bold* -> Markdown **bold** (вне инлайн-кода); ~ -> пробел."""

    def one(s: str) -> str:
        s = re.sub(r"(?<![\w\\*])\*([^*\n]+?)\*(?!\*)", r"**\1**", s)
        return s.replace("~", " ")

    return _outside_code(line, one)


def convert_inline_math(line: str) -> str:
    """Инлайн-математика $...$ внутри строки -> $latex$ (вне инлайн-кода)."""
    parts = re.split(r"(`[^`]*`)", line)
    for idx in range(0, len(parts), 2):
        parts[idx] = _convert_math_spans(parts[idx])
    return "".join(parts)


def _convert_math_spans(s: str) -> str:
    parts, i = [], 0
    while i < len(s):
        j = s.find("$", i)
        if j == -1:
            parts.append(s[i:])
            break
        if j > 0 and s[j - 1] == "\\":  # \$ — экранированный доллар
            parts.append(s[i:j + 1])
            i = j + 1
            continue
        k = s.find("$", j + 1)
        if k == -1:  # одинокий $ — оставляем как есть
            parts.append(s[i:])
            break
        parts.append(s[i:j] + "$" + typst_math_to_md(s[j + 1:k]) + "$")
        i = k + 1
    return "".join(parts)


# --- функции #name(args)[body] ---

def replace_first_fn(line: str, name: str) -> str | None:
    """Заменить первое вхождение #name(...)[...] на Markdown; None — нет его."""
    m = re.search(r"#" + re.escape(name) + r"(?![\w.-])", line)
    if not m:
        return None
    i = m.end()
    args = ""
    if i < len(line) and line[i] == "(":
        end = balance_at(line, i, "(", ")")
        if end == -1:
            return line[:m.start()] + render_fn(name, line[i + 1:], "")
        args = line[i + 1:end - 1]
        i = end
    body = ""
    if i < len(line) and line[i] == "[":
        end = balance_at(line, i, "[", "]")
        if end == -1:
            body = line[i + 1:]
            return line[:m.start()] + render_fn(name, args, body)
        body = line[i + 1:end - 1]
        i = end
    return line[:m.start()] + render_fn(name, args, body) + line[i:]


def drop_fn(line: str, name: str) -> str:
    r = replace_first_fn(line, name)
    return line if r is None else r


def image_md(args: str, body: str) -> str:
    """#image("p") / #figure(image("p"), caption: [c]) -> ![c](p)."""
    hay = args + "\x00" + body
    pm = re.search(r'["\']([^"\']+\.(?:png|jpe?g|gif|svg|webp))["\']', hay)
    path = pm.group(1) if pm else ""
    cm = re.search(r"caption:\s*\[(.*?)\]\s*[,)]", hay, re.S)
    cap = strip_labels(cm.group(1)).strip() if cm else ""
    cap = cap.replace("[", "\\[").replace("]", "\\]").replace("|", "\\|")
    return f"![{cap}]({path.replace(' ', '%20')})"


def table_md(s: str) -> str | None:
    """#table(columns: n, [a], [b], ...) -> Markdown-таблица."""
    cm = re.search(r"columns:\s*(\d+)", s)
    if not cm:
        return None
    ncol = int(cm.group(1))
    if ncol < 1:
        return None
    cells = [strip_labels(c).strip().replace("|", "\\|")
             for c in re.findall(r"\[([^\[\]]*)\]", s)]
    if not cells or len(cells) % ncol:
        return None
    rows = [cells[i:i + ncol] for i in range(0, len(cells), ncol)]
    out = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * ncol]
    for r in rows[1:]:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def fence(lang: str, code: str) -> str:
    """Ограда с гарантией пустых строк вокруг."""
    code = code.strip("\n")
    if not code:
        return ""
    return f"```{lang}\n{code}\n```"


def quote_block(text: str) -> str:
    """Многострочная цитата: каждая строка с "> ", пустые выкинуты."""
    return "\n".join("> " + ln.strip() for ln in text.splitlines()
                     if ln.strip())


def render_fn(name: str, args: str, body: str) -> str:
    """Markdown для одной Typst-функции."""
    if name == "link":
        url = args.strip().strip("\"'")
        text = wrap_bold(strip_labels(body)).strip()
        return f"[{text}]({url})" if text else f"<{url}>"
    if name in ("image", "figure"):
        return image_md(args, body)
    if name == "heading":
        lvl = re.search(r"level:\s*(\d+)", args)
        level = int(lvl.group(1)) if lvl else 1
        return "#" * min(level, 6) + " " + process_line(body).strip()
    if name == "codeblock" or name == "terminal":
        lang = (re.search(r'lang:\s*"(\w+)"', args)
                or re.search(r'"(\w+)"', args.strip()))
        return fence(lang.group(1) if lang else "text", body)
    if name == "resultblock":
        return fence("text", body)
    if name in ("yellowbox", "redbox"):
        inner = process_line(body).strip()
        label = "Note" if name == "yellowbox" else "Warning"
        return quote_block(f"**{label}:** {inner}") if inner else ""
    inner = process_line(body).strip()
    if name == "strong":
        return f"**{inner}**" if inner else ""
    if name == "emph":
        return f"*{inner}*" if inner else ""
    if name == "underline":
        return f"<u>{inner}</u>" if inner else ""
    if name == "strike":
        return f"~~{inner}~~" if inner else ""
    if name == "quote":
        return quote_block(inner) if inner else ""
    if name == "footnote":
        return f" (примечание: {inner})" if inner else ""
    # text / align / block / pad / box / par / highlight и неизвестные:
    if not inner and "image(" in args:
        return image_md(args, "")
    return inner


def process_line(line: str) -> str:
    """Инлайн-обработка строки: функции, математика, жирный, метки."""
    line = re.sub(r"#(?:emoji|sym)\.[\w.]+",
                  lambda m: SYM_MAP.get(m.group(0), ""), line)
    for name in ("figure", "image", "link", "heading", "footnote", "strong",
                 "emph", "underline", "strike", "quote", "highlight",
                 "codeblock", "terminal", "resultblock", "yellowbox",
                 "redbox", "text", "align", "block", "pad", "box", "par"):
        while True:
            new = replace_first_fn(line, name)
            if new is None:
                break
            line = new
    # неизвестные #func[...] -> разворачиваем содержимое
    line = re.sub(
        r"#[A-Za-z][\w.-]*\[((?:[^\[\]]|\[[^\[\]]*\])*)\]",
        lambda m: process_line(m.group(1)),
        line,
    )
    # неизвестные #func(...) без тела -> вырезаем
    line = re.sub(r"#[A-Za-z][\w.-]*\((?:[^()]|\([^()]*\))*\)", "", line)
    line = convert_inline_math(line)
    return wrap_bold(strip_labels(line))


# --- построчная конвертация документа ---

TERM_RE = re.compile(r"^(\s*)/\s+([^:]+):\s*(.*)$")
ENUM_RE = re.compile(r"^(\s*)\+\s+(.*)$")
LIST_RE = re.compile(r"^(\s*)-\s+(.*)$")
HEAD_RE = re.compile(r"^(=+) (.+)$")


def convert(text: str) -> str:
    out: list[str] = []
    in_raw = in_comment = in_math = paren_skip = False
    math_buf: list[str] = []
    skip_buf: list[str] = []
    enum_at: dict[int, int] = {}
    lines = text.splitlines()
    idx = 0

    while idx < len(lines):
        line = lines[idx]
        idx += 1

        # --- глобальные состояния ---
        if in_raw:
            out.append(line)
            if line.strip().startswith("```"):
                in_raw = False
            continue
        if in_comment:
            if "*/" in line:
                in_comment = False
            continue
        if in_math:
            if "$" in line:
                math_buf.append(line[:line.index("$")])
                out.append("$$" + typst_math_to_md("\n".join(math_buf)) + "$$")
                in_math, math_buf = False, []
            else:
                math_buf.append(line)
            continue
        if paren_skip:
            skip_buf.append(line)
            if depth_of("\n".join(skip_buf)) <= 0:
                paren_skip, skip_buf = False, []
            continue

        s = line.strip()

        # --- простые случаи ---
        if s.startswith("```"):
            in_raw = True
            out.append(line)
            continue
        if s.startswith("/*"):
            if "*/" not in s[2:]:
                in_comment = True
            continue
        if s.startswith("//"):
            continue
        if s == "$":
            in_math = True
            continue
        if s.startswith("$") and s.endswith("$") and len(s) > 1:
            out.append("$$" + typst_math_to_md(s[1:-1]) + "$$")
            continue

        # --- заголовок = / == / === ---
        hm = HEAD_RE.match(s)
        if hm:
            title = process_line(hm.group(2)).strip()
            out.append("#" * min(len(hm.group(1)), 6) + " " + title)
            continue

        # --- термин / term: definition ---
        tm = TERM_RE.match(line)
        if tm:
            indent, term, definition = tm.groups()
            out.append(f"{indent}- **{process_line(term).strip()}** — "
                       f"{process_line(definition).strip()}")
            continue

        # --- нумерованный список + item ---
        em = ENUM_RE.match(line)
        if em:
            indent = em.group(1)
            level = len(indent.expandtabs(4)) // 2
            for deeper in [k for k in enum_at if k > level]:
                enum_at[deeper] = 0
            enum_at[level] = enum_at.get(level, 0) + 1
            out.append(f"{indent}{enum_at[level]}. {process_line(em.group(2))}")
            continue
        if s:  # обычная строка сбивает нумерацию
            enum_at = {}

        # --- маркированный список - item ---
        lm = LIST_RE.match(line)
        if lm:
            out.append(f"{lm.group(1)}- {process_line(lm.group(2))}")
            continue

        # --- строки на #
        if s.startswith("#"):
            head = re.match(r"#([A-Za-z][\w.]*|\()(.*)$", s)
            fname = head.group(1) if head else ""
            base = fname.split(".")[-1] if fname else ""

            # preamble-строка: вырезается целиком; с незакрытыми скобками
            # едем до закрытия
            if fname and (base in PREAMBLE or fname == "("):
                if depth_of(s) > 0:
                    paren_skip, skip_buf = True, [line]
                continue
            if fname == "v" or fname == "h":
                continue

            if base in ("figure", "table", "grid"):
                full = s
                while depth_of(full) > 0 and idx < len(lines):
                    full += "\n" + lines[idx]
                    idx += 1
                if base == "figure":
                    out.append(image_md(full, ""))
                else:
                    md_t = table_md(full)
                    if md_t:
                        out.append(md_t)
                    else:
                        warn("таблица не разобрана (нужны columns: N и "
                             "клетки [..]) — оформи руками")
                continue
            if base == "quote" and s.count("[") > s.count("]"):
                buf = [line]
                while depth_of("".join(buf)) > 0 and idx < len(lines):
                    buf.append(lines[idx])
                    idx += 1
                joined = "\n".join(buf)
                r = replace_first_fn(joined, "quote")
                if r:
                    out.extend(l for l in r.splitlines() if l.strip())
                continue
            # любой другой #func(...)[...] с телом на несколько строк
            # (#align, свои обёртки) — собираем до баланса и конвертируем
            if s.count("[") > s.count("]"):
                buf = [line]
                while depth_of("".join(buf)) > 0 and idx < len(lines):
                    buf.append(lines[idx])
                    idx += 1
                out.append(process_line("\n".join(buf)))
                continue
            out.append(process_line(line))
            continue

        # --- обычная строка (Typst-\ в конце строки -> жёсткий перенос) ---
        out.append(process_line(re.sub(r"[ \t]*\\$", "  ", line)))

    if in_math and math_buf:
        out.append("$$" + typst_math_to_md("\n".join(math_buf)) + "$$")

    md = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", md).strip()


# --- шапка конспекта #align(right)[...] с полями *Ключ:* значение ---

META_LINE = re.compile(r"^\s*\*([^*]+):\*\s*(.*?)\s*\\?\s*$")
META_OPEN = re.compile(r"^\s*#align\(\s*(?:right|center|left)\s*\)\[")


def extract_meta(text: str) -> tuple[str, dict[str, str]]:
    """Вынуть первый #align(...)[...] с полями *Ключ:* значение.

    Возвращает (текст без этого блока, словарь полей). Если полей меньше
    двух — это контентная выравнивалка, возвращаем текст как был."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not META_OPEN.match(line):
            continue
        buf = [line]
        j = i
        while depth_of("\n".join(buf)) > 0 and j + 1 < len(lines):
            j += 1
            buf.append(lines[j])
        inner_start = "\n".join(buf).find("[")
        inner = "\n".join(buf)[inner_start + 1:].rstrip("]").rstrip()
        fields = {}
        for ln in inner.splitlines():
            m = META_LINE.match(ln)
            if m:
                key = m.group(1).strip()
                fields[key] = m.group(2).strip()
        if len(fields) >= 2:  # это шапка, не контент
            rest = lines[:i] + lines[j + 1:]
            return "\n".join(rest), fields
        break  # align без полей — обычный контент, дальше не ищем
    return text, {}


def is_stub(text: str) -> bool:
    """Заглушка README: маркер шаблона, строки-заполнители или черновик без контента."""
    if "конвертировано из" in text:  # продукт конвертера — не заглушка
        return False
    if "<!-- stub" in text:  # маркер из templates/writeup-README.md
        return True
    stripped = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    lines = [ln.strip() for ln in stripped.splitlines() if ln.strip()]
    if sum(1 for ln in lines if PLACEHOLDER_RE.fullmatch(ln)) >= 2:
        return True
    if not DRAFT_MARK_RE.search(stripped):
        return False
    # маркер черновика есть: заглушка, если за таблицей и заголовками нет
    # содержательного текста (подсказки шаблона контентом не считаются)
    prose = [ln for ln in lines
             if not ln.startswith(("#", "|", ">"))
             and not PLACEHOLDER_RE.fullmatch(ln)]
    words = sum(len(ln.split()) for ln in prose)
    hint_words = sum(len(ln.split()) for ln in prose if STUB_HINT_RE.search(ln))
    return max(words - hint_words, 0) < 40


# --- шапка райтапа ---

def event_of(rel_path: Path) -> tuple[str, str]:
    """(событие, категория) из пути solarctf-2026/Web/ssti1/notes.typ."""
    parts = rel_path.parts[:-1]
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from generate_index import event_title
        event = event_title(parts[0]) if parts else "—"
    except Exception:
        event = parts[0].replace("-", " ").capitalize() if parts else "—"
    category = parts[1] if len(parts) > 1 else "—"
    return event, category


def header_table(rel_path: Path, status: str, date: str,
                 meta: dict[str, str] | None = None) -> str:
    meta = meta or {}
    event, category = event_of(rel_path)
    category = meta.get("Категория") or category
    difficulty = meta.get("Сложность") or "—"
    date = meta.get("Дата") or date
    return (
        "| | |\n"
        "|---|---|\n"
        f"| **Платформа / Событие** | {event} |\n"
        f"| **Категория** | {category} |\n"
        f"| **Сложность** | {difficulty} |\n"
        f"| **Статус** | {status} |\n"
        f"| **Дата решения** | {date} |\n"
        "| **Ссылка на таск** | — |\n"
    )


# --- сбор и конвертация ---

STATUS_CELL_RE = re.compile(r"(\|\s*\**\s*Статус\s*\**\s*\|\s*)([^|]*?)(\s*\|)")


def mark_done(rp: Path) -> tuple[str, str]:
    """draft -> done в строке «Статус» шапки README.

    Возвращает (результат, сообщение): done/clean/index/stub/nomark/partial."""
    text = rp.read_text(encoding="utf-8", errors="replace")
    if not DRAFT_MARK_RE.search(text):
        return "clean", ""
    outside = strip_index_blocks(text)
    if not DRAFT_MARK_RE.search(outside):
        return "index", ""  # папка-индекс: черновик-слова только в автотаблицах
    if is_stub(outside):
        return "stub", "заглушка без контента — сначала перенеси текст из .typ"
    new, n = STATUS_CELL_RE.subn(
        lambda m: m.group(1) + "done" + m.group(3), text, count=1)
    if not n:
        return "nomark", "не нашёл строку «Статус» в таблице шапки — поправь руками"
    rest = re.sub(r"^\|.*Статус.*$", "", new, flags=re.M)
    rp.write_text(new, encoding="utf-8", newline="\n")
    if DRAFT_MARK_RE.search(rest):
        return "partial", "статус проставлен, но маркер черновика остался в тексте — глянь"
    return "done", ""


def find_typ(pattern: str | None) -> list[Path]:
    files = []
    for p in ROOT.rglob("*.typ"):
        rel = p.relative_to(ROOT)
        if any(part in EXCLUDE or part.startswith(".") for part in rel.parts):
            continue
        if len(rel.parts) == 1:  # .typ в корне репо — не конспект таска
            continue
        if p.stem.lower().startswith("template"):
            continue
        if pattern and not fnmatch.fnmatch(rel.as_posix(), pattern):
            continue
        files.append(p)
    return sorted(files)


def convert_file(src: Path, status: str, date: str) -> str:
    text = src.read_text(encoding="utf-8-sig")
    rel = src.relative_to(ROOT)
    text, meta = extract_meta(text)
    title = meta.get("Задание")
    if title:
        # первый = -заголовок (типа «= WriteUp: PICO-CTF») дублирует
        # название задания — убираем, титулом станет само задание
        text = re.sub(r"^= .*$(\n)?", "", text, count=1, flags=re.M)
    body = convert(text)
    if not body.startswith("# "):
        body = f"# {title or src.parent.name}\n\n" + body
    md = (PROVENANCE.format(src.stem) + "\n\n"
          + header_table(rel, status, date, meta) + "\n" + body + "\n")
    # остатки непереваренной Typst-разметки — сигнализируем
    for leftover in sorted(set(re.findall(r"#[A-Za-z][\w.]*[\[(]", md)))[:3]:
        warn(f"не конвертировалось: {leftover}... — проверь {rel}")
    if re.search(r"^]$", md, re.M):
        warn(f"одинокая «]» в выводе — проверь {rel}")
    return md


def main() -> int:
    ap = argparse.ArgumentParser(description="Typst конспект -> README.md райтапа")
    ap.add_argument("pattern", nargs="?", default=None,
                    help="маска файлов относительно корня репо (по умолчанию все *.typ)")
    ap.add_argument("--status", default="draft", choices=["draft", "done"],
                    help="статус в шапке README (по умолчанию draft)")
    ap.add_argument("--date", default="—", help="дата решения для шапки")
    ap.add_argument("--force", action="store_true",
                    help="перезаписать любой существующий README.md")
    ap.add_argument("--no-stubs", action="store_true",
                    help="не заменять существующие README вовсе (старое поведение)")
    ap.add_argument("--dry-run", action="store_true", help="не писать файлы")
    ap.add_argument("--list", action="store_true",
                    help="показать *.typ и что будет сделано, без записи")
    ap.add_argument("--mark-done", action="store_true",
                    help="пометить готовое: «Статус» в шапке README draft -> done "
                         "(заглушки не трогаются, конвертация не запускается)")
    args = ap.parse_args()

    if args.list:
        files = find_typ(args.pattern)
        print(f"Найдено конспектов *.typ: {len(files)}")
        counts: dict[str, int] = {}
        for p in files:
            rel = p.relative_to(ROOT).as_posix()
            target = p.parent / "README.md"
            if not target.exists():
                act = "создам README"
            elif args.force:
                act = "заменю README (--force)"
            else:
                old = target.read_text(encoding="utf-8", errors="replace")
                act = ("заменю черновик-README" if DRAFT_MARK_RE.search(old)
                       else "пропущу (README готов, не черновик)")
            counts[act] = counts.get(act, 0) + 1
            print(f"  [{act}] {rel}")
        for act, n in counts.items():
            print(f"  итого — {act}: {n}")
        if not files:
            print("  *.typ не нашлись. Проверь по порядку:")
            print("  1. Скрипт запущен из корня репо (рядом лежат папки portswigger/, solarctf-2026/...)?")
            print("  2. Есть ли *.typ вообще:  Get-ChildItem -Recurse -Filter *.typ | Select-Object FullName")
            print("  3. Не ищем только в: tools/, templates/, скрытых папках, корне репо; template*.typ пропускается")
        return 0

    if args.mark_done:
        n_done = n_stub = n_index = n_warn = 0
        for rp in sorted(ROOT.rglob("README.md")):
            if rp == ROOT / "README.md":
                continue  # корневой дашборд — не райтап
            parts = rp.relative_to(ROOT).parts
            if any(part in EXCLUDE or part.startswith(".") for part in parts):
                continue
            if args.pattern and not fnmatch.fnmatch(
                    rp.relative_to(ROOT).as_posix(), args.pattern):
                continue
            res, msg = mark_done(rp)
            rel = rp.relative_to(ROOT).as_posix()
            if res == "done":
                n_done += 1
                print(f"  done: {rel}")
            elif res == "stub":
                n_stub += 1
            elif res == "index":
                n_index += 1
            elif res in ("nomark", "partial"):
                n_warn += 1
                print(f"  ! {rel}: {msg}")
        print(f"\nПометлено done: {n_done}, заглушек пропущено: {n_stub}"
              + (f", индексов пропущено: {n_index}" if n_index else "")
              + (f", с оговорками: {n_warn}" if n_warn else ""))
        print("Дальше: python tools/generate_index.py — пересчитает дашборд из статусов.")
        return 0

    files = find_typ(args.pattern)
    if not files:
        print("Конспектов *.typ не найдено.")
        return 0

    done_n = skip_n = 0
    for src in files:
        rel = src.relative_to(ROOT).as_posix()
        target = src.parent / "README.md"
        note = "готово"
        if target.exists() and not args.force:
            old = target.read_text(encoding="utf-8", errors="replace")
            if args.no_stubs:
                print(f"  пропущено (README уже есть): {rel}")
                skip_n += 1
                continue
            if not DRAFT_MARK_RE.search(old):
                print(f"  пропущено (README готов, не черновик; замена — --force): {rel}")
                skip_n += 1
                continue
            note = ("заглушка заменена" if is_stub(old)
                    else "черновик README заменён из .typ")
        md = convert_file(src, args.status, args.date)
        if args.dry_run:
            print(f"  [dry-run] {note}: запишу {len(md.splitlines())} строк -> "
                  f"{target.relative_to(ROOT).as_posix()}")
        else:
            target.write_text(md, encoding="utf-8", newline="\n")
            print(f"  {note}: {rel} -> README.md")
        done_n += 1

    print(f"\nКонвертировано: {done_n}, пропущено: {skip_n}")
    if WARNINGS:
        print("Замечания (проверь в готовых README):")
        for wtext in WARNINGS:
            print(f"  - {wtext}")
    if args.status == "draft":
        print("Статусы поставлены draft. Пометить готовое:"
              " python tools/typ2readme.py --mark-done (или конвертируй с --status done).")
    print("Дальше: python tools/generate_index.py — пересчитает дашборд из статусов.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
