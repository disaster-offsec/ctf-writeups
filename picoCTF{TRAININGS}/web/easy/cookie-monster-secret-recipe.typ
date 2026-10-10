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
  *Задание:* Cookie Monster Secret Recipe \
  *Категория:* Web \
  *Сложность:* Easy 50 pts
]

== Задание

Cookie Monster has hidden his top-secret cookie recipe somewhere on his website. As an aspiring cookie detective, your mission is to uncover this delectable secret. Can you outsmart Cookie Monster and find the hidden recipe?

== Решение

Вводим любой логин и пароль, проваливаемя на страничку с Access Denied.

Затем просто берем cookie из DevTools

```text
secret_recipe:cGljb0NURntjMDBrMWVfbTBuc3Rlcl9sMHZlc19jMDBraWVzXzJDODA0MEVGfQ%3D%3D
```

Затем прогоняем в base64 -d:

```bash
echo cGljb0NURntjMDBrMWVfbTBuc3Rlcl9sMHZlc19jMDBraWVzXzJDODA0MEVGfQ%3D%3D | base64 -d

picoCTF{c00k1e_m0nster_l0ves_c00kies_2C8040EF}
```


