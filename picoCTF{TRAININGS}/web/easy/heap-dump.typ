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
  *Задание:* head-dump \
  *Категория:* Web \
  *Сложность:* Easy 50 pts
]

== Задание

Welcome to the challenge! In this challenge, you will explore a web application and find an endpoint that exposes a file containing a hidden flag.

The application is a simple blog website where you can read articles about various topics, including an article about API Documentation. Your goal is to explore the application and find the endpoint that generates files holding the server’s memory, where a secret flag is hidden.

== Решение

cначала находим папку api-docs, неважно фаззингом или ручками, затем находим функцию heapdump,
затем, качаем файл и выводим флаг

```bash
cat heapdump-1784483276876.heapsnapshot | grep "picoCTF" | less
```
