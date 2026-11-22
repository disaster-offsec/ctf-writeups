<!-- конвертировано из where-are-the-robots.typ, tools/typ2readme.py -->

| | |
|---|---|
| **Платформа / Событие** | picoCTF Trainings |
| **Категория** | Web |
| **Сложность** | Easy 100 pts |
| **Статус** | done |
| **Дата решения** | 19 июля 2026 |
| **Ссылка на таск** | — |

# where are the robots

## Задание

Can you find the robots?

## Решение

Открываем /robots.txt и видим:
```text
User-agent: *
Disallow: /cc6b1.html
```

Заходим на /cc6b1.html:
```text
Guess you found the robots
picoCTF{ca1cu1at1ng_Mach1n3s_cc6b1}

```
