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
├── standoff-bootcamp-7/  # Standoff Bootcamp, сезон 7 — по трекам
├── <event>-<year>/       # CTF-события: flare-on-2014, solarctf-2026, kubok-ctf-2026...
└── templates/ + tools/   # шаблоны и скрипты (индекс, проверки)
```

## Конвенции

- Райтап = папка с `README.md`: **TL;DR → Steps → Why it works → Defense**.
- Коммиты: `[<класс>|<платформа>] суть`; служебные: `docs:`, `chore:`, `fix:`.

## Новый райтап

```
./tools/new_writeup.sh portswigger/csrf 06-csrf-referrer-validation "CSRF where Referer validation is bypassed"
python3 tools/generate_index.py   # обновить индексные таблицы
python3 tools/check_titles.py     # безликие заголовки (lab1, task2) и код-блоки
python3 tools/check_writeups.py   # соответствие шаблону: шапка, секции, ссылки
```

`generate_index.py` помимо таблиц: создаёт заготовки README для классов
portswigger, где конспекта ещё нет, и чинит ссылки во всех README —
GitHub `blob`/`tree`-URL и корневые пути переводит в относительные
(как папки лежат на диске). Ссылки на чужие репозитории и внешние сайты
не трогает; второй запуск изменений не вносит.

`check_writeups.py` — проверка райтапов на соответствие
`templates/writeup-README.md`: шапка, канонические секции (с синонимами:
«Кратко» ≡ TL;DR, «Решение» ≡ Steps), пустые секции, битые внутренние
ссылки/картинки, остатки текста-заглушки из шаблона. Чужие разборы
(`alternate-solution.md` в папке задачи) структурой не нормируются —
внимание только к своим README.

---

<!-- INDEX:START -->
## PortSwigger Academy

Solved: 31/31

| Folder                      | Done  | Draft | Last commit |
|-----------------------------|-------|-------|-------------|
| [portswigger](portswigger/) | 31/31 | —     | 2026-11-22  |

## CTF events

Solved: 27/37 · drafts: 4 · no writeup: 6

| Folder                                | Done  | Draft | Last commit |
|---------------------------------------|-------|-------|-------------|
| [avitoctf-2026](avitoctf-2026/)       | 2/2   | —     | 2026-11-22  |
| [flare-on-2014](flare-on-2014/)       | 1/7   | —     | 2026-11-22  |
| [kubok-ctf-2026](kubok-ctf-2026/)     | 5/9   | 4     | 2026-11-22  |
| [liga-ctf-r1-2026](liga-ctf-r1-2026/) | 3/3   | —     | 2026-11-22  |
| [solarctf-2026](solarctf-2026/)       | 16/16 | —     | 2026-11-22  |

## Platforms & trainings

Solved: 38/38

| Folder                                      | Done  | Draft | Last commit |
|---------------------------------------------|-------|-------|-------------|
| [hackthebox](hackthebox/)                   | 6/6   | —     | 2026-11-22  |
| [picoctf-trainings](picoctf-trainings/)     | 22/22 | —     | 2026-11-22  |
| [standoff-bootcamp-7](standoff-bootcamp-7/) | 10/10 | —     | 2026-11-22  |
<!-- INDEX:END -->
