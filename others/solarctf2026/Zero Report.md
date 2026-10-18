# Zero Report — writeup

**Флаг:** `SOLARCTF{y0u_h4sh3d_th3_wr0ng_th1ng}`
**Сервер:** `nc solarctf.ru 30102` · **Категория:** crypto/quiz

## Условие
«Если аудитор одобряет программу, в её отчёте точно одни нули». Нужно добиться одобрения для ненулевого отчёта.

## Уязвимость
Сервис парсит каноническую программу-обёртку, ограниченным оценщиком вычисляет отчёт `(a, b)` и одобряет программу, если:

```
0 <= a < P, 0 <= b < P, (a != 0 or b != 0),
(1 - h) * a + h * b ≡ 0 (mod P),   h = sha256(source) % P,  P = 2**127 - 1
```

1. **Легенда ложная:** проверка `(a != 0 or b != 0)` отвергает нулевой отчёт — одобряются только ненулевые.
2. **Условие — линейное уравнение** с двумя неизвестными; нулевое решение лишь одно из бесконечного семейства.
3. Оценщик поддерживает `H(SOURCE)` и возвращает ровно то самое `h`, которое использует audit, поэтому фиксированную точку хеша искать не нужно — `h` доступно как символ.

## Решение
`a = h`, `b = (h - 1) mod P`: `(1-h)·h + h·(h-1) ≡ 0` — тождество при любом `h` (включая 0 и 1).

Тело `generate()`:

```python
h = H(SOURCE)
return [h, (h - 1) % P]
```

`SOURCE` — исходник программы целиком; `H` считает `sha256` по модулю `P`. Обёртка подставляет `repr` исходника в `SOURCE` (самоссылочность честная, в этом и суть задумки автора).

## Воспроизведение

Тело выше вставляется в каноническую обёртку (модуль с `P`, `H`, `SOURCE` и `generate()`); локальный запуск печатает `Report: [h, h-1]` и `ACCEPT`. Собранную обёртку сохранить рядом как `program.py` — скрипт отправки ниже читает её. Отправка — base64 одной строкой на сервис:

```python
import base64
import socket
import sys

HOST, PORT = "solarctf.ru", 30102

with open("program.py", "rb") as fh:
    source = fh.read()
line = base64.b64encode(source).decode()
assert len(line) <= 21848, "transport line too long"

with socket.create_connection((HOST, PORT), timeout=30) as sock:
    buf = b""
    while not buf.endswith(b"> "):
        chunk = sock.recv(4096)
        if not chunk:
            break
        buf += chunk
    sys.stdout.write(buf.decode(errors="replace"))
    sock.sendall((line + "\n").encode())
    resp = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        resp += chunk
print()
print("RESPONSE:", resp.decode(errors="replace"))
```

Локальная проверка (до отправки): программа печатает `Report: [h, h-1]`, аудитор отвечает `ACCEPT`. После отправки сервис возвращает флаг.

## Вывод
Автор тестировал только нулевые отчёты; аудитора следовало проверять на *любые* отчёты, проходящие линейную проверку. Линейность + самореферентный `H(SOURCE)` = тривиальный обход.

## Флаг

```text
SOLARCTF{y0u_h4sh3d_th3_wr0ng_th1ng}
```
