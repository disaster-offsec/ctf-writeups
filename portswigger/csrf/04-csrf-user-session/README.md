# Lab: CSRF where token is not tied to user session

| | |
|---|---|
| **Платформа / Событие** | PortSwigger Web Security Academy |
| **Категория** | csrf |
| **Сложность** | — |
| **Статус** | done |
| **Дата решения** | 2026-11-15 |
| **Ссылка на таск** | — |

Level: `PRACTITIONER`

## Description

This lab's email change functionality is vulnerable to CSRF. It uses tokens to try to prevent CSRF attacks, but they aren't integrated into the site's session handling system.

> To solve the lab, use your exploit server to host an HTML page that uses a CSRF attack to change the viewer's email address.

You have two accounts on the application that you can use to help design your attack. The credentials are as follows:

- `wiener:peter`
- `carlos:montoya`

# Solution

Механизм `CSRF`-токена здесь валидацию не отменяет — сервер требует, чтобы параметр `csrf`
существовал и был валидным. Но название лабы подсказывает слабое место:
токен не привязан к сессии пользователя.

Гипотеза: сервер отвечает на вопрос 
"валиден ли этот токен вообще",
а не "принадлежит ли он сессии, из которой пришёл запрос".

Токен виден на странице `/my-account` в скрытом поле формы, а также в любом перехваченном `POST`-запросе:

```http
POST /login HTTP/2
...
csrf=aHoLiukdqwNJOVBEaznjxjanjTf57o2P&username=wiener&password=peter
```

Проверяем гипотезу в `Repeater`:

- `POST /my-account/change-email` с валидным токеном и своими куками -> `302` (база, валидация существует);
- тот же запрос с битым токеном (`csrf=AAA`) -> `отказ`;
- тот же запрос с токеном из другой сессии (второго аккаунта `carlos:montoya` или устаревшим своим) -> `302`.
  Вот здесь и уязвимость: сервер не сверяет токен с сессией.

Для пейлоада достаточно любого валидного токена — красть куку жертвы не нужно.
Вшиваем токен в форму и доставляем жертве через `exploit`-сервер:

```html
<form action="https://0a7800620313531e805308fe00f600f2.web-security-academy.net/my-account/change-email" method="POST">
  <input type="hidden" name="csrf" value="aHoLiukdqwNJOVBEaznjxjanjTf57o2P">
  <input type="hidden" name="email" value="hacker@evil-user.net">
  <input type="submit" value="Submit request">
</form>
<script>document.forms[0].submit();</script>
```

**Почему это работает.**\
В запросе жертвы куки — её (значит, сервер действует от её имени), а токен — атакующего.
Валидация проходит, потому что сервер проверяет лишь существование и валидность токена глобально,
не сопоставляя его с владельцем сессии.

**Как такое встречается в реальных приложениях:**\
токены `CSRF` генерируются в общем пуле без привязки к `session ID`, либо бэкенд хранит их в единой таблице
"токен -> валиден" и не проверяет владельца.
Достаточно разово добыть любой валидный токен — например,
зарегистрировав собственный аккаунт в уязвимом приложении — и он подойдёт для атак на всех пользователей.
