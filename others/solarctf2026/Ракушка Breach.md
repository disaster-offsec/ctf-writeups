---
title: "Ракушка Breach"
ctf: "SolarCTF"
date: 2026-10-17
category: forensics
flag_format: "SOLARCTF{...}"
---

# Ракушка Breach

**Флаг: `SOLARCTF{sh3llb4g_m4nual_pars1ng_is_th3_w4y}`**

## Кратко

В архиве — образ диска `disk.vhd` (динамический VHD, ~10.5 МБ). Образ разворачивается в raw вручную, далее вручную разбирается NTFS: записи MFT, атрибуты, runlist'ы и альтернативные потоки данных (ADS). Флаг лежал в XOR-зашифрованном ADS `metadata` отчёта `report_q3.xlsx`. Побочно восстановлены NTUSER.DAT (реестр с ShellBags, тот самый «ручной разбор») и база SRUM с сетевыми записями.

## 1. Триаж

- `solar_forensic.zip` → `disk.vhd`, 10 514 432 байт; в конце — футер `conectix` (Microsoft Virtual Hard Disk), в заголовке — `cxsparse` (динамический тип).
- Строки образа сразу задают сценарий: `Jira board: SOLAR project`, `Export archive password: dr0pp3d_th3_k3y`, `\\192.168.50.10\drop\solar_docs`, PDF «SolarGrid Panel v2/v3».
- Подписей `NTFS`/`FILE` по смещениям мало: динамический VHD хранит данные по блокам, нужен ручной разворот. Никаких монтирований и сторонних утилит не потребовалось — только Python.

## 2. Разворот VHD → raw

У динамического VHD: в конце футер `conectix`, в заголовке со смещения 512 — big-endian поля: смещение dyn-таблицы (BAT), число блоков, размер блока; в BAT по каждому блоку — сектор данных и при наличии sector-bitmap. Собираем 64 МБ raw-образа:

```python
from pathlib import Path
import struct,json
d = Path('disk.vhd').read_bytes()
table = struct.unpack_from('>Q', d, 512+16)[0]
n, bs = struct.unpack_from('>II', d, 512+28)
bitmap = ((bs//512+7)//8+511)//512*512
raw = bytearray(struct.unpack_from('>Q', d, 48)[0])
for i in range(n):
    sector = struct.unpack_from('>I', d, table+4*i)[0]
    if sector != 0xffffffff:
        start = sector*512
        for s in range(bs//512):
            if d[start+s//8] & (0x80 >> (s % 8)):
                a = i*bs + s*512
                if a < len(raw):
                    raw[a:a+512] = d[start+bitmap+s*512:start+bitmap+(s+1)*512]
```

## 3. Ручной разбор NTFS

MBR → раздел NTFS; из boot sector берём размер сектора/кластера и `$MFT`. Далее вручную: применение USA-fixup к каждой записи MFT, обход атрибутов `0x30` (имена) и `0x80` (данные), разбор runlist'ов (обычных и разреженных). Потоки сохраняем как отдельные файлы; именованные потоки (ADS) получают суффикс имени.

```python
def runs(buf):
    pos = 0; lcn = 0
    while pos < len(buf) and buf[pos]:
        a = buf[pos] & 15; b = buf[pos] >> 4; pos += 1
        count = int.from_bytes(buf[pos:pos+a], 'little'); pos += a
        delta = int.from_bytes(buf[pos:pos+b], 'little', signed=True); pos += b
        lcn += delta
        yield lcn, count, b == 0

def contents(attr):
    if not attr[8]:
        return attr[u16(attr,20):u16(attr,20)+u32(attr,16)]
    size = u64(attr,48); res = bytearray()
    for lcn, count, sparse in runs(attr[u16(attr,32):]):
        res.extend(bytes(count*cs) if sparse else raw[part+lcn*cs:part+(lcn+count)*cs])
        if len(res) >= size: break
    return bytes(res[:size])
```

(полный скрипт — в приложении). Восстановлено 80+ потоков. Среди них документы пользователя `d.korshunov` (SolarGrid): `notes.txt`, `todo.txt`, `jira.lnk`, `vpn.lnk`, `panel_v2_draft.pdf`, `panel_v3_final.pdf`, `specs_2024.xlsx`, `backup_config.lnk`, `drop_link.lnk`, `report_q1.xlsx`–`report_q4_draft.docx`, `NTUSER.DAT`, ESE-база SRUM. У `report_q3.xlsx` обнаружен **альтернативный поток данных** `metadata` (44 байта).

