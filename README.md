# ctf-writeups

Public practice log in offensive security: walkthroughs of labs and machines with
theory notes. Every writeup contains **what I did**, **why it worked** and
**how to defend against it**.

> Автор: **nedo-offsec** · МАИ · offensive security (pentest / red team / RE)
> GitHub: [disaster-offsec](https://github.com/disaster-offsec)

---

## Stats

- **Platforms:** PortSwigger Academy, HackTheBox, picoCTF Trainings
- **CTF events:** SOLAR CTF 2026, Кубок CTF 2026, AvitoCTF 2026 (SecondLayer / NEDO-OFFSEC)
- **50+ writeups** · 7 web-classes closed on PortSwigger · HTB season machines

---

## Structure

```
ctf-writeups/
├── portswigger/          # PortSwigger Academy — по классам уязвимостей
│   ├── sqli/             #   NN-slug/ = одна лаба: README + EXPLANATION + figN.png
│   ├── xss/
│   ├── csrf/
│   ├── access-control/
│   ├── ssrf/
│   ├── xxe/
│   └── path-traversal/
├── hackthebox/           # HTB — по машинам
├── picoctf-trainings/    # picoCTF Trainings — по категориям
├── avitoctf-2026/        # CTF-события: <event>-<year>
├── kubok-ctf-2026/
├── solarctf-2026/
├── bootcamp/             # учебные треки
└── others/               # разрозненные задачи
```

## PortSwigger Academy

| Class | Labs | Path |
|-------|------|------|
| SQL Injection | n | [portswigger/sqli](portswigger/sqli/) |
| Cross-Site Scripting | n | [portswigger/xss](portswigger/xss/) |
| Cross-Site Request Forgery | 5 | [portswigger/csrf](portswigger/csrf/) |
| Access Control | n | [portswigger/access-control](portswigger/access-control/) |
| SSRF | n | [portswigger/ssrf](portswigger/ssrf/) |
| XXE | n | [portswigger/xxe](portswigger/xxe/) |
| Path Traversal | n | [portswigger/path-traversal](portswigger/path-traversal/) |

*Каждый класс — конспект теории (`README.md`: что это, 3 условия атаки, защиты,
почему защита ломается) + нумерованные лабы `NN-slug/` с полным прохождением.*

## HackTheBox

Machines: [hackthebox/](hackthebox/) — starting point -> season machines.
Каждая машина: разведка -> foothold -> privilege escalation → **why it worked**.

## CTF events

| Event | Team | Writeups |
|-------|------|----------|
| SOLAR CTF 2026 | SecondLayer | [solarctf-2026/](solarctf-2026/) |
| Кубок CTF 2026 | SecondLayer | [kubok-ctf-2026/](kubok-ctf-2026/) |
| AvitoCTF 2026 (HoneyBadger) | NEDO-OFFSEC | [avitoctf-2026/](avitoctf-2026/) |

---

## Conventions

- Имя лабы: `NN-краткое-имя` внутри папки класса/события.
- Одна лаба = `README.md` (прохождение) + `EXPLANATION.md` (теория) + `figN.png`.
- В каждом райтапе есть секция **Why it works** — ментальная модель уязвимости,
  а не только последовательность команд.
- Коммиты: `[<класс>|<платформа>] суть`; служебные: `docs:`, `chore:`, `fix:`.

## New writeup

```
./tools/new_writeup.sh portswigger/csrf 06-csrf-referrer-validation "CSRF where Referer validation is bypassed"
python3 tools/generate_index.py   # обновить индексные таблицы
```

---

<!-- INDEX:START -->
## PortSwigger Academy

### portswigger

| Class          | Labs | Last commit | Path                       |
|----------------|------|-------------|----------------------------|
| access-control | 3    | 2026-11-18  | portswigger/access-control |
| csrf           | 6    | 2026-11-18  | portswigger/csrf           |
| path-traversal | 1    | 2026-10-26  | portswigger/path-traversal |
| sqli           | 11   | 2026-11-18  | portswigger/sqli           |
| ssrf           | 3    | 2026-10-26  | portswigger/ssrf           |
| xss            | 5    | 2026-11-18  | portswigger/xss            |
| xxe            | 1    | 2026-10-26  | portswigger/xxe            |

## CTF events

### avitoctf-2026

| Writeup         | Files | Last commit | Path                          |
|-----------------|-------|-------------|-------------------------------|
| Сопромёд: метро | 5     | 2026-11-18  | avitoctf-2026/sopromyod-metro |

### kubok-ctf-2026

| Writeup                                     | Files | Last commit | Path                        |
|---------------------------------------------|-------|-------------|-----------------------------|
| burmalda                                    | 2     | 2026-11-18  | kubok-ctf-2026/burmalda     |
| compuuuter — writeup                        | 10    | 2026-11-18  | kubok-ctf-2026/computer     |
| connecttome                                 | 3     | 2026-11-18  | kubok-ctf-2026/connecttome  |
| Электронный журнал — райтап (web, 1000 pts) | 29    | 2026-11-18  | kubok-ctf-2026/eljournal    |
| image-viewer                                | 2     | 2026-11-18  | kubok-ctf-2026/image-viewer |
| MeowSim: Schrödinger E... — райтап          | 3     | 2026-11-18  | kubok-ctf-2026/meow-sim     |
| Райтап: реверс-инжиниринг задания mmm       | 8     | 2026-11-18  | kubok-ctf-2026/mmm          |
| my-own-fs                                   | 6     | 2026-11-18  | kubok-ctf-2026/my-own-fs    |
| Weird RSA — райтап                          | 5     | 2026-11-18  | kubok-ctf-2026/weird-rsa    |

### solarctf-2026

| Writeup                                     | Files | Last commit | Path                                       |
|---------------------------------------------|-------|-------------|--------------------------------------------|
| Writeup — Kommunalki (web)                  | 1     | 2026-11-18  | solarctf-2026/_unsorted/kommunalki         |
| Невероятная утка                            | 1     | 2026-11-18  | solarctf-2026/_unsorted/neveroyatnaya-utka |
| Нейропитомец                                | 1     | 2026-11-18  | solarctf-2026/_unsorted/neyropitomets      |
| Новый телефон                               | 1     | 2026-11-18  | solarctf-2026/_unsorted/novyy-telefon      |
| Out of frame — Майя                         | 1     | 2026-11-18  | solarctf-2026/_unsorted/out-of-frame       |
| PBX «Солярис-3» — разбор ночного дампа      | 1     | 2026-11-18  | solarctf-2026/_unsorted/pbx-sabotage       |
| Что было в архиве                           | 1     | 2026-11-18  | solarctf-2026/_unsorted/poslednee-delo     |
| Пустота — решение                           | 1     | 2026-11-18  | solarctf-2026/_unsorted/pustota            |
| Шах и мат                                   | 1     | 2026-11-18  | solarctf-2026/_unsorted/shakh-i-mat        |
| Writeup — Zero Report (SolarCTF 2026)       | 5     | 2026-11-18  | solarctf-2026/crypto/0-report              |
| Writeup — Пропавший архив (SolarCTF 2026)   | 5     | 2026-11-18  | solarctf-2026/crypto/lostarch              |
| Writeup — РакушкаBreach (SolarCTF 2026)     | 2     | 2026-11-18  | solarctf-2026/forensics/breach             |
| Writeup — Локпик / Lockpick (SolarCTF 2026) | 5     | 2026-11-18  | solarctf-2026/misc/lockpick                |
| Writeup — Вентилятор303 (SolarCTF 2026)     | 2     | 2026-11-18  | solarctf-2026/misc/vent303                 |
| Writeup — Ткач / Weaver (SolarCTF 2026)     | 10    | 2026-11-18  | solarctf-2026/reverse/tkach                |
| Writeup — Vintage Bank (SolarCTF 2026)      | 2     | 2026-11-18  | solarctf-2026/web/vintage_bank             |

## Platforms & trainings

### bootcamp

| Writeup                                                             | Files | Last commit | Path                     |
|---------------------------------------------------------------------|-------|-------------|--------------------------|
| infra-1                                                             | 2     | 2026-10-24  | bootcamp/7/infra-1       |
| infra                                                               | 7     | 2026-10-25  | bootcamp/7/infra-2       |
| infra-3                                                             | 1     | 2026-10-25  | bootcamp/7/infra-3       |
| [infra-4] Внутренняя разведка (Active Directory)                    | 3     | 2026-10-25  | bootcamp/7/infra-4       |
| [infra-5] Получение доступа к компьютеру сотрудника HR-департамента | 1     | 2026-10-25  | bootcamp/7/infra-5       |
| [infra-6] Получите доступ к компьютеру сотрудника HR-департамента   | 2     | 2026-10-25  | bootcamp/7/infra-6       |
| Отчёт по задачам web-1-1 -- RCE на узле library.edu.stf             | 2     | 2026-11-18  | bootcamp/7/web-1/web-1-1 |
| Райтап: Standoff 365 Bootcamp — Web-1-2 (CVE-2023-4911)             | 3     | 2026-11-18  | bootcamp/7/web-1/web-1-2 |
| Отчёт по задачам web-2-1 -- LFI на узле www.edu.stf                 | 1     | 2026-11-18  | bootcamp/7/web-2/1       |
| web-2-2: RCE. Write-Up                                              | 1     | 2026-11-18  | bootcamp/7/web-2/2       |

### flare-on

| Writeup       | Files | Last commit | Path                                  |
|---------------|-------|-------------|---------------------------------------|
| Flare-On 2014 | 17    | 2026-11-18  | flare-on/2014/2014_FLAREOn_Challenges |

### hackthebox

| Writeup    | Files | Last commit | Path                  |
|------------|-------|-------------|-----------------------|
| Cohort     | 4     | 2026-11-13  | hackthebox/cohort     |
| Dancing    | 1     | 2026-10-23  | hackthebox/dancing    |
| DoubleTake | 3     | 2026-11-16  | hackthebox/doubletake |
| Fawn       | 1     | 2026-10-23  | hackthebox/fawn       |
| Management | 1     | 2026-11-18  | hackthebox/management |
| Meow       | 1     | 2026-10-23  | hackthebox/meow       |

### others

| Writeup                     | Files | Last commit | Path   |
|-----------------------------|-------|-------------|--------|
| WRITEUPS FROM OTHERS PEOPLE | 9     | 2026-11-18  | others |

### picoctf-trainings

| Writeup                      | Files | Last commit | Path                                                    |
|------------------------------|-------|-------------|---------------------------------------------------------|
| bookmarklet                  | 3     | 2026-11-18  | picoctf-trainings/web/easy/bookmarklet                  |
| cookie-monster-secret-recipe | 3     | 2026-11-18  | picoctf-trainings/web/easy/cookie-monster-secret-recipe |
| cookies                      | 3     | 2026-11-18  | picoctf-trainings/web/easy/cookies                      |
| crack-the-gate               | 3     | 2026-11-18  | picoctf-trainings/web/easy/crack-the-gate               |
| dont-use-client-side         | 4     | 2026-11-18  | picoctf-trainings/web/easy/dont-use-client-side         |
| get-ahead                    | 3     | 2026-11-18  | picoctf-trainings/web/easy/get-ahead                    |
| heap-dump                    | 4     | 2026-11-18  | picoctf-trainings/web/easy/heap-dump                    |
| includes                     | 4     | 2026-11-18  | picoctf-trainings/web/easy/includes                     |
| inspect-html                 | 3     | 2026-11-18  | picoctf-trainings/web/easy/inspect-html                 |
| inspect-me                   | 3     | 2026-11-18  | picoctf-trainings/web/easy/inspect-me                   |
| introtoburp                  | 3     | 2026-11-18  | picoctf-trainings/web/easy/introtoburp                  |
| local-authority              | 3     | 2026-11-18  | picoctf-trainings/web/easy/local-authority              |
| logon                        | 3     | 2026-11-18  | picoctf-trainings/web/easy/logon                        |
| n0s4n1ty-1                   | 4     | 2026-11-18  | picoctf-trainings/web/easy/n0s4n1ty-1                   |
| scavenger-hunt               | 3     | 2026-11-18  | picoctf-trainings/web/easy/scavenger-hunt               |
| ssti1                        | 3     | 2026-11-18  | picoctf-trainings/web/easy/ssti1                        |
| unminify                     | 3     | 2026-11-18  | picoctf-trainings/web/easy/unminify                     |
| webdecode                    | 3     | 2026-11-18  | picoctf-trainings/web/easy/webdecode                    |
| where-are-the-robots         | 3     | 2026-11-18  | picoctf-trainings/web/easy/where-are-the-robots         |
| hashgate                     | 6     | 2026-11-18  | picoctf-trainings/web/medium/hashgate                   |
| nofa                         | 7     | 2026-11-18  | picoctf-trainings/web/medium/nofa                       |
| secret-box                   | 20    | 2026-11-18  | picoctf-trainings/web/medium/secret-box                 |

<!-- INDEX:END -->
