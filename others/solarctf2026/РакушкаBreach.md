# EnergyVHD — "Ракушка Пакетин"

**Категория:** Forensics (Disk / Windows artifacts)
**Файл:** `solar_forensic.zip` → `disk.vhd`
**Флаг:** `SOLARCTF{sh3llb4g_m4nual_pars1ng_is_th3_w4y}`

---

## Легенда

Компания EnergyVHD обнаружила утечку проектной документации по новой солнечной панели.
Инженер Ракушка Пакетин (д. Коршунов) уволен неделю назад; перед уходом удалил папки,
очистил корзину, затёр историю браузера. IT снял образ диска, но инструменты анализа падают.
Нужно восстановить путь утечки и найти доказательство.

---

## 0. Разбор контейнера

```
solar_forensic.zip
└── disk.vhd   (10 514 432 байт)
```

```
$ file disk.vhd
Microsoft Disk Image, Virtual Server or Virtual PC, Creator win a.0 (W2k),
67108864 bytes, CHS 963/8/17
```

Dynamic VHD:

| Структура | Смещение | Значение |
|---|---|---|
| Footer cookie | `0x000` | `conectix` |
| Disk type | `0x03C` | `0x03` (dynamic) |
| Dynamic header | `0x200` | `cxsparse` |
| BAT offset | — | `0x600` |
| Max table entries | — | `32` |
| Block size | — | `0x200000` (2 MiB) |

32 × 2 MiB = 64 MiB — всё согласовано, контейнер целый. «Падают инструменты» относится
к содержимому (см. §3), а не к VHD.

```bash
qemu-img convert -f vpc -O raw disk.vhd disk.raw
```

```
$ fdisk -l disk.raw
Disklabel type: dos      Disk identifier: 0x118f91bb
Device      Boot Start    End  Sectors  Size Id Type
disk.raw1         128 129023   128896 62.9M  7 HPFS/NTFS/exFAT

$ dd if=disk.raw of=part1.img bs=512 skip=128 count=128896
```

NTFS: метка тома `EVIDENCE`, кластер 4096 Б, MFT-запись 1024 Б, `$MFT` с кластера 5370,
16111 кластеров всего.

---

## 1. Обзор файловой системы

```bash
sudo mount -t ntfs3 -o ro,loop part1.img mnt
```

```
Documents/
├── Desktop/notes.txt
├── Desktop/shortcuts/{jira,vpn}.lnk
├── Personal/{todo.txt, vacation_2024.jpg}
└── SolarGrid/
    ├── Designs/{panel_v2_draft.pdf, panel_v3_final.pdf, specs_2024.xlsx}
    ├── Export/{backup_config,drop_link,old_server,shared_drive}.lnk
    ├── Meetings/{notes_jan,notes_feb,standup_template}.docx
    └── Reports/{report_q1,report_q2,report_q3}.xlsx, report_q4_draft.docx
ProgramData/Microsoft/Diagnosis/diag_perfmon.edb   (1 MiB)
Users/d.korshunov/NTUSER.DAT                       (12 KiB)
System Volume Information/WPSettings.dat
```

Корзины нет, удалённых записей в MFT нет (все 73 используемые записи — `flags & 1`).
Проверяем, есть ли что карвить из нераспределённого пространства: собираем runlist'ы всех
`$DATA` / `$INDEX_ALLOCATION` / `$BITMAP` и сравниваем с ненулевыми кластерами образа.

```
unallocated nonzero clusters: 0
```

Ничего. Значит всё спрятано **внутри живых файлов**.

---

## 2. Пароли «на поверхности»

```
$ cat Documents/Desktop/notes.txt
VPN password reset: contact IT
Jira board: SOLAR project

Backup password: s0lar_backup!!            ← приманка, нигде не используется

$ cat Documents/Personal/todo.txt
- Finish panel specs
- Submit Q3 report
- Clean up export folder                   ← намёк на Export/

Export archive password: dr0pp3d_th3_k3y   ← рабочий ключ для §3
```

Цели LNK-ярлыков из `SolarGrid/Export/`:

| LNK | Target |
|---|---|
| `shared_drive.lnk` | `\\fileserver\shared` |
| `old_server.lnk` | `\\172.16.0.1\legacy\archive` |
| `backup_config.lnk` | `\\10.0.0.5\backups\config` |
| **`drop_link.lnk`** | **`\\192.168.50.10\drop\solar_docs`** |

---

## 3. «Падающие инструменты» — NTUSER.DAT

