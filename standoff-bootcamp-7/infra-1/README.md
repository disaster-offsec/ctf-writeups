# infra-1

## Description

> Получите список учетных записей с внешних веб-ресурсов компании.
> Восстановите пропущенные символы в адресе `r***s@edu.stf` 
> и укажите его в отчете полностью.

# Solution

Естественно сразу возникает вопрос, а что искать. Надо изучать сеть))
Нам измвестен скоуп внешнего периметра: `10.124.1.224/27`

Сначала посмотрим живые хосты без сканирования самих портов:
```bash
nmap -sn 10.124.1.224/27
Starting Nmap 7.95 ( https://nmap.org ) at 2026-10-24 19:25 UTC
Nmap scan report for 10.124.1.225
Host is up (0.099s latency).
Nmap scan report for 10.124.1.231
Host is up (0.099s latency).
Nmap scan report for 10.124.1.232
Host is up (0.099s latency).
Nmap scan report for library.edu.stf (10.124.1.233)
Host is up (0.099s latency).
Nmap scan report for 10.124.1.234
Host is up (0.099s latency).
Nmap scan report for 10.124.1.235
Host is up (0.13s latency).
Nmap scan report for 10.124.1.236
Host is up (0.13s latency).
Nmap scan report for 10.124.1.237
Host is up (0.063s latency).
Nmap scan report for 10.124.1.238
Host is up (0.063s latency).
Nmap scan report for 10.124.1.239
Host is up (0.063s latency).
Nmap scan report for 10.124.1.240
Host is up (0.063s latency).
Nmap scan report for 10.124.1.241
Host is up (0.063s latency).
Nmap scan report for 10.124.1.242
Host is up (0.063s latency).
Nmap scan report for 10.124.1.253
Host is up (0.13s latency).
Nmap done: 32 IP addresses (14 hosts up) scanned in 8.66 seconds
```

Но для читабельности сделаем так:
```bash
nmap -sn 10.124.1.224/27 | grep report
Nmap scan report for 10.124.1.225
Nmap scan report for 10.124.1.231
Nmap scan report for 10.124.1.232
Nmap scan report for library.edu.stf (10.124.1.233)
Nmap scan report for 10.124.1.234
Nmap scan report for 10.124.1.235
Nmap scan report for 10.124.1.236
Nmap scan report for 10.124.1.237
Nmap scan report for 10.124.1.238
Nmap scan report for 10.124.1.239
Nmap scan report for 10.124.1.240
Nmap scan report for 10.124.1.241
Nmap scan report for 10.124.1.242
Nmap scan report for 10.124.1.253
```

Перед тем как продолжить добавим домен `library.edu.stf` в `/etc/hosts`:
```bash
...
# Others
10.124.1.233    library.edu.stf
```

Создадим список целей: `targets.txt`

```text
10.124.1.225
10.124.1.231
10.124.1.232
library.edu.stf
10.124.1.234
10.124.1.235
10.124.1.236
10.124.1.237
10.124.1.238
10.124.1.239
10.124.1.240
10.124.1.241
10.124.1.242
10.124.1.253
```

Запускаем быстрое сканирование:
```bash
nmap -sV -T4 -iL targets.txt -oN fast_scan.txt
```

- `-sV` скан с версиями
- `-T4` ускорение сканирования
- `-iL targets.txt` читаем цели из файла
- `oN fast_scan.txt` сохраняем результат в файл

Имеем:
```bash
Starting Nmap 7.95 ( https://nmap.org ) at 2026-10-24 19:34 UTC
Warning: 10.124.1.232 giving up on port because retransmission cap hit (6).
Warning: 10.124.1.233 giving up on port because retransmission cap hit (6).
...
```

