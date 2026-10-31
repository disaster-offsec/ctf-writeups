#!/usr/bin/env bash
# Локальный стенд таска 'Электронный журнал' — для тренировки/перепроверки.
# Использование:  bash setup_local_lab.sh [путь/к/uroki.zip]
set -e

ZIP="${1:-/home/z/my-project/upload/uroki.zip}"
LAB="${LAB:-/tmp/uroki_test}"

echo "[*] lab dir: $LAB"
rm -rf "$LAB"
mkdir -p "$LAB"
cd "$LAB"

echo "[*] extracting $ZIP"
unzip -qo "$ZIP" -d .
# архив распаковывается в подкаталог uroki/ — поднимаем содержимое наверх
if [ -d uroki ]; then
    cp -a uroki/. .
    rm -rf uroki
fi

echo "[*] patching hardcoded paths -> $LAB"
sed -i "s|DATA_DIR = \"/data\"|DATA_DIR = \"$LAB/data\"|" app/db.py
sed -i "s|UPLOAD_DIR = \"/data/uploads\"|UPLOAD_DIR = \"$LAB/data/uploads\"|" app/web.py
sed -i "s|MQ_DIR = \"/data/mq\"|MQ_DIR = \"$LAB/data/mq\"|" app/tasks.py

mkdir -p data/uploads data/mq
echo "[*] init db (как это делает entrypoint.sh)"
python3 -c "import sys; sys.path.insert(0, '$LAB'); from app import db; db.init_db(); print('db ok')"

echo "[*] готово. Запуск приложения:"
echo "    python3 uroki_local_run.py        # http://127.0.0.1:5099"
echo "    (в другом терминале) python3 uroki_exploit.py http://127.0.0.1:5099 $LAB/data/SECRET_FLAG.txt $LAB/data/uroki.db"