```
$ file Users/d.korshunov/NTUSER.DAT
data                      ← нет магии regf; любой парсер реестра падает
```

```
00000000: 0000 0000 0000 0000 0000 0000 0000 0000  ................
00000010: 0000 0000 3264 5f74 6d33 5f6b 3379 6472  ....2d_th3_k3ydr
...
00000080: 7468 335f 6b33 7964 7230 7070 3364 5f74  th3_k3ydr0pp3d_t
00000090: 6833 5f6b 3379 6472 3070 7033 645f 7468  h3_k3ydr0pp3d_th
```

Файл проXOR-ен повторяющимся ключом. Бо́льшая часть куста реестра — нули, поэтому
**keystream читается глазами**: `dr0pp3d_th3_k3y` (15 байт) — ровно пароль из `todo.txt`.

```python
key = b'dr0pp3d_th3_k3y'
d   = open('NTUSER.DAT', 'rb').read()
dec = bytes(b ^ key[i % 15] for i, b in enumerate(d))
```

После XOR структура куста валидна, но первые `0x14` байт затёрты:

```
0x00  regf-магия       → 00 00 00 00        ЗАТЁРТА
0x04  seq1 / seq2      → 00 00 00 00 ...    ЗАТЁРТЫ
0x0C  timestamp (8 B)  → 00 ...             ЗАТЁРТ
0x14  major = 1
0x18  minor = 5
0x1C  file type = 0 (primary)
0x20  file format = 1
0x24  root cell offset = 0x1A50
0x28  hive bins size   = 0x2000
0x2C  clustering = 1
0x30  "\??\C:\Users\d.korshunov\NTUSER."   (UTF-16)
```

Восстанавливаем заголовок и пересчитываем контрольную сумму
(XOR всех `u32` в диапазоне `0x000..0x1FB`, пишется в `0x1FC`):

```python
import struct
d = bytearray(dec)
d[0:4] = b'regf'
struct.pack_into('<I', d, 4, 1)      # seq1
struct.pack_into('<I', d, 8, 1)      # seq2
struct.pack_into('<Q', d, 12, 0)     # timestamp
cs = 0
for i in range(0, 0x1FC, 4):
    cs ^= struct.unpack_from('<I', d, i)[0]
if cs in (0, 0xFFFFFFFF):
    cs ^= 1
struct.pack_into('<I', d, 0x1FC, cs)
open('ntuser_fixed.dat', 'wb').write(bytes(d))
```

Теперь куст открывается чем угодно: `python-registry`, `hivexsh`, RegRipper, Registry Explorer.

---

## 4. Shellbags: три аномальные записи

Содержимое восстановленного куста:

```
Software\Microsoft\Windows\CurrentVersion\Explorer\Diagnostic
    PerfLogPath = C:\ProgramData\Microsoft\Diagnosis\diag_perfmon.edb   ← указатель на §5

Software\Microsoft\Windows\Shell\BagMRU\0\0\0\0\...
```

BagMRU восстанавливает всё дерево папок, включая `Downloads`, которой на диске уже нет.
Но важнее **форма** shell item'ов.

Нормальная запись (тип `0x31` — каталог/файл):

```
34 00 | 31 | 00 | 00000000 | 1459E051 | 1000 | "USERS\0" | 1E 00 03 00 04 00 EF BE ...
 size   typ  unk   filesize   dosdate   attr    8.3-имя     BEEF0004 extension block
```

Три записи выбиваются из общего ряда: тип ≠ `0x31`, 8.3-имя полностью занулено,
DOS-дата = `FFFFFFFF`, атрибуты = `0000`:

| Элемент | байты 2..13 | 8.3-имя |
|---|---|---|
| `Export` | `07 09 33 09 00 00 FF FF FF FF 00 00` | 10 нулей вместо `EXPORT` |
| `report_q3.xlsx` | `4A 29 91 29 00 00 FF FF FF FF 00 00` | 14 нулей вместо `REPORT~1.XLS` |
| `drop_link.lnk` | `15 23 D1 23 00 00 FF FF FF FF 00 00` | 12 нулей вместо `DROP_L~1.LNK` |

Автоматические парсеры (ShellBags Explorer и аналоги) такие записи молча пропускают или
падают — отсюда и формулировка задания, и сам флаг. Руками же это прямое указание на три
объекта пути утечки: **папка Export → файл report_q3.xlsx → ярлык drop_link.lnk**.

---

## 5. SRUM, замаскированный под diag_perfmon.edb

