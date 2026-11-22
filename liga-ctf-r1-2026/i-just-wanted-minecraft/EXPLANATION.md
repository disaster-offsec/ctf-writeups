# Лига CTF (раунд 1): теория — supply chain, LD_PRELOAD-руткиты, закрепление

> Теоретический конспект к таску `i-just-wanted-minecraft`. Три класса,
> спрятанных в одном задании: compromise of supply chain, defense evasion
> через LD_PRELOAD и persistence. Всё — по факту решения, без домыслов.

## What is it

1. **Supply Chain Compromise (T1195).** Доверие переносится с разработчика
   на промежуточное звено: `sources.list` указывает на сторонний
   `repo.mchost.io`, подпись `InRelease` валидна (подключом), значит apt
   молча ставит всё, что в репозитории. Пакет выглядит легитимно
   (собирает Minecraft-сервер, тянет зависимости из Ubuntu), вредоносная
   логика живёт в maintainer-скриптах (`postinst`/`prerm`), которые
   выполняются от root при установке.
2. **LD_PRELOAD-руткит (T1574.006, Defense Evasion).** `libmcbackup.so`
   прописывается в `/etc/ld.so.preload` — библиотека подгружается в
   КАЖДЫЙ динамический бинарник до libc. Перехватом `stat`/`lstat`/
   `opendir` (через `dlsym(RTLD_NEXT, ...)`) она возвращает `ENOENT`
   для `/var/cache/mc-backup-tool` и `/var/log/mc-backup-tool`: файлы
   существуют на диске, но невидимы для `ls`, `find`, `stat`. Класс
   bypass'а: пользовательские инструменты доверяют своему view через
   syscall-обёртки, а не читают сырой блок-девайс/память.
3. **Persistence (T1053.003, T1098).** Два механизма, один живой:
   cron-файл `/etc/cron.d/mc-backup-sync` (sync.sh 2 раза в день,
   heartbeat каждые 6 часов) и SSH-ключ `backup@mc-backup-server` в
   `/root/.ssh/authorized_keys`. systemd-таймер из пакета — приманка:
   без `systemctl enable` он никогда не стартует.

## How it works

**Чему доверяет система на каждом шаге:**

1. **apt доверяет подписи, а не происхождению репозитория.** GPG
   проверяет целостность `InRelease`, но не «заслуженность» источника:
   добавил чужой ключ в `sources.list` — подписанный мусор ставится как
   свой. Подпись подключом (не первичным) — штатная практика, фильтром
   не служит.
2. **Утилиты доверяют libc-обёрткам.** `ls` не делает `getdents` сам:
   он вызывает `opendir` из подгруженной библиотеки. `ld.so.preload`
   встаёт перед libc в порядке разрешения символов — перехватчик
   решает, какой ответ отдать. Отсюда правило расследования: данные из
   `/proc`, сырого MFT/журналов и сетевого трафика не проходят через
   скомпрометированный слой.
3. **cron доверяет файлам в `/etc/cron.d` без перезапуска**, а root
   доверяет `authorized_keys` — поэтому обе точки дают пережить перезагрузку
   и смену пароля.

**Что собирает C2-канал:** handshake (`host_id` = копия `/etc/machine-id`),
heartbeat, upload почтовых архивов — всё открытым HTTP на 8443, что
Wireshark по умолчанию показывает как TLS («TCP segment of a reassembled
PDU»), пока порт не декодирован как HTTP.

## Impact

- RCE от root при `apt install` без единого интерактивного действия
  жертвы — установка пакета и есть атака.
- Стойкое закрепление: перезагрузка не помогает (cron + authorized_keys),
  смена пароля root не помогает (ключ).
- Эксфильтрация данных: в задаче — почтовые архивы (~50 МБ) на
  `backup.mchost.io:8443`, канал маскирован под «backup tool».
- Антифорензика: руткит прячет свои каталоги от файловых утилит —
  точка опоры расследования остаётся в сетевом дампе и образе диска.

## Defenses

1. **Происхождение репозиториев.** Официальные зеркала; сторонний репозиторий
   — только после аудита и с pinned-версиями. `unattended-upgrades` —
   только из доверенных источников.
2. **Мониторинг целостности.** `/etc/ld.so.preload`, `/etc/cron.d/`,
   `/root/.ssh/authorized_keys`, `sources.list` — в AIDE/auditd watchlist.
   Файл `/etc/ld.so.preload` в нормально настроенной системе пуст или
   отсутствует: любое его появление — инцидент.
3. **Проверка «невидимости».** `ls` и `stat` на подозрительных путях из
   живой системы сверять с Offline-образом (autopsy, `fls` по сырому MFT)
   — расхождение = руткит.
4. **Сетевой egress.** Серверу, который не HTTP-клиент, исходящие 8443
   закрываются политикой; эксфильтрация через «нестандартный порт с
   открытым HTTP» видна даже на дешёвом NetFlow.
5. **Эвристика на maintainer-скрипты.** `postinst`, пишущий в
   `/root/.ssh` и `/etc/ld.so.preload`, — повод смотреть в пакет ДО
   установки (`apt-get download` + `dpkg-deb -e`).

## Why defenses break

- **Аудит есть, но точечный:** следят за `/etc/passwd` и `/etc/shadow`,
  а `ld.so.preload` и `cron.d` не в списке — обход списком наблюдаемых
  путей.
- **Egress закрыт на 80/443, остальное «и так видно»:** 8443 выглядит
  TLS-портом в мониторах, пока кто-то не декодировал трафик.
- **«Мы ставим только подписанные пакеты»:** подпись проверяет автора
  внутри цепочки, а не доверие к цепочке.

## References

- [MITRE ATT&CK T1195 Supply Chain Compromise](https://attack.mitre.org/techniques/T1195/)
- [MITRE ATT&CK T1574.006 LD_PRELOAD](https://attack.mitre.org/techniques/T1574/006/)
- [Debian SecureApt](https://wiki.debian.org/SecureApt)
- [Wireshark: Decode As](https://www.wireshark.org/docs/wsug_html_chunked/ChCustProtocolDecode.html)
- [LD_PRELOAD rootkits: how they work](https://www.nexpose.com/blog/ld-preload-rootkits)