И файл `fast_scan.txt`, опустим предупреждения и `closed`/`filtered` порты:
```text
Nmap scan report for 10.124.1.231
PORT     STATE    SERVICE        VERSION
22/tcp   open     ssh            OpenSSH 8.2p1 Ubuntu 4ubuntu0.11 (Ubuntu Linux; protocol 2.0)
80/tcp   open     http           nginx 1.25.4
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Nmap scan report for 10.124.1.232
PORT     STATE    SERVICE         VERSION
22/tcp   open     ssh             OpenSSH 8.4p1 Debian 5 (protocol 2.0)
80/tcp   open     http            Apache httpd 2.4.49 ((Unix))
8080/tcp open     http            Golang net/http server
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Nmap scan report for library.edu.stf (10.124.1.233)
PORT      STATE    SERVICE           VERSION
22/tcp    open     ssh               OpenSSH 9.0p1 Ubuntu 1ubuntu7.3 (Ubuntu Linux; protocol 2.0)
80/tcp    open     http              Apache httpd 2.4.54 ((Ubuntu))
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Nmap scan report for 10.124.1.234
PORT      STATE    SERVICE        VERSION
22/tcp    open     ssh            OpenSSH 8.2p1 Ubuntu 4ubuntu0.11 (Ubuntu Linux; protocol 2.0)
80/tcp    open     http           Apache httpd 2.4.51 ((Debian))
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Nmap scan report for 10.124.1.235
PORT      STATE  SERVICE    VERSION
21/tcp    open   tcpwrapped
22/tcp    open   tcpwrapped
80/tcp    open   tcpwrapped

Nmap scan report for 10.124.1.236
PORT     STATE    SERVICE        VERSION
22/tcp   open     ssh            OpenSSH 7.6p1 Ubuntu 4ubuntu0.3 (Ubuntu Linux; protocol 2.0)
80/tcp   open     http           Apache httpd 2.4.29 ((Ubuntu))
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Nmap scan report for 10.124.1.237
PORT      STATE    SERVICE VERSION
22/tcp    open     ssh     OpenSSH 8.4p1 Debian 5+deb11u1 (protocol 2.0)
80/tcp    open     http    nginx 1.14.2
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Nmap scan report for 10.124.1.238
PORT     STATE    SERVICE  VERSION
22/tcp   open     ssh      OpenSSH 8.4p1 Debian 5+deb11u2 (protocol 2.0)
80/tcp   open     http     Apache httpd 2.4.56 ((Debian))
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Nmap scan report for 10.124.1.239
PORT     STATE    SERVICE    VERSION
22/tcp   open     ssh        OpenSSH 8.2p1 Ubuntu 4ubuntu0.13 (Ubuntu Linux; protocol 2.0)
80/tcp   open     http       Apache httpd 2.4.41 ((Ubuntu))
5432/tcp open     postgresql PostgreSQL DB 12.14 - 12.18
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Nmap scan report for 10.124.1.240
PORT     STATE    SERVICE       VERSION
22/tcp   open     ssh           OpenSSH 8.2p1 Ubuntu 4ubuntu0.11 (Ubuntu Linux; protocol 2.0)
53/tcp   open     domain        ISC BIND 9.16.48 (Ubuntu Linux)
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Nmap scan report for 10.124.1.241
PORT    STATE    SERVICE VERSION
22/tcp  open     ssh     OpenSSH 8.2p1 Ubuntu 4ubuntu0.13 (Ubuntu Linux; protocol 2.0)
80/tcp  open     http    Apache httpd 2.4.41 ((Ubuntu))
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Nmap scan report for 10.124.1.242
PORT     STATE    SERVICE VERSION
22/tcp   open     ssh     OpenSSH 7.6p1 Ubuntu 4ubuntu0.5 (Ubuntu Linux; protocol 2.0)
80/tcp   open     http    Apache httpd 2.4.29 ((Ubuntu))
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Nmap scan report for 10.124.1.253
PORT    STATE SERVICE VERSION
443/tcp open  https?
```

Теперь посмотрим что лежит на `http`/`https` серваках этих хостов:

По адресу `http://10.124.1.235/`:

![fig1.png](fig1.png)

есть 3 адреса:
- `r_andrews@edu.stf`
- `t_mathis@edu.stf`
- `s_dotson@edu.stf`

А искомый адрес начинается на `r`, значит искомый это `r_andrews@edu.stf`