```
$ file ProgramData/Microsoft/Diagnosis/diag_perfmon.edb
Extensible storage engine DataBase, version 0x620, checksum 0x2014c1c7,
page size 4096, Windows version 10.0
```

Это не perfmon, а **SRUDB.dat** — System Resource Usage Monitor:

```
MSysObjects / MSysObjectsShadow / MSysObjids / MSysLocales
SruDbIdMapTable                            83 записи
{D10CA2FE-6FCF-4F6D-848E-B2E99266FA89}    415  — Application Resource Usage
{DD6636C4-8929-4683-974E-22C046A43763}     96  — Network Data Usage
```

Парсинг (`libesedb-python`):

```python
import pyesedb, struct, datetime

f = pyesedb.file(); f.open('diag_perfmon.edb')

idmap = {}
t = next(x for x in f.tables if x.name == 'SruDbIdMapTable')
for r in t.records:
    v = [r.get_value_data(i) for i in range(r.get_number_of_values())]
    idmap[struct.unpack('<i', v[1])[0]] = v[2].decode('utf-16le').rstrip('\x00')

def ole(b):
    return datetime.datetime(1899, 12, 30) + datetime.timedelta(days=struct.unpack('<d', b)[0])
```

### 5.1 Карта приложений

Среди ~80 легитимных путей (`svchost.exe`, `chrome.exe`, `OUTLOOK.EXE`, …) один выделяется:

```
AppId 78 → C:\Users\d.korshunov\AppData\Local\Temp\solarsync.exe
```

### 5.2 Network Data Usage — сортировка по BytesSent

```
AppId 78   2024-09-15 14:30:20   sent = 50 753 567   recv =      9 937   solarsync.exe
AppId 32   2024-09-16 04:15:40   sent =  3 147 937   recv =  4 642 347   chrome.exe
AppId 32   2024-09-21 08:22:16   sent =  3 147 535   recv = 49 044 141   chrome.exe
AppId 33   2024-10-14 20:13:39   sent =  3 079 121   recv = 43 524 281   firefox.exe
```

**≈48 MiB исходящего против 10 KiB входящего** — на порядок больше любого другого процесса
и с перевёрнутым соотношением sent/recv. Классический признак эксфильтрации.

### 5.3 Application Resource Usage — подтверждение «прочитал → отправил»

```
14:29:07  ForegroundBytesRead = 40 367 637   BytesWritten = 1 605
14:29:20  ForegroundBytesRead = 52 286 828   BytesWritten = 4 885
14:29:47  ForegroundBytesRead = 51 820 186   BytesWritten = 4 858
14:30:01  ForegroundBytesRead = 40 011 467   BytesWritten = 2 358
14:30:28  ForegroundBytesRead = 54 925 014   BytesWritten = 4 804
```

`UserId` во всех записях: `S-1-5-21-1051133241-1255605371-1627168530-1001` (d.korshunov).
Окно эксфильтрации — **2024-09-15 14:29–14:30**.

---

## 6. Доказательство: Alternate Data Stream

Вторая аномальная shellbag-запись указывает на `report_q3.xlsx`.
В MFT-записи №64 — **два** атрибута `$DATA`:

```python
=== record 64 (report_q3.xlsx) ===
  DATA name=''          nonresident  realsize = 1579
  DATA name='metadata'  resident     size     = 44
```

(для сравнения: два `$DATA` есть ещё только у `$BadClus:$Bad`, `$UpCase:$Info`
и `$Repair:$Config` — это штатные системные потоки)

Через обычное монтирование ADS не виден, нужен `ntfs-3g`:

```bash
sudo mount -t ntfs-3g -o ro,loop,streams_interface=windows part1.img mnt
xxd "mnt/Documents/SolarGrid/Reports/report_q3.xlsx:metadata"
```

```
00000000: f9f4 8050 7070 fefd b762 4a00 c6d7 ae25  ...Ppp...bJ....%
00000010: 456c c78f a264 435f f5cb ad63 5102 c4dc  El...dC_...cQ...
00000020: 9378 516c ded3 ff4e 5507 d3c6            .xQl...NU...
```

44 байта шифротекста. Ни `dr0pp3d_th3_k3y`, ни `s0lar_backup!!`, ни их MD5/SHA1/SHA256,
ни RC4 на их основе не подходят. Частотный анализ по длине ключа даёт кандидатов
L = 6 / 12 / 18, но перебор без известного открытого текста бесполезен.

---

