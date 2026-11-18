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

## New writeup

```
./tools/new_writeup.sh portswigger/csrf 06-csrf-referrer-validation "CSRF where Referer validation is bypassed"
python3 tools/generate_index.py   # обновить индексные таблицы
```

---

<!-- INDEX:START -->
## PortSwigger Academy

### [portswigger](portswigger/)

| Class                                         | Labs | Last commit |
|-----------------------------------------------|------|-------------|
| [access-control](portswigger/access-control/) | 3    | 2026-11-18  |
| [csrf](portswigger/csrf/)                     | 6    | 2026-11-18  |
| [path-traversal](portswigger/path-traversal/) | 1    | 2026-10-26  |
| [sqli](portswigger/sqli/)                     | 12   | 2026-11-08  |
| [ssrf](portswigger/ssrf/)                     | 3    | 2026-10-26  |
| [xss](portswigger/xss/)                       | 5    | 2026-11-18  |
| [xxe](portswigger/xxe/)                       | 1    | 2026-10-26  |

## CTF events

### [avitoctf-2026](avitoctf-2026/)

| Writeup                                           | Files | Last commit |
|---------------------------------------------------|-------|-------------|
| [Сопромёд: метро](avitoctf-2026/sopromyod-metro/) | 5     | 2026-11-18  |

### [kubok-ctf-2026](kubok-ctf-2026/)

| Writeup                                                                  | Files | Last commit |
|--------------------------------------------------------------------------|-------|-------------|
| [burmalda](kubok-ctf-2026/burmalda/)                                     | 2     | 2026-11-18  |
| [compuuuter — writeup](kubok-ctf-2026/computer/)                         | 10    | 2026-11-18  |
| [connecttome](kubok-ctf-2026/connecttome/)                               | 3     | 2026-11-18  |
| [Электронный журнал — райтап (web, 1000 pts)](kubok-ctf-2026/eljournal/) | 29    | 2026-11-18  |
| [image-viewer](kubok-ctf-2026/image-viewer/)                             | 2     | 2026-11-18  |
| [MeowSim: Schrödinger E... — райтап](kubok-ctf-2026/meow-sim/)           | 3     | 2026-11-18  |
| [Райтап: реверс-инжиниринг задания mmm](kubok-ctf-2026/mmm/)             | 8     | 2026-11-18  |
| [my-own-fs](kubok-ctf-2026/my-own-fs/)                                   | 6     | 2026-11-18  |
| [Weird RSA — райтап](kubok-ctf-2026/weird-rsa/)                          | 5     | 2026-11-18  |

### [solarctf-2026](solarctf-2026/)

| Writeup                                                                         | Files | Last commit |
|---------------------------------------------------------------------------------|-------|-------------|
| [Writeup — Kommunalki (web)](solarctf-2026/_unsorted/kommunalki/)               | 1     | 2026-11-18  |
| [Невероятная утка](solarctf-2026/_unsorted/neveroyatnaya-utka/)                 | 1     | 2026-11-18  |
| [Нейропитомец](solarctf-2026/_unsorted/neyropitomets/)                          | 1     | 2026-11-18  |
| [Новый телефон](solarctf-2026/_unsorted/novyy-telefon/)                         | 1     | 2026-11-18  |
| [Out of frame — Майя](solarctf-2026/_unsorted/out-of-frame/)                    | 1     | 2026-11-18  |
| [PBX «Солярис-3» — разбор ночного дампа](solarctf-2026/_unsorted/pbx-sabotage/) | 1     | 2026-11-18  |
| [Что было в архиве](solarctf-2026/_unsorted/poslednee-delo/)                    | 1     | 2026-11-18  |
| [Пустота — решение](solarctf-2026/_unsorted/pustota/)                           | 1     | 2026-11-18  |
| [Шах и мат](solarctf-2026/_unsorted/shakh-i-mat/)                               | 1     | 2026-11-18  |
| [Writeup — Zero Report (SolarCTF 2026)](solarctf-2026/crypto/0-report/)         | 5     | 2026-11-18  |
| [Writeup — Пропавший архив (SolarCTF 2026)](solarctf-2026/crypto/lostarch/)     | 5     | 2026-11-18  |
| [Writeup — РакушкаBreach (SolarCTF 2026)](solarctf-2026/forensics/breach/)      | 2     | 2026-11-18  |
| [Writeup — Локпик / Lockpick (SolarCTF 2026)](solarctf-2026/misc/lockpick/)     | 5     | 2026-11-18  |
| [Writeup — Вентилятор303 (SolarCTF 2026)](solarctf-2026/misc/vent303/)          | 2     | 2026-11-18  |
| [Writeup — Ткач / Weaver (SolarCTF 2026)](solarctf-2026/reverse/tkach/)         | 10    | 2026-11-18  |
| [Writeup — Vintage Bank (SolarCTF 2026)](solarctf-2026/web/vintage_bank/)       | 2     | 2026-11-18  |

## Platforms & trainings

### [bootcamp](bootcamp/)

