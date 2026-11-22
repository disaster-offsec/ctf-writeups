# ctf-writeups

Public practice log in offensive security: walkthroughs of labs and machines with
theory notes. Every writeup contains **what I did**, **why it worked** and
**how to defend against it**.

> Автор: **nedo-offsec** · МАИ · offensive security (pentest / red team / RE)
> Команды: SecondLayer (SOLAR CTF, Кубок CTF) · NEDO-OFFSEC (AvitoCTF)
> GitHub: [disaster-offsec](https://github.com/disaster-offsec)

---

## Структура

```
ctf-writeups/
├── portswigger/          # PortSwigger Academy — по классам уязвимостей (NN-slug/)
├── hackthebox/           # HTB — по машинам
├── picoctf-trainings/    # picoCTF Trainings — по категориям
├── <event>-<year>/       # CTF-события: solarctf-2026, kubok-ctf-2026, avitoctf-2026
├── bootcamp/             # учебные треки
└── others/               # разрозненные задачи
```

## Конвенции

- Райтап = папка с `README.md`: **TL;DR → Steps → Why it works → Defense**.
- Коммиты: `[<класс>|<платформа>] суть`; служебные: `docs:`, `chore:`, `fix:`.

## Новый райтап

```
./tools/new_writeup.sh portswigger/csrf 06-csrf-referrer-validation "CSRF where Referer validation is bypassed"
python3 tools/generate_index.py   # обновить индексные таблицы
python3 tools/check_titles.py     # найти безликие заголовки (lab1, task2) и заглушки
```

`generate_index.py` помимо таблиц: создаёт заготовки README для классов
portswigger, где конспекта ещё нет, и чинит ссылки во всех README —
GitHub `blob`/`tree`-URL и корневые пути переводит в относительные
(как папки лежат на диске). Ссылки на чужие репозитории и внешние сайты
не трогает; второй запуск изменений не вносит.

---

<!-- INDEX:START -->
## PortSwigger Academy

Solved: 31/31

| Folder                      | Done  | Draft | Last commit |
|-----------------------------|-------|-------|-------------|
| [portswigger](portswigger/) | 31/31 | —     | 2026-11-19  |

## CTF events

Solved: 22/28 · drafts: 6

| Folder                                | Done  | Draft | Last commit |
|---------------------------------------|-------|-------|-------------|
| [avitoctf-2026](avitoctf-2026/)       | 2/2   | —     | 2026-11-18  |
| [kubok-ctf-2026](kubok-ctf-2026/)     | 5/9   | 4     | 2026-11-18  |
| [liga-ctf-r1-2026](liga-ctf-r1-2026/) | 0/1   | 1     | 2026-11-21  |
| [solarctf-2026](solarctf-2026/)       | 15/16 | 1     | 2026-11-18  |

## Platforms & trainings

Solved: 40/40

| Folder                                  | Done  | Draft | Last commit |
|-----------------------------------------|-------|-------|-------------|
| [bootcamp](bootcamp/)                   | 10/10 | —     | 2026-11-18  |
| [flare-on](flare-on/)                   | 1/1   | —     | 2026-11-18  |
| [hackthebox](hackthebox/)               | 6/6   | —     | 2026-11-20  |
| [others](others/)                       | 1/1   | —     | 2026-11-18  |
| [picoctf-trainings](picoctf-trainings/) | 22/22 | —     | 2026-11-18  |
<!-- INDEX:END -->