## 7. Ключ спрятан в LNK

Known-plaintext атака по формату флага `SOLARCTF{...}`:

```python
ct[:9] ^ b'SOLARCTF{'  ==  aa bb cc 11 22 33 | aa bb cc
```

Keystream повторяется с периодом 6 → ключ `AA BB CC 11 22 33`, то есть **MAC-адрес**.

Этот MAC лежит в `TrackerDataBlock` (signature `0xA0000003`) ярлыка `drop_link.lnk` —
последние 6 байт `DroidFileId` / `BirthDroidFileId` (UUID v1 несёт MAC в node-поле):

```
$ xxd Documents/SolarGrid/Export/drop_link.lnk | tail -5
000000a0: 0003 0000 a058 0000 0000 0000 0057 4f52  .....X.......WOR
000000b0: 4b53 5441 5449 4f4e 3031 0000 00d4 c3b2  KSTATION01......
000000c0: a1f6 e589 17ab 0101 2345 6789 abf0 e8d7  ........#Eg.....
000000d0: c6b5 a3d8 11aa 63aa bbcc 1122 33c4 d3e2  ......c...."3...
000000e0: f1a6 b598 1087 65aa bbcc ddee fff0 e8d7  ......e.........
000000f0: c6b5 a3d8 11aa 63aa bbcc 1122 3300 0000  ......c...."3...
```

У каждого ярлыка свой MAC — выбрать нужный позволяет именно третья аномальная
shellbag-запись:

| LNK | DroidFileId | MAC |
|---|---|---|
| **`drop_link.lnk`** | `f0e8d7c6-b5a3-d811-aa63-aabbcc112233` | **`AA:BB:CC:11:22:33`** |
| `backup_config.lnk` | `...-aa63-deadbeef0001` | `DE:AD:BE:EF:00:01` |
| `old_server.lnk` | `...-aa63-525400123456` | `52:54:00:12:34:56` |
| `shared_drive.lnk` | `...-aa63-001a2b3c4d5e` | `00:1A:2B:3C:4D:5E` |
| `vpn.lnk` | `...-aa63-000000000001` | — |
| `jira.lnk` | `...-aa63-000000000002` | — |

### Расшифровка

```python
ads = open('report_q3.xlsx_metadata', 'rb').read()   # 44 байта
key = bytes.fromhex('aabbcc112233')
print(bytes(c ^ key[i % 6] for i, c in enumerate(ads)).decode())
```

```
SOLARCTF{sh3llb4g_m4nual_pars1ng_is_th3_w4y}
```

---

## Итоговая цепочка утечки

1. `d.korshunov` работает с `SolarGrid\Designs` и `SolarGrid\Reports` — зафиксировано в shellbags (`NTUSER.DAT`).
2. Из `%TEMP%` запускается `solarsync.exe`, читает ~50 MiB проектной документации
   (SRUM Application Resource Usage, 2024-09-15 14:29–14:30).
3. В 14:30:20 отправляет **50 753 567 байт** наружу при 9 937 входящих
   (SRUM Network Data Usage).
4. Точка сброса — `\\192.168.50.10\drop\solar_docs`, ярлык `Export\drop_link.lnk`,
   MAC хоста-приёмника `AA:BB:CC:11:22:33`.
5. Доказательство спрятано в ADS `report_q3.xlsx:metadata` и зашифровано XOR по этому MAC.

## Приёмы антифорензики в задании

| Приём | Что ломает | Обход |
|---|---|---|
| Обнулённая магия `regf` + XOR всего куста | парсеры реестра | keystream виден в зонах нулей; патч заголовка + checksum `0x1FC` |
| Сломанные shell item'ы (тип ≠ `0x31`, 8.3 занулено, дата `FFFFFFFF`) | ShellBags Explorer | ручной разбор структуры BagMRU |
| SRUM переименован в `diag_perfmon.edb` в `Diagnosis\` | эвристики по имени файла | по сигнатуре ESE + именам таблиц-GUID |
| Данные в ADS | `find`/обычное монтирование | второй `$DATA` в MFT, `streams_interface=windows` |
| Ключ в `DroidFileId` LNK | strings-подход | парсинг TrackerDataBlock / known-plaintext |
| Ложный пароль `s0lar_backup!!` | лобовой перебор | — |

## Инструменты

`qemu-img` · `ntfs-3g` (`streams_interface=windows`) · ручной парсер MFT на Python ·
`python-registry` · `libesedb-python` (`pyesedb`) · known-plaintext XOR.
