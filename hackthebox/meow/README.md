# Meow

## Description

Level: `Very Easy`
OS: `Linux`
Target: `10.129.48.158`

# Solution

## In cybersecurity, isolated environments—like Pwnbox or the vulnerable target machines—are often VMs. What does VM stand for?

Answer: `Virtual Machine`

## What tool do we use to interact with the operating system in order to issue commands via the command line, such as the one to start our VPN connection? It's also known as a console or shell.

Answer: `terminal`

## What service do we use to form our VPN connection into HTB labs?

Answer: `openvpn`

## What tool do we use to test our connection to the target with an ICMP echo request?

Answer: `ping`

## What is the name of the most common tool for finding open ports on a target?

Answer: `nmap`

## What service do we identify on port 23/tcp during our scans?

Answer: `Telnet`

## What username is able to log into the target over telnet with a blank password?

Answer: `root`

## Submit the flag located in root's home directory.

```bash
telnet 10.129.48.158
Trying 10.129.48.158...
Connected to 10.129.48.158.
Escape character is '^]'.

ls
  █  █         ▐▌     ▄█▄ █          ▄▄▄▄
  █▄▄█ ▀▀█ █▀▀ ▐▌▄▀    █  █▀█ █▀█    █▌▄█ ▄▀▀▄ ▀▄▀
  █  █ █▄█ █▄▄ ▐█▀▄    █  █ █ █▄▄    █▌▄█ ▀▄▄▀ █▀█


Meow login: 
lsPassword: 

Login incorrect
Meow login: root
Welcome to Ubuntu 20.04.2 LTS (GNU/Linux 5.4.0-77-generic x86_64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/advantage

  System information as of Fri 23 Oct 2026 07:57:45 PM UTC

  System load:           0.0
  Usage of /:            41.7% of 7.75GB
  Memory usage:          4%
  Swap usage:            0%
  Processes:             135
  Users logged in:       0
  IPv4 address for eth0: 10.129.48.158
  IPv6 address for eth0: dead:beef::a0de:adff:fead:8ae

 * Super-optimized for small spaces - read how we shrank the memory
   footprint of MicroK8s to make it the smallest full K8s around.

   https://ubuntu.com/blog/microk8s-memory-optimisation

75 updates can be applied immediately.
31 of these updates are standard security updates.
To see these additional updates run: apt list --upgradable


The list of available updates is more than a week old.
To check for new updates run: sudo apt update

Last login: Mon Sep  6 15:15:23 UTC 2021 from 10.10.14.18 on pts/0
root@Meow:~# ls
flag.txt  snap
root@Meow:~# cat flag.txt 
b40abdfe23665f766f9c61ecba8a4c19
```

Answer: `b40abdfe23665f766f9c61ecba8a4c19`
