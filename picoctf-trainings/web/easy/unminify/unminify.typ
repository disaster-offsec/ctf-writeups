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
  *Задание:* Unminify \
  *Категория:* Web \
  *Сложность:* Easy 100 pts
]

== Задание

I don't like scrolling down to read the code of my website, so I've squished it. As a bonus, my pages load faster!

== Решение

Ну и рофл, просто открывает devtools:network

и смотрим содержимое titan.picoctf.net

```html
<!doctype html>
<html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>picoCTF - picoGym | Unminify Challenge</title>
        <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
        <style>
            body {
                font-family: "Lucida Console",Monaco,monospace
            }

            h1,p {
                color: #000
            }
        </style>
    </head>
    <body class="picoctf{}" style="margin:0">
        <div class="picoctf{}" style="margin:0;padding:0;background-color:#757575;display:auto;height:40%">
            <a class="picoctf{}" href="/">
                <img src="picoctf-logo-horizontal-white.svg" alt="picoCTF logo" style="display:inline-block;width:160px;height:90px;padding-left:30px">
            </a>
        </div>
        <center>
            <br class="picoctf{}">
            <br class="picoctf{}">
            <div class="picoctf{}" style="padding-top:30px;border-radius:3%;box-shadow:0 5px 10px #0000004d;width:50%;align-self:center">
                <img class="picoctf{}" src="hero.svg" alt="flag art" style="width:150px;height:150px">
                <div class="picoctf{}" style="width:85%">
                    <h2 class="picoctf{}">Welcome to my flag distribution website!</h2>
                    <div class="picoctf{}" style="width:70%">
                        <p class="picoctf{}">If you're reading this, your browser has succesfully received the flag.</p>
                        <p class="picoCTF{pr3tty_c0d3_dbe259ce}"></p>
                        <p class="picoctf{}">I just deliver flags, I don't know how to read them...</p>
                    </div>
                </div>
                <br class="picoctf{}">
            </div>
        </center>
    </body>
</html>
```

ну и фигня)
