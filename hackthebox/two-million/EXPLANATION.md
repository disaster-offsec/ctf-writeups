# hackthebox: теория класса

> Теоретический конспект, общий для всех лаб папки `hackthebox`.
> Живёт в `README.md` папки класса, лабы ссылаются сюда.

## What is it

В этой лабе (TwoMillion) сработали сразу несколько классов уязвимостей, и
теория — про каждый из них в отдельности:

1. **Broken access control / mass assignment** — сервер определяет, кто
   клиент, по признакам, которыми клиент управляет сам (заголовок запроса,
   поля тела). Клиент и меняет формат запроса, обходя проверку, и задаёт
   значение привилегированного поля (`is_admin`).
2. **OS command injection** — пользовательский ввод попадает в строку,
   исполняемую оболочкой, как фрагмент кода этой строки, а не как данные.
3. **Утечка секретов (hardcoded/env в webroot)** — конфигурация с паролями
   лежит в документ-руте и читается как обычный файл при любом RCE/LFI.
4. **Kernel privilege escalation** — известная CVE в ядре/линкере даёт
   локальному пользователю root без интеракции с приложением.

## How it works

Каждый класс формулируется через **чему доверяет приложение**:

1. **Access control.** Приложение доверяет, что «запрос с
   `Content-Type: application/json` уже проверен» — проверка роли исполняется
   в ветке парсинга JSON, а не до входа в обработчик. И что поля тела —
   только те, что объявил сервер.

    ```http
    PUT /api/v1/admin/settings/update HTTP/1.1
    Host: 2million.htb
    Content-Type: application/x-www-form-urlencoded
    email=user@2million.htb&is_admin=1
    ```

2. **Command injection.** Приложение доверяет, что строка `username` — это
   данные. Оболочка видит иначе: `;` начинает новую команду.

    ```http
    PUT /api/v1/admin/vpn/generate HTTP/1.1
    Content-Type: application/json

    {"username":"admin; id"}
    ```

3. **Секреты.** Приложение доверяет, что файлы webroot — статические. Файл
   `.env` в `GET /var/www/html/.env` (или чтение через любой RCE) отдаёт
   креды как есть.

4. **Kernel privesc.** Приложение тут ни при чём: доверие — это предположение
   «у пользователя без прав нет способа заставить ядро переместить файл с
   сохранением setuid-метаданных через OverlayFS» (CVE-2023-0386) или
   «тюнинг-переменная линкера не переполняет буфер» (CVE-2023-4911).

**Условия для каждого класса:**

1. Access control: маршрут проверяет роль в одной ветке кода; тело запроса
   может прийти в другом формате; клиент знает имя привилегированного поля.
2. Command injection: ввод попадает в `system()`/`exec`-подобный вызов без
   аргументного разделения; символы `;`, `|`, `$(`, backtick не экранированы.
3. Секреты: конфиг в webroot + права чтения + переиспользование пароля
   между двумя плоскостями (БД и ОС).
4. Kernel privesc: непропатченная версия ядра/линкера; локальный доступ
   (шелл от непривилегированного пользователя уже получен).

## Impact

- Access control: полный account takeover → роль администратора → доступ к
  админ-функциональности (в лабе — генерация VPN-конфигов с RCE).
- Command injection: исполнение команд от пользователя веб-сервера
  (`www-data`) → RCE на сервере. В связке с пунктом 1 — доступ сразу после
  повышения роли.
- Секреты: горизонтальное движение — креды из webroot переиспользуются для
  SSH/системных учёток → переход от `www-data` к полноценному пользователю.
- Kernel privesc: `uid=0` — конец цепочки, чтение любых данных на хосте.

## Defenses

1. **Авторизация как middleware.** Проверка роли — единый слой до обработчика,
   по сессионному объекту, не по формату запроса. Массовое присвоение —
   whitelist полей в ORM/сериализаторе (Symfony `form.fields`, Laravel
   `$fillable`, DRF `read_only_fields`).
2. **Никаких shell-строк из ввода.** `subprocess.run([...], shell=False)`;
   ввод — как отдельный аргумент (`execve`), не как фрагмент строки. Если
   shell неизбежен — `escapeshellarg` + whitelist разрешённых символов.
3. **Секреты.** Конфиг вне webroot и вне git (`.gitignore`), пароли — через
   переменные окружения/секрет-менеджер; БД-пароль ≠ системный пароль;
   регулярная ротация.
4. **Патч-менеджмент.** `unattended-upgrades` для ядра и glibc; мониторинг
   локальных privesc CVE для установленной версии ядра.

## Why defenses break

Классы bypass'ов — скелет всех лаб этого раздела:

- **bypass 1 (access control):** проверка есть, но в ветке, которую можно
  обойти сменой `Content-Type` — авторизация не как пред-обработчик, а как
  часть обработки одного формата. Лаба: `01-content-type-bypass`.
- **bypass 2 (mass assignment):** валидация полей есть для публичных форм,
  но админ-поле просто не вынесено в read-only — сервер доверяет телу как
  «своим» данным. Лаба: `02-mass-assignment`.
- **bypass 3 (command injection):** экранирование есть, но экранируется не
  тот слой — экранируются кавычки, а не разделители команд; либо ввод
  попадает в вызов через промежуточный конкатенированный шаблон. Лаба:
  `03-command-injection-shell-strings`.
- **bypass 4 (kernel):** патч вышел, но не применён; эксплуатация живёт
  месяцами в window между релизом фикса и деплоем. Лаба:
  `04-kernel-exploit-outdated`.

## References

- [PortSwigger Web Security Academy — Access control](https://portswigger.net/web-security/access-control)
- [OWASP Cheat Sheets](https://cheatsheetseries.owasp.org/)
- [OWASP: Mass Assignment](https://cheatsheetseries.owasp.org/cheatsheets/Mass_Assignment_Cheat_Sheet.html)
- [OWASP: OS Command Injection Defense](https://cheatsheetseries.owasp.org/cheatsheets/OS_Command_Injection_Defense_Cheat_Sheet.html)
- [NVD: CVE-2023-0386](https://nvd.nist.gov/vuln/detail/CVE-2023-0386)
- [NVD: CVE-2023-4911](https://nvd.nist.gov/vuln/detail/CVE-2023-4911)