## 4. Флаг: XOR в ADS

Содержимое 44-байтового ADS — XOR с ASCII-ключом `aabbcc112233`:

```python
from pathlib import Path
c = Path('064_metadata.bin').read_bytes()
key = b'aabbcc112233'
out = bytes(x ^ key[i % len(key)] for i, x in enumerate(c))
print(out.decode())      # SOLARCTF{sh3llb4g_m4nual_pars1ng_is_th3_w4y}
```

Ключ найден перебором коротких кандидатов (строки-пароли из образа, типовые MAC-подобные значения вида `aabbcc112233`); вариант XOR «сырым» ключом даёт ровно один осмысленный результат, начинающийся с `SOLARCTF{` и заканчивающийся `}`. Полный перебор ключа и проверка — в приложении.

## 5. Побочные находки (подтверждают сценарий)

- **NTUSER.DAT** (запись MFT 68) в образе тоже обфусцирован: циклический XOR с фазой по ключу `dr0pp3d_th3_k3y` («Export archive password» из строк). После снятия маски видно сигнатуры `regf`/`hbin`; вручную разбирая ячейки hive, доходим до ветки `Software/Microsoft/Windows/Shell/BagMRU` и порядка `MRUListEx`:

```python
def cell(off):                      # ячейка hive по смещению
    p = 0x1000 + off
    return b[p+4:p+abs(struct.unpack_from('<i', b, p)[0])]
```

  Восстанавливается дерево: `C:\Users\d.korshunov\` → `Documents`, `Desktop`, `Downloads`, `SolarGrid\Designs` (`panel_v2_draft.pdf`, `panel_v3_final.pdf`, `specs_2024.xlsx`), `SolarGrid\...\Reports` (`report_q1.xlsx`, `report_q3.xlsx`, `report_q2.xlsx`, `report_q4_draft.docx`), `Export`, `Meetings`. Именно на этот ручной разбор ShellBag намекает текст флага.
- **SRUM (SRUDB.dat)**: в ESE-таблицах есть записи сетевой активности; отдельная запись (GUID `a1c3e5f7-2b4d-6f8a-0c2e-4a6b8c0d2e4f`, время `2024-09-15T14:30:20`) отправила наружу ~50 МБ (50 753 567 байт, получено 9 937). В строках образа рядом встречается `C:\Users\d.korshunov\AppData\Local\Temp\solarsync.exe` — след утилиты выгрузки.

## 6. Вывод

Задание полностью строится на ручном разборе форматов: динамический VHD → NTFS (MFT, runlist'ы, ADS) → XOR. Автор даже подсказал это в тексте флага: `manual parsing is the way`. Дополнительный путь через реестр (ShellBags) и SRUM подтверждает сценарий, но для получения флага достаточно аккуратного разбора ADS.

## Приложение: полный скрипт (VHD → NTFS → потоки)

```python
from pathlib import Path
import struct,json
W=Path('.')
d=(W/'disk.vhd').read_bytes()
u16=lambda b,o:struct.unpack_from('<H',b,o)[0]
u32=lambda b,o:struct.unpack_from('<I',b,o)[0]
u64=lambda b,o:struct.unpack_from('<Q',b,o)[0]
table=struct.unpack_from('>Q',d,512+16)[0]
n,bs=struct.unpack_from('>II',d,512+28)
bitmap=((bs//512+7)//8+511)//512*512
raw=bytearray(struct.unpack_from('>Q',d,48)[0])
print('VHD BAT',table,n,bs,'bitmap',bitmap,'size',len(raw))
for i in range(n):
    sector=struct.unpack_from('>I',d,table+4*i)[0]
    if sector!=0xffffffff:
        start=sector*512
        # Respect sector bitmap.
        for s in range(bs//512):
            if d[start+s//8] & (0x80>>(s%8)):
                a=i*bs+s*512
                if a<len(raw):raw[a:a+512]=d[start+bitmap+s*512:start+bitmap+(s+1)*512]
(W/'disk.raw').write_bytes(raw)
print('MBR partitions',raw[446:510].hex())
part=u32(raw,454)*512
if raw[3:7]==b'NTFS':part=0
b=raw[part:part+512]
ss=u16(b,11);cs=ss*b[13]; mft=u64(b,48)*cs+part
rs=int.from_bytes(b[64:65],'little',signed=True);rs=(1<<-rs) if rs<0 else rs*cs
print('NTFS',part,'sector',ss,'cluster',cs,'mft',mft,'record',rs)
out=W/'recovered';out.mkdir(exist_ok=True)
records={}
def runs(buf):
    pos=0;lcn=0
    while pos<len(buf) and buf[pos]:
        a=buf[pos]&15;b=buf[pos]>>4;pos+=1
        count=int.from_bytes(buf[pos:pos+a],'little');pos+=a
        delta=int.from_bytes(buf[pos:pos+b],'little',signed=True);pos+=b
        lcn+=delta
        yield lcn,count,b==0
def contents(attr):
    if not attr[8]:return attr[u16(attr,20):u16(attr,20)+u32(attr,16)]
    size=u64(attr,48);res=bytearray()
    for lcn,count,sparse in runs(attr[u16(attr,32):]):
        res.extend(bytes(count*cs) if sparse else raw[part+lcn*cs:part+(lcn+count)*cs])
        if len(res)>=size:break
    return bytes(res[:size])
for idx in range(256):
    rec=bytearray(raw[mft+idx*rs:mft+(idx+1)*rs])
    if rec[:4]!=b'FILE':
        if any(rec):print('BAD record',idx,rec[:16].hex())
        continue
    usa=u16(rec,4);cnt=u16(rec,6)
    if usa+cnt*2>len(rec):print('BAD USA',idx,usa,cnt);continue
    for s in range(1,cnt):rec[s*ss-2:s*ss]=rec[usa+2*s:usa+2*s+2]
    pos=u16(rec,20);attrs=[];names=[];streams=[]
    while pos+16<=len(rec):
        typ=u32(rec,pos)
        if typ==0xffffffff:break
        length=u32(rec,pos+4)
        if length<24 or pos+length>len(rec):print('BAD ATTR',idx,pos,hex(typ),length);break
        a=rec[pos:pos+length];aname=a[u16(a,10):u16(a,10)+a[9]*2].decode('utf-16le',errors='replace') if a[9] else ''
        if typ==0x30:
            v=contents(a);names.append((u64(v,0)&0xffffffffffff,v[66:66+v[64]*2].decode('utf-16le',errors='replace')))
        if typ==0x80:
            val=contents(a);fname=f'{idx:03d}'+('_'+aname.replace(':','_') if aname else '')+'.bin'
            (out/fname).write_bytes(val);streams.append((aname,len(val),fname))
        attrs.append((hex(typ),aname,bool(a[8])))
        pos+=length
    records[idx]={'flags':u16(rec,22),'names':names,'streams':streams,'attrs':attrs}
for idx,r in records.items():print(idx,json.dumps(r,ensure_ascii=False))
(W/'records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf8')
```

## Приложение: перебор ключа к ADS

```python
from pathlib import Path
import hashlib,itertools,struct,uuid
from Crypto.Cipher import ARC4,AES
W=Path('.')
c=(W/'recovered/064_metadata.bin').read_bytes()
words=['dr0pp3d_th3_k3y','aabbcc112233','aa:bb:cc:11:22:33','AA:BB:CC:11:22:33','AABBCC112233','50753567','solarsync.exe','192.168.50.10',r'\\192.168.50.10\drop\solar_docs','report_q3.xlsx','a1c3e5f7-2b4d-6f8a-0c2e-4a6b8c0d2e4f','2024-09-15T14:30:20']
def test(k,label):
 for h in [lambda x:x,lambda x:hashlib.md5(x).digest(),lambda x:hashlib.sha1(x).digest(),lambda x:hashlib.sha256(x).digest(),lambda x:hashlib.sha256(x).hexdigest().encode()]:
  key=h(k)
  if not key:continue
  for typ,out in [('xor',bytes(x^key[i%len(key)] for i,x in enumerate(c))),('rc4',ARC4.new(key).decrypt(c))]:
   if out.startswith(b'SOLAR') or b'CTF{' in out:
    print('SUCCESS',label,key,typ,out);(W/'flag.txt').write_bytes(out)
for w in words:test(w.encode(),w)
for mac in ['aabbcc112233','deadbeef0001','525400123456','001a2b3c4d5e']:
 test(bytes.fromhex(mac),mac)
for n in range(2,4):
 for ws in itertools.permutations(words[:7],n):
  for sep in ['',':','|','_','-']:
   w=sep.join(ws);test(w.encode(),w)
test(struct.pack('<Q',50753567),'sent little endian')
test(struct.pack('>Q',50753567),'sent big endian')
```

## Флаг

```text
SOLARCTF{sh3llb4g_m4nual_pars1ng_is_th3_w4y}
```
