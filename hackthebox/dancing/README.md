# Dancing

## Description

Level: Very Easy
OS: Windows
Target: 10.129.1.12

# Solution

## What does the 3-letter acronym SMB stand for? 

Answer: `Server Message Block`

## What port does SMB use to operate at?

Answer: `445`

## What is the service name for port 445 that came up in our Nmap scan?

```bash
nmap -Pn -sV 10.129.1.12
Starting Nmap 7.95 ( https://nmap.org ) at 2026-10-23 16:27 EDT
Nmap scan report for 10.129.1.12
Host is up (0.022s latency).
Not shown: 996 closed tcp ports (conn-refused)
PORT     STATE SERVICE       VERSION
135/tcp  open  msrpc         Microsoft Windows RPC
139/tcp  open  netbios-ssn   Microsoft Windows netbios-ssn
445/tcp  open  microsoft-ds?
5985/tcp open  http          Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
Service Info: OS: Windows; CPE: cpe:/o:microsoft:windows

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
Nmap done: 1 IP address (1 host up) scanned in 7.86 seconds
```

Answer: `microsoft-ds`

## What is the 'flag' or 'switch' that we can use with the smbclient utility to 'list' the available SMB shares on Dancing?

```bash
mbclient -h

Invalid option -h: unknown option

Usage: smbclient [-?EgqBNPkV] [-?|--help] [--usage] [-M|--message=HOST]
        [-I|--ip-address=IP] [-E|--stderr] [-L|--list=HOST]
        [-T|--tar=<c|x>IXFvgbNan] [-D|--directory=DIR] [-c|--command=STRING]
        [-b|--send-buffer=BYTES] [-t|--timeout=SECONDS] [-p|--port=PORT]
        [-g|--grepable] [-q|--quiet] [-B|--browse]
        [-d|--debuglevel=DEBUGLEVEL] [--debug-stdout]
        [-s|--configfile=CONFIGFILE] [--option=name=value]
        [-l|--log-basename=LOGFILEBASE] [--leak-report] [--leak-report-full]
        [-R|--name-resolve=NAME-RESOLVE-ORDER]
        [-O|--socket-options=SOCKETOPTIONS] [-m|--max-protocol=MAXPROTOCOL]
        [-n|--netbiosname=NETBIOSNAME] [--netbios-scope=SCOPE]
        [-W|--workgroup=WORKGROUP] [--realm=REALM]
        [-U|--user=[DOMAIN/]USERNAME[%PASSWORD]] [-N|--no-pass]
        [--password=STRING] [--pw-nt-hash] [-A|--authentication-file=FILE]
        [-P|--machine-pass] [--simple-bind-dn=DN]
        [--use-kerberos=desired|required|off] [--use-krb5-ccache=CCACHE]
        [--use-winbind-ccache] [--client-protection=sign|encrypt|off]
        [-k|--kerberos] [-V|--version] [OPTIONS] service <password>
```

Answer: `-L`

## How many shares are there on Dancing? 

```bash
smbclient -L //10.129.1.12/
Password for [WORKGROUP\d1s4]:
␍
	Sharename       Type      Comment
	---------       ----      -------
	ADMIN$          Disk      Remote Admin
	C$              Disk      Default share
	IPC$            IPC       Remote IPC
	WorkShares      Disk      
SMB1 disabled -- no workgroup available␍
```

Answer: `4`

## What is the name of the share we are able to access in the end with a blank password?

```bash
smbclient //10.129.1.12/WorkShares -N
Try "help" to get a list of possible commands.␍
smb: \>
```

Answer: `WorkShares`

## What is the command we can use within the SMB shell to download the files we find?

Answer: `get`

## Submit the flag located on the SMB share.

```bash
smbclient //10.129.1.12/WorkShares -N
Try "help" to get a list of possible commands.
smb: \> cd James.P
smb: \> get flag.txt
EOF
cat flag.txt
5f61c10dffbc77a704d76016a22f1664
```

Answer: `5f61c10dffbc77a704d76016a22f1664`
