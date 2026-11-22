# Can YOU handle it?

| | |
|---|---|
| **Платформа / Событие** | liga-ctf-r1-2026 |
| **Категория** | forensics |
| **Сложность** | 643 |
| **Статус** | solved |
| **Дата решения** | 21.11.2026 |
| **Ссылка на таск** | - |

## TL;DR

Программа открыла файл с флагом, **удалила его прямо под открытым
«билетиком»** (хэндлом) и 90 секунд держала содержимое в памяти. Флаг в дампе
ни разу не лежит открытым текстом (0 байт ASCII, 403 приманки в UTF-16) — он
зашифрован XOR с ключом 252. Ключ и смещение процесс сам выдал в своей
командной строке, а содержимое файла осталось в памяти. Ищем в памяти
зашифрованную форму префикса `flag{` (один `grep` по байтам), декодируем:
`flag{w3_h4ndl3_i7_by_n07_h4ndling_i7}`.

**Мини-словарь:**

- **дамп процесса** — «фотография» всей памяти программы в момент снимка;
- **хэндл** — «билетик», который Windows выдаёт программе на открытый файл;
- **маппинг** — способ показать файл как кусок памяти; файл можно удалить,
  а содержимое в памяти останется;
- **UTF-16LE** — как Windows хранит строки: каждый символ в 2 байтах, поэтому
  текст `flag{` в памяти выглядит как `f\x00l\x00a\x00g\x00{\x00`;
- **XOR** — примитивное шифрование: каждый байт смешивается с ключом,
  обратно извлекается тем же ключом;
- **decoy** — приманка.

## Recon

Парадокс CTF-форензики: скрипт-автомат у меня появился в самом конце, когда
руки уже всё потрогали. На реальном заезде так и надо: сначала смотрим файлы
инструментами, и только потом (если хочется) оформляем путь в `solve.py`.
Поэтому ниже — терминал. Python появляется только там, где шелл бессилен:
четыре однострочника (XOR-арифметика и два декода), мини-скрипт поиска MZ
и один блок в самом конце — таблица памяти. Всё это «на коленке».

Инструменты (все есть в Linux / WSL / Git Bash): `file`, `strings`, `grep`,
`od` (или `xxd`), `dd`, `printf`. Плюс HEX-редактор (HxD / 010 Editor) для
«посмотреть глазами» и ILSpy / dnSpy для .NET-сборки, которую мы вырежем из
памяти. Каждая команда ниже выполнялась на этих файлах — выводы настоящие.

### Что за файлы

`file` уже говорит почти всё:

```
$ file *
disk.vhdx:           Microsoft Disk Image eXtended, by Microsoft Windows 10.0.26200.0, sequence 0xa; LOG ...
suspicious_full.dmp: Mini DuMP crash report, 15 streams, Fri Feb 27 22:05:11 2026, 0x20006 type
```

- `disk.vhdx` — образ диска виртуалки (внутри NTFS, можно открыть 7-Zip'ом
  и походить по папкам);
- `suspicious_full.dmp` — **полный дамп памяти процесса** в формате minidump.
  «Full» — значит, вся память процесса целиком. Время в заголовке
  2026-02-27 22:05:11 UTC — старт процесса (совпадает с папкой запуска
  `20260227_140506` из путей, UTC+8).

### Заголовок дампа — байт за байтом

Minidump — это заголовок + «каталог потоков» (здесь «потоки» — не треды ОС,
а секции файла: ThreadList, ModuleList, Memory64List...). Сигнатура и счётчики:

```
$ od -A x -t x1z -N 16 suspicious_full.dmp
000000 4d 44 4d 50 93 a7 f4 a0 0f 00 00 00 20 00 00 00  >MDMP........ ...<
```

Читаем little-endian: сигнатура `MDMP`, по смещению 8 — число потоков `0x0f`
(15 штук), по 0xC — RVA каталога `0x20`. Каждый вход каталога — ровно
12 байт: тип (4) + размер (4) + RVA (4). Смотрим весь каталог:

