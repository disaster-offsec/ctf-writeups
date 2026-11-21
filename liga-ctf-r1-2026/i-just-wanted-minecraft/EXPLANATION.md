# liga-ctf-r1-2026: теория класса

> Теоретический конспект, общий для всех лаб папки `liga-ctf-r1-2026`.
> Живёт в `README.md` папки класса, лабы ссылаются сюда.

## What is it

Определение уязвимости своими словами, без копипасты из документации.

## How it works

Условия, при которых атака возможна (как у CSRF — три условия). Формулируй
через «чему доверяет приложение».

Пример уязвимого запроса:

```http
POST /email/change HTTP/1.1
Host: vulnerable-website.com
Cookie: session=...
email=attacker@evil.com
```

## Impact

- Что получает атакующий в худшем случае (account takeover, RCE, …).
- Цепочки: что можно скомбинировать с другими классами.

## Defenses

1. Основная защита (токен / SameSite / параметризация / …) — как работает.
2. Вторая линия (Referer, CSP, WAF) — почему она «менее надёжна».
3. Что включено по умолчанию в современных браузерах/фреймворках.

## Why defenses break

Классы bypass'ов — это скелет всех лаб этого раздела:

- bypass 1: когда защита есть, но не покрывает случай X → лаба `01-…`
- bypass 2: … → лаба `02-…`

## References

- [PortSwigger Web Security Academy](https://portswigger.net/web-security)
- [OWASP Cheat Sheet](https://cheatsheetseries.owasp.org/)
