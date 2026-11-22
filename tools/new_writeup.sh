#!/usr/bin/env bash
# Создаёт каркас новой лабы из шаблонов.
#
# Usage:
#   ./tools/new_writeup.sh <класс-или-событие> <NN-slug> "Название таска"
#
# Примеры:
#   ./tools/new_writeup.sh portswigger/ssrf 01-ssrf-basic "Basic SSRF against the local server"
#   ./tools/new_writeup.sh hackthebox 06-machine-name "Machine Name"
set -euo pipefail

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <класс> <NN-slug> \"Название\""
    echo "Пример: $0 portswigger/csrf 06-csrf-referrer-validation \"CSRF with Referer validation\""
    exit 1
fi

CLASS="$1"; SLUG="$2"; TITLE="$3"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="$ROOT/$CLASS/$SLUG"
TPL="$ROOT/templates"

if [ ! -d "$ROOT/$CLASS" ]; then
    echo "Папка $CLASS не существует — создаю."
    mkdir -p "$ROOT/$CLASS"
fi
if [ -e "$TARGET" ]; then
    echo "Ошибка: $TARGET уже существует."; exit 1
fi
if [ ! -f "$TPL/writeup-README.md" ]; then
    echo "Ошибка: не найден шаблон $TPL/writeup-README.md"; exit 1
fi

mkdir -p "$TARGET"
DATE="$(date +%d.%m.%Y)"

sed -e "s|{{TITLE}}|$TITLE|g" \
    -e "s|{{CLASS}}|$CLASS|g" \
    -e "s|{{DATE}}|$DATE|g" \
    "$TPL/writeup-README.md" > "$TARGET/README.md"

sed -e "s|{{TITLE}}|$TITLE|g" \
    -e "s|{{CLASS}}|$CLASS|g" \
    -e "s|{{DATE}}|$DATE|g" \
    "$TPL/writeup-EXPLANATION.md" > "$TARGET/EXPLANATION.md"

echo "Создано: $TARGET/README.md"
echo "Создано: $TARGET/EXPLANATION.md"
echo ""
echo "Дальше:"
echo "  1. Заполни TL;DR, Steps, Why it works, Defense"
echo "  2. Скрины — fig1.png, fig2.png, ... рядом с README"
echo "  3. Когда райтап дописан — в шапке замени Статус draft на done,"
echo "     иначе он вечно числится черновиком в индексах"
echo "  4. python3 tools/generate_index.py   # обновить индексы"
echo "  5. git add -A && git commit -m \"[$(basename "$CLASS")] $TITLE\""
