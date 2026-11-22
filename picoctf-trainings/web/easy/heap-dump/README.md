<!-- конвертировано из heap-dump.typ, tools/typ2readme.py -->

| | |
|---|---|
| **Платформа / Событие** | picoCTF Trainings |
| **Категория** | Web |
| **Сложность** | Easy 50 pts |
| **Статус** | done |
| **Дата решения** | 19 июля 2026 |
| **Ссылка на таск** | — |

# head-dump

## Задание

Welcome to the challenge! In this challenge, you will explore a web application and find an endpoint that exposes a file containing a hidden flag.

The application is a simple blog website where you can read articles about various topics, including an article about API Documentation. Your goal is to explore the application and find the endpoint that generates files holding the server’s memory, where a secret flag is hidden.

## Решение

cначала находим папку api-docs, неважно фаззингом или ручками, затем находим функцию heapdump,
затем, качаем файл и выводим флаг

```bash
cat heapdump-1784483276876.heapsnapshot | grep "picoCTF" | less
```