```
$ od -A x -t x1z -j 32 -N 180 suspicious_full.dmp
000020 03 00 00 00 84 01 00 00 60 06 00 00 04 00 00 00  >........`.......<
000030 90 0a 00 00 f0 07 00 00 0d 00 00 00 6c 3f 08 00  >............l?..<
000040 80 12 00 00 09 00 00 00 70 17 00 00 db 86 08 00  >........p.......<
000050 07 00 00 00 38 00 00 00 d4 00 00 00 0f 00 00 00  >....8...........<
000060 54 05 00 00 0c 01 00 00 15 00 00 00 0c 02 00 00  >T...............<
000070 ec 51 08 00 16 00 00 00 98 00 00 00 f8 53 08 00  >.Q...........S..<
000080 18 00 00 00 34 00 00 00 90 54 08 00 00 00 00 00  >....4....T......<
000090 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  >................<
*
0000d0 00 00 00 00                                      >....<
```

Всё, что нам нужно (остальное — FunctionTable и прочая обвязка):

- `@0x2C` — тип **4 ModuleList**: размер `0xa90` = 4 + 25×108 → 25 модулей,
  лежит с RVA `0x7f0`;
- `@0x44` — тип **9 Memory64List**: размер `0x1770` = 16 + 374×16 → 374
  диапазона памяти, лежит с RVA `0x886db` (понадобится в шаге 6);
- `@0x5C` — тип **15 MiscInfo**: лежит с RVA `0x10c` — там PID:

```
$ od -A x -t x1z -j $((0x10c)) -N 12 suspicious_full.dmp
00010c 54 05 00 00 f7 01 00 00 50 0e 00 00              >T.......P...<
```

Первые поля MiscInfo: размер `0x554`, флаги `0x1f7`, **PID `0x0e50` = 3664**.

### Кто это был — строки

Одна команда — и у нас имя процесса, путь сборки и даже PDB автора:

```
$ strings suspicious_full.dmp | grep -i suspiciousbrief | sort -u
"C:\Users\rcsi\out\author\20260227_140506\bin\SuspiciousBrief.exe" --flag-path ...
C:\Users\rcsi\Desktop\src\SuspiciousBrief\obj\Release\net8.0\win-x64\SuspiciousBrief.pdb
C:\Users\rcsi\out\author\20260227_140506\bin\SuspiciousBrief.dll
SuspiciousBrief
SuspiciousBrief.dll
```

Забавно: первая строка — это **ASCII-копия командной строки** процесса, она
нашлась обычным `strings`. Но не полагаемся на удачу: в Windows командная
строка хранится в PEB в UTF-16LE, поэтому всё же смотрим обе кодировки
(`strings -e l` = 16-bit little-endian, ниже пригодится).

Контекст собран: дамп процесса `SuspiciousBrief.exe` (PID 3664). Судя по
cmdline, процесс держал файл в памяти 90 секунд — и дамп поймал его именно
в этом окне (что и позволило найти флаг в шаге 3). Ищем флаг.

## Steps

### 1. Поиск `flag{` в лоб — 0 в ASCII, 403 приманки

Первый рефлекс — grep по слову. Прогоняем обе кодировки:

```
$ strings suspicious_full.dmp      | grep -c 'flag{'    # 0     — в ASCII нет вообще
$ strings -e l suspicious_full.dmp | grep -c 'flag{'    # 403   — а в UTF-16 есть!
$ strings -e l suspicious_full.dmp | grep -c 'flag{decoy-'  # 403 — и ВСЕ до единого decoy
$ strings -e l suspicious_full.dmp | grep 'flag{' | head -3
flag{decoy-
flag{decoy-
flag{decoy-399-da346df789e2b95a9907}ProgramData\Microsoft\Windows\WER\...
```

(Третья строка склеилась с путём — не пугайтесь: `strings` печатает соседние
UTF-16 строки, стоящие в памяти вплотную, одной строкой. В HxD то же самое:
Ctrl+F → «UTF-16 string» → `flag{` → листаешь сотни совпадений.)

Итого: 400 сгенерированных приманок `flag{decoy-<N>-<hash>}` плюс шаблоны.
Настоящего флага в открытом виде нет вообще. Значит, он зашифрован — и где-то
должна лежать инструкция, как его расшифровать.

### 2. Конфиг процесса лежит в его же памяти

Командная строка запуска всегда остаётся в дампе (PEB), а процесс ещё и сам
собирает себе строку-конфиг. Обе находятся простым grep по UTF-16:

```
$ strings -e l suspicious_full.dmp | grep -F -- '--xor-key' | sort -u
"C:\Users\rcsi\out\author\20260227_140506\bin\SuspiciousBrief.exe" --flag-path "R:\ProgramData\\Microsoft\\Windows\\WER\\ReportQueue\\{7b2c8c2e-6c56-4c73-9f5f-2f5b7d1b0d91}\\cache\telemetry.bin" --hold-seconds 90 --decoy-heap-flags 400 --xor-key 252 --flag-offset 7434 --flag-length 37
--xor-key

$ strings -e l suspicious_full.dmp | grep -F 'cfg:xor=' | sort -u
cfg:xor=252;off=7434;len=37;path=R:\ProgramData\Microsoft\Windows\WER\ReportQueue\{7b2c8c2e-6c56-4c73-9f5f-2f5b7d1b0d91}\cache\telemetry.bin
```

Переводим на человеческий: настоящий флаг — **37 байт** на позиции **7434**
внутри файла `telemetry.bin` (который лежал в `WER\ReportQueue\...` и был
удалён), закодирован XOR ключом **252** (0xFC). Числа из cmdline и из
cfg-строки совпадают — это не случайность, а конфиг.

### 3. Флаг: зашифрованный префикс → один grep → decode

Гениальное в этом таске: флаг ни разу не превращается в строку, поэтому его
нет ни в ASCII, ни в UTF-16. Но XOR обратим — значит, мы сами можем посчитать,
как выглядят первые байты флага после шифрования. Ключ уже у нас (252):

```
$ python3 -c "print(' '.join(f'{b^252:02x}' for b in b'flag{'))"
9a 90 9d 9b 87
```

Ищем эти байты во всём дампе (в HxD: Ctrl+F → тип данных «hex-байты» →
`9A 90 9D 9B 87`):

```
$ LC_ALL=C grep -obUaP '\x9a\x90\x9d\x9b\x87' suspicious_full.dmp
61352789:<байты>
$ printf '0x%x\n' 61352789
0x3a82b55
```

**Грабелька №1:** `LC_ALL=C` — обязательно. В UTF-8-локали `grep -P` матчит
*символы*, а не байты, и любой паттерн с байтами ≥ 0x80 перестаёт находиться.
Флаги: `-o` — только совпадение, `-b` — байтовое смещение, `-U`/`-a` — «это
бинарник, не выбрасывай его».

Ровно **одно** вхождение на все 115 МБ (приманки-то лежали открытым текстом,
их никто не XOR-ил). Смотрим байты глазами и декодируем:

```
$ od -A x -t x1 -j $((0x3a82b55)) -N 37 suspicious_full.dmp
3a82b55 9a 90 9d 9b 87 8b cf a3 94 c8 92 98 90 cf a3 95
3a82b65 cb a3 9e 85 a3 92 cc cb a3 94 c8 92 98 90 95 92
3a82b75 9b a3 95 cb 81

$ python3 -c "f=open('suspicious_full.dmp','rb'); f.seek(0x3a82b55); print(bytes(b^252 for b in f.read(37)).decode())"
flag{w3_h4ndl3_i7_by_n07_h4ndling_i7}
```

(XOR в чистом bash не живёт — это тот момент заезда, когда на 10 секунд
открываешь python REPL. Длина 37 — из `--flag-length`.)

**Флаг получен.** Дальше — проверки и понимание, что это вообще было.

### 4. Сверка с disk.vhdx — бесплатно

Тот же зашифрованный префикс ищем в образе диска:

```
$ LC_ALL=C grep -obUaP '\x9a\x90\x9d\x9b\x87' disk.vhdx
10071306:<байты>
$ printf '0x%x\n' 10071306
0x99ad0a
$ python3 -c "f=open('disk.vhdx','rb'); f.seek(0x99ad0a); print(bytes(b^252 for b in f.read(37)).decode())"
flag{w3_h4ndl3_i7_by_n07_h4ndling_i7}
```

Тот же флаг, сидит и на диске. Арифметика на бумажке даёт красивую деталь:

```
$ python3 -c "o=0x99ad0a-7434; print(hex(o), o % 4096 == 0)"
0x999000 True
```

`0x99ad0a − 7434 = 0x999000` — выровнено на 4 КБ (страница NTFS). Это значит:
флаг лежит ровно на смещении 7434 внутри файла `telemetry.bin`, а сам файл
начинается в образе с `0x999000`. Дамп и диск показывают одно и то же.

### 5. Реверс: вырезаем .NET-сборку из памяти и читаем код

Хочется понять, *зачем* программа удаляла файл. Она на .NET single-file —
сборка запакована внутрь exe и разворачивается в памяти. Метаданные .NET
начинаются с сигнатуры `BSJB`, их в дампе много (системные сборки):

```
$ LC_ALL=C grep -obUaP 'BSJB' suspicious_full.dmp | wc -l
33
```

Находим «нашу» — у каждой сборки в метаданных лежит имя модуля. Цикл: окно
2 страницы вокруг каждого BSJB → `strings` → ищем имя:

```
$ for off in $(LC_ALL=C grep -obUaP 'BSJB' suspicious_full.dmp | cut -d: -f1); do
    dd if=suspicious_full.dmp bs=4096 skip=$((off/4096)) count=2 2>/dev/null \
      | strings | grep -qi suspiciousbrief \
      && printf 'OUR: %d = 0x%x\n' $off $off
  done
OUR: 28252051 = 0x1af1793
```

Ровно один кандидат. Заглянем в окно вокруг него — сразу видно WinAPI-начинку:

```
$ dd if=suspicious_full.dmp bs=1 skip=$((0x1af1793)) count=4096 2>/dev/null | strings | head -14
BSJB
v4.0.30319
#Strings
#GUID
#Blob
ReadOnlySpan`1
List`1
Int32
<Module>
GENERIC_READ
FILE_SHARE_READ
FILE_MAP_READ
FILE_SHARE_DELETE
FILE_SHARE_WRITE
```

`FILE_SHARE_DELETE` и `FILE_MAP_READ` в строках — обещание фокуса с удалением.
Образ сборки начинается с `MZ` где-то до BSJB. Идём назад (в HxD — поиск
назад по `MZ`; в терминале — одной строкой, попутно проверяя PE-заголовок):

```
$ python3 -c "
import struct
d = open('suspicious_full.dmp','rb').read()
b = 0x1af1793                      # наш BSJB
i = d.rfind(b'MZ', b-0x1000, b)    # ближайший MZ назад, в пределах 4 КБ
lfa = struct.unpack_from('<I', d, i+0x3c)[0]   # e_lfanew
print(hex(i), hex(lfa), d[i+lfa:i+lfa+4])
"
0x1af0e4b 0x80 b'PE\x00\x00'
```

Вырезаем и проверяем (`file` сразу скажет, угадали ли с размером):

```
$ dd if=suspicious_full.dmp of=SuspiciousBrief.dll bs=1 skip=$((0x1af0e4b)) count=12288
$ file SuspiciousBrief.dll
SuspiciousBrief.dll: PE32+ executable for MS Windows 4.00 (console), x86-64 Mono/.Net assembly, 2 sections
```

Готовый файл лежит рядом: `SuspiciousBrief_carved.dll`. Открываем в
**ILSpy** или **dnSpy** (перетащить файл, раскрыть `SuspiciousBrief` →
`Program` → `Main`). Декомпилятор показывает ровно то, что обещали строки:

```
1. CreateFileW(telemetry.bin)          открыть файл
2. CreateFileMappingW + MapViewOfFile  показать его как память
3. DeleteFileW(тот же путь)            «удалить» — при живом view!
4. Sleep-цикл ~90 сек                  держать содержимое в памяти
   (+ параллельно сгенерировать 400 приманок flag{decoy-...})
5. UnmapViewOfFile + CloseHandle       и только теперь отпустить
```

Если GUI-тулз под рукой нет, IL можно вытащить и парсером метаданных — но для
решения этот шаг не обязателен: cmdline из шага 2 уже дала всё.

### 6. Бонус: «геометрия» дампа — откуда 7434 в памяти

Самая приятная проверка: смещение 7434 из cmdline должно сойтись с позицией
флага **в памяти процесса**. Для этого переводим файловое смещение `0x3a82b55`
в виртуальный адрес через Memory64List (поток 9, RVA `0x886db` — нашли в
Recon). Формат: число диапазонов, база данных, потом 374 записи «VA + размер»
(данные диапазонов лежат в файле вплотную). Руками в hex-редакторе 374 записи
не листают — вот тут я и сел за скрипт:

```python
import struct
data = open('suspicious_full.dmp','rb').read()
n, dir_rva = struct.unpack_from('<II', data, 8)
streams = {}
for i in range(n):
    t, sz, rva = struct.unpack_from('<III', data, dir_rva + i*12)
    streams.setdefault(t, (sz, rva))

sz, r = streams[9]                                    # Memory64List
nranges, base = struct.unpack_from('<QQ', data, r)    # 374, база данных
ranges, desc = [], r + 16
for _ in range(nranges):
    start, size = struct.unpack_from('<QQ', data, desc); desc += 16
    ranges.append((start, size, base)); base += size

fo = 0x3a82b55                                        # хит из grep
start, size, rva = next((s,z,rv) for s,z,rv in ranges if rv <= fo < rv+z)
va = start + (fo - rva)
print(hex(start), hex(size), hex(va), va - start)
# 0x1f403f00000 0x4000 0x1f403f01d0a 7434
```

Схема сошлась: регион VA `0x1f403f00000` размером `0x4000` — это и есть
отображённый в память `telemetry.bin`, флаг лежит на VA `0x1f403f01d0a`, то
есть со смещением **0x1d0a = 7434** внутри региона — ровно `--flag-offset`
из командной строки. Ответ подтверждён с трёх сторон: содержимое (XOR-скан),
диск (`0x99ad0a` в VHDX), геометрия (VA и смещение в маппинге).

## Why it works

Программа доверяла трём вещам, и все три оказались неверны:

1. **«Удалил файл — данных больше нет».** Windows убирает только имя файла;
   содержимое держится в памяти, пока жив хотя бы один хэндл. Удалять улику
   *под открытым хэндлом* — это не удаление. Хэндл и сдал виновника (название
   таска и флага: «мы обрабатываем это, НЕ обрабатывая это»).
2. **«Секрета в памяти нет, если не делать из него строку».** Байты лежат в
   памяти независимо от строк — поэтому их нашёл байтовый grep, а не поиск
   по слову. А конфиг (ключ, смещения) процесс вообще написал в командную
   строку — она всегда попадает в дампы.
3. **«Приманки замаскируют флаг».** 403 приманки ломают поиск по слову
   `flag{`, но не поиск по *зашифрованному* префиксу: настоящий — ровно один.

## Defense

1. **Правильный порядок закрытия**: сначала `UnmapViewOfFile` + `CloseHandle`
   (секция умирает вместе с последним хэндлом), и только потом удалять файл.
   После чтения секретов — обнулять память (`RtlZeroMemory`).
2. **Не передавать секреты в argv**: ключи и смещения — в конфиг-файле или
   DPAPI. Командная строка навсегда остаётся в дампах и логах (Sysmon и т.п.).
3. **Детектирование у защитников**: связка «создал файл → открыл маппинг →
   тут же удалил» — типичный паттерн сокрытия; полный дамп при инциденте
   снимают *пока процесс жив*, тогда содержимое удалённых файлов в нём есть.

## Artifacts

- `README.md` — этот райтап: решение руками и инструментами
  (strings/grep/od/dd/ILSpy), каждая команда с настоящим выводом;
- `SOLVE_SCRIPT.md` — короткая инструкция к скрипту-автомату;
- `solve.py` — то же решение одним скриптом (параметры из cfg-строки /
  cmdline / брут ключа → XOR-скан → декод; `--disk` сверяет с образом);
- `SuspiciousBrief_carved.dll` — сборка, вырезанная из дампа
  (file offset `0x1af0e4b`), открывается в ILSpy/dnSpy;
- `FLAG.txt` — `flag{w3_h4ndl3_i7_by_n07_h4ndling_i7}`;
- `BEGINNER_GUIDE.md` — то же самое для совсем новичка;
- `EXPLANATION.md` — теория класса «удаление улик при живом хэндле».

## References

- [CreateFileMappingW / MapViewOfFile — как работает маппинг файлов](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-createfilemappinga)
- [Формат minidump (Memory64List)](https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/ns-minidumpapiset-minidump_memory64_list)
- [Breakpad: спецификация minidump](https://chromium.googlesource.com/breakpad/breakpad/+/HEAD/docs/minidump.md)
- [ILSpy — .NET декомпилятор](https://github.com/icsharpcode/ILSpy)
- [Sysmon: события ProcessCreate (1) и FileDelete (23)](https://learn.microsoft.com/en-us/sysinternals/downloads/sysmon)
