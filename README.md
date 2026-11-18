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
| access-control | -    | -           | portswigger/access-control |
| csrf           | 6    | 2026-11-18  | portswigger/csrf           |
| path-traversal | 1    | 2026-10-26  | portswigger/path-traversal |
| sqli           | 6    | 2026-11-08  | portswigger/sqli           |
| ssrf           | 3    | 2026-10-26  | portswigger/ssrf           |
| xss            | -    | -           | portswigger/xss            |
| xxe            | 1    | 2026-10-26  | portswigger/xxe            |

## CTF events

### avitoCTF2026

| Writeup | Files | Last commit | Path |
|---------|-------|-------------|------|

### kubok-ctf2026

| Writeup                                     | Files | Last commit | Path                    |
|---------------------------------------------|-------|-------------|-------------------------|
| compuuuter — writeup                        | 10    | 2026-10-31  | kubok-ctf2026/computer  |
| Электронный журнал — райтап (web, 1000 pts) | 29    | 2026-10-31  | kubok-ctf2026/eljournal |
| MeowSim: Schrödinger E... — райтап          | 3     | 2026-10-31  | kubok-ctf2026/meow-sim  |
| Райтап: реверс-инжиниринг задания mmm       | 8     | 2026-10-31  | kubok-ctf2026/mmm       |
| Weird RSA — райтап                          | 5     | 2026-10-31  | kubok-ctf2026/weird-rsa |

### picoCTF{TRAININGS}

| Writeup | Files | Last commit | Path |
|---------|-------|-------------|------|

### solarctf2026

| Writeup | Files | Last commit | Path |
|---------|-------|-------------|------|

## Platforms & trainings

### bootcamp

| Writeup                                                             | Files | Last commit | Path               |
|---------------------------------------------------------------------|-------|-------------|--------------------|
| infra-1                                                             | 2     | 2026-10-24  | bootcamp/7/infra-1 |
| infra                                                               | 7     | 2026-10-25  | bootcamp/7/infra-2 |
| infra-3                                                             | 1     | 2026-10-25  | bootcamp/7/infra-3 |
| [infra-4] Внутренняя разведка (Active Directory)                    | 3     | 2026-10-25  | bootcamp/7/infra-4 |
| [infra-5] Получение доступа к компьютеру сотрудника HR-департамента | 1     | 2026-10-25  | bootcamp/7/infra-5 |
| [infra-6] Получите доступ к компьютеру сотрудника HR-департамента   | 2     | 2026-10-25  | bootcamp/7/infra-6 |

### flare-on

| Writeup       | Files | Last commit | Path                               |
|---------------|-------|-------------|------------------------------------|
| Flare-On 2014 | 17    | -           | flare-on/1/2014_FLAREOn_Challenges |

### hackthebox

| Writeup    | Files | Last commit | Path                  |
|------------|-------|-------------|-----------------------|
| Cohort     | 4     | 2026-11-13  | hackthebox/cohort     |
| Dancing    | 1     | 2026-10-23  | hackthebox/dancing    |
| DoubleTake | 3     | 2026-11-16  | hackthebox/doubletake |
| Fawn       | 1     | 2026-10-23  | hackthebox/fawn       |
| Management | 1     | -           | hackthebox/management |
| Meow       | 1     | 2026-10-23  | hackthebox/meow       |

### others

| Writeup                     | Files | Last commit | Path   |
|-----------------------------|-------|-------------|--------|
| WRITEUPS FROM OTHERS PEOPLE | 18    | 2026-10-18  | others |

<!-- INDEX:END -->