| Writeup                                                                                      | Files | Last commit |
|----------------------------------------------------------------------------------------------|-------|-------------|
| [infra-1](bootcamp/7/infra-1/)                                                               | 2     | 2026-10-24  |
| [infra](bootcamp/7/infra-2/)                                                                 | 7     | 2026-10-25  |
| [infra-3](bootcamp/7/infra-3/)                                                               | 1     | 2026-10-25  |
| [\[infra-4\] Внутренняя разведка (Active Directory)](bootcamp/7/infra-4/)                    | 3     | 2026-10-25  |
| [\[infra-5\] Получение доступа к компьютеру сотрудника HR-департамента](bootcamp/7/infra-5/) | 1     | 2026-10-25  |
| [\[infra-6\] Получите доступ к компьютеру сотрудника HR-департамента](bootcamp/7/infra-6/)   | 2     | 2026-10-25  |
| [Отчёт по задачам web-1-1 -- RCE на узле library.edu.stf](bootcamp/7/web-1/web-1-1/)         | 2     | 2026-11-18  |
| [Райтап: Standoff 365 Bootcamp — Web-1-2 (CVE-2023-4911)](bootcamp/7/web-1/web-1-2/)         | 3     | 2026-11-18  |
| [Отчёт по задачам web-2-1 -- LFI на узле www.edu.stf](bootcamp/7/web-2/1/)                   | 1     | 2026-11-18  |
| [web-2-2: RCE. Write-Up](bootcamp/7/web-2/2/)                                                | 1     | 2026-11-18  |

### [flare-on](flare-on/)

| Writeup                                                 | Files | Last commit |
|---------------------------------------------------------|-------|-------------|
| [Flare-On 2014](flare-on/2014/2014_FLAREOn_Challenges/) | 17    | 2026-11-18  |

### [hackthebox](hackthebox/)

| Writeup                              | Files | Last commit |
|--------------------------------------|-------|-------------|
| [Cohort](hackthebox/cohort/)         | 4     | 2026-11-13  |
| [Dancing](hackthebox/dancing/)       | 1     | 2026-10-23  |
| [DoubleTake](hackthebox/doubletake/) | 3     | 2026-11-16  |
| [Fawn](hackthebox/fawn/)             | 1     | 2026-10-23  |
| [Management](hackthebox/management/) | 1     | 2026-11-18  |
| [Meow](hackthebox/meow/)             | 1     | 2026-10-23  |

### [others](others/)

| Writeup                                | Files | Last commit |
|----------------------------------------|-------|-------------|
| [WRITEUPS FROM OTHERS PEOPLE](others/) | 9     | 2026-11-18  |

### [picoctf-trainings](picoctf-trainings/)

| Writeup                                                                                  | Files | Last commit |
|------------------------------------------------------------------------------------------|-------|-------------|
| [bookmarklet](picoctf-trainings/web/easy/bookmarklet/)                                   | 3     | 2026-11-18  |
| [cookie-monster-secret-recipe](picoctf-trainings/web/easy/cookie-monster-secret-recipe/) | 3     | 2026-11-18  |
| [cookies](picoctf-trainings/web/easy/cookies/)                                           | 3     | 2026-11-18  |
| [crack-the-gate](picoctf-trainings/web/easy/crack-the-gate/)                             | 3     | 2026-11-18  |
| [dont-use-client-side](picoctf-trainings/web/easy/dont-use-client-side/)                 | 4     | 2026-11-18  |
| [get-ahead](picoctf-trainings/web/easy/get-ahead/)                                       | 3     | 2026-11-18  |
| [heap-dump](picoctf-trainings/web/easy/heap-dump/)                                       | 4     | 2026-11-18  |
| [includes](picoctf-trainings/web/easy/includes/)                                         | 4     | 2026-11-18  |
| [inspect-html](picoctf-trainings/web/easy/inspect-html/)                                 | 3     | 2026-11-18  |
| [inspect-me](picoctf-trainings/web/easy/inspect-me/)                                     | 3     | 2026-11-18  |
| [introtoburp](picoctf-trainings/web/easy/introtoburp/)                                   | 3     | 2026-11-18  |
| [local-authority](picoctf-trainings/web/easy/local-authority/)                           | 3     | 2026-11-18  |
| [logon](picoctf-trainings/web/easy/logon/)                                               | 3     | 2026-11-18  |
| [n0s4n1ty-1](picoctf-trainings/web/easy/n0s4n1ty-1/)                                     | 4     | 2026-11-18  |
| [scavenger-hunt](picoctf-trainings/web/easy/scavenger-hunt/)                             | 3     | 2026-11-18  |
| [ssti1](picoctf-trainings/web/easy/ssti1/)                                               | 3     | 2026-11-18  |
| [unminify](picoctf-trainings/web/easy/unminify/)                                         | 3     | 2026-11-18  |
| [webdecode](picoctf-trainings/web/easy/webdecode/)                                       | 3     | 2026-11-18  |
| [where-are-the-robots](picoctf-trainings/web/easy/where-are-the-robots/)                 | 3     | 2026-11-18  |
| [hashgate](picoctf-trainings/web/medium/hashgate/)                                       | 6     | 2026-11-18  |
| [nofa](picoctf-trainings/web/medium/nofa/)                                               | 7     | 2026-11-18  |
| [secret-box](picoctf-trainings/web/medium/secret-box/)                                   | 20    | 2026-11-18  |

<!-- INDEX:END -->
