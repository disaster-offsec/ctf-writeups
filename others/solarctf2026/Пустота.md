---
title: "Пустота"
ctf: "SolarCTF"
date: 2026-10-18
category: forensics
flag_format: "SOLARCTF{...}"
---

# Пустота — решение

**Флаг: `SOLARCTF{v01d_l1nuzz_yjs_cv3_buzzw0rd5}`**

## Кратко

Из дампа памяти восстановлены скрытый поток, зашифрованный кэш и удалённое содержимое Yjs-документа. Исторический snapshot вернул правильный ключ, после чего два аутентифицированных AES-GCM-конверта раскрыли ZIP с флагом. Использованы Python 3.12, Node.js, Capstone и Ghidra; финальный скрипт Ghidra не требует.

## Воспроизведение

Нужны Python с `pycryptodome` и Node.js. Скрипт из приложения работает офлайн, не запускает исполняемые файлы из дампа и принимает архив с дампом и путь к **новому** (ещё не существующему) выходному каталогу:

```powershell
python recover.py memory.zip new-reproduction
```

Скрипт проверен повторным полным запуском на исходном архиве.

## Цепочка восстановления

1. `memory.elf` — физическая память Void Linux 6.12.113_1. Таблицы страниц x86-64 восстановлены с DTB `0xb9c2000`; пользовательская память `asrn-sync` читается через `0xb9c0000`.
2. В памяти найден загрузчик `hwsens_aux.ko`. Модуль прячет поток службы: отсоединяет его от списков/идентификаторов и меняет `exit_state`. Сохранённый указатель указывает на `task_struct` по `0xffff8d69af086900`.
3. Из загруженного модуля извлечён маскированный recovery kit: секрет `9b1f4c7ae3d8026516fa4b90c7e3d18f` и метки `asrn-cache:`, `asrn-index:`.
4. В памяти процесса найдены два настоящих фрагмента кэша и пять пар ложных. Настоящие фрагменты по `0x7fa51653f000` и `0x7fa51652e000` проходят FNV-1a-проверки. Сняты XOR/LCG-маска с boot nonce и циклический сдвиг.
5. Кэш расшифрован AES-256-GCM: ключ `sha256("asrn-cache:" + secret_hex)`, первые 12 байт — nonce, последние 16 — тег. Тег успешно проверен.
6. В кэше находятся журнал атаки, исходная и внедрённая записи DLS3, а также двухслойный SND1-конверт. Журнал описывает RCE через `sync-api.jsp`, повышение привилегий через `asrn-restore --apply`, сокрытие потока и подмену адресата на `mira@counse1.example`.
7. Из page cache восстановлены `runtime/core.cjs` (Yjs), `journal.sqlite`, `objects.bin` и WASM-кодек. Реализован обратный DLS3-кодек; CRC32 всех использованных записей проверены.
8. LCV3-цепочки восстановлены по parent digest. Важная ловушка: **в реальных данных digest относится к запечатанному DLS3-конверту родителя**, а не к результату, как утверждает `FORMAT.txt`.
9. Yjs-документ восстанавливается с `gc:false`; исходная запись возвращает удалённый текст. Исторический snapshot из записи №2 выбирает правильные символы ключа из 256-символьного текста. Простое чтение текущего документа, 64-символьные подстроки и текущий сокращённый ключ не подходят.
10. Внешний SND1 открывается ключом `sha256("asrn-wrap:" + wrap_session + secret_hex)`, внутренний — `sha256(historical_dispatch.release_key)`. **Оба тега GCM проверены.** Внутри ZIP найден текстовый файл с флагом.

## Что подтверждено

- Оба тега AES-GCM (внешний и внутренний SND1) успешно проверены `decrypt_and_verify`.
- CRC32 всех использованных DLS3-записей совпали; цепочки LCV3 сходятся по parent digest.
- Флаг извлечён из ZIP, найденного внутри аутентифицированного конверта; повторный прогон скрипта воспроизвёл результат.
- Отправка на платформу соревнования не выполнялась.

## Приложение: скрипт восстановления

Три файла положить в одну папку: `recover.py`, `codec.py`, `history.cjs` (последний `recover.py` сам запускает через Node).

### recover.py

```python
"""Offline recovery for memory.zip. Requires Python, pycryptodome and Node.js.
Usage: python recover.py path/to/memory.zip path/to/new-output-directory
All addresses below are verified addresses in this particular challenge dump.
No challenge native executables are run.
"""
import pathlib,sys,zipfile,mmap,struct,hashlib,json,zlib,re,sqlite3,subprocess
from Crypto.Cipher import AES

archive=pathlib.Path(sys.argv[1]).resolve();out=pathlib.Path(sys.argv[2]).resolve()
out.mkdir(parents=True,exist_ok=False)
with zipfile.ZipFile(archive) as z, z.open('memory.elf') as src, (out/'memory.elf').open('wb') as dst:
 import shutil
 shutil.copyfileobj(src,dst)
f=(out/'memory.elf').open('rb');m=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)
segments=[]
for i in range(struct.unpack_from('<H',m,56)[0]):
 h=struct.unpack_from('<IIQQQQQQ',m,192+i*56)
 if h[0]==1:segments.append((h[4],h[2],h[5]))
def phys(pa,n):
 for p,o,s in segments:
  if p<=pa<p+s:return m[o+pa-p:o+pa-p+n]
 raise ValueError(hex(pa))
def translate(va,dtb):
 t=dtb
 for shift in (39,30,21,12):
  e=struct.unpack('<Q',phys(t+((va>>shift)&511)*8,8))[0]
  assert e&1
  if shift in (30,21) and e&128:return (e&0xffffffffff000&~((1<<shift)-1))+(va&((1<<shift)-1))
  t=e&0xffffffffff000
 return t+(va&4095)
def virt(va,n,dtb=0xb9c2000):
 data=bytearray()
 while n:
  k=min(n,4096-(va&4095));data+=phys(translate(va,dtb),k);va+=k;n-=k
 return bytes(data)
def vq(va):return struct.unpack('<Q',virt(va,8))[0]
def xa(e,idx=0):
 if not e:return
 if e&3==2 and e>0xffff000000000000:
  node=e&~3;shift=virt(node,1)[0]
  for i,child in enumerate(struct.unpack('<64Q',virt(node+40,512))):
   if child:yield from xa(child,idx+(i<<shift))
 elif e&3==0:yield idx,e
def filecache(inode):
 size=vq(inode+80);data=bytearray(size)
 for idx,page in xa(vq(vq(inode+48)+16)):
  pa=((page-0xfffffafcc0000000)//64)*4096
  data[idx*4096:(idx+1)*4096]=phys(pa,4096)
 return bytes(data[:size])
def put(name,data):
 p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);return p
def lcg(s):return (s*1664525+1013904223)&0xffffffff
def fnv(data):
 s=0xcbf29ce484222325
 for c in data:s=((s^c)*0x100000001b3)&0xffffffffffffffff
 return s

# Decode the module's recovery kit; authenticate the encrypted cache.
mask=virt(0xffffffffc0529080,16);kit=virt(0xffffffffc0529040,64);s=0x9e3779b9
for i in range(0,16,4):s=(((s<<5)^(s>>3))^(mask[i]<<24)^(mask[i+3]<<16))&0xffffffff
plain=bytearray()
for i,c in enumerate(kit):s=lcg(s);plain.append(c^mask[i%16]^(s>>24))
secret=plain[:16].hex();assert plain[16:27]==b'asrn-cache:'
salt=virt(0x56328facf200,16,0xb9c0000);buf=bytearray()
for va in (0x7fa51653f000,0x7fa51652e000):
 h=virt(va,4096,0xb9c0000);n=struct.unpack_from('<Q',h,8)[0];part=virt(va+4096,n,0xb9c0000)
 assert fnv(part)==struct.unpack_from('<Q',h,16)[0]
 buf+=part
s=int.from_bytes(salt[:4],'little')^0x2545f491
for i in range(len(buf)):s=lcg(s);buf[i]^=salt[i%16]^(s>>24)
shift=int.from_bytes(salt[:4],'little')%len(buf);buf=buf[-shift:]+buf[:-shift]
key=hashlib.sha256(('asrn-cache:'+secret).encode()).digest()
cache=AES.new(key,AES.MODE_GCM,nonce=buf[:12]).decrypt_and_verify(buf[12:-16],buf[-16:])
header_end=cache.index(b'client=');n=int(cache[:header_end].split(b'story_bytes=')[1].split(b'\n')[0])
story=cache[header_end:header_end+n];put('attack-story.txt',story)
stash=cache[header_end+n:];p=stash.index(b'DLS3');header=stash[:p]
sizes=[int(header.split(x+b'=')[1].split(b'\n')[0]) for x in (b'orig_update_bytes',b'inj_update_bytes',b'envelope_bytes')]
parts=[]
for name,size in zip(('pristine.dls3','injected.dls3','outer.snd1'),sizes):parts.append(stash[p:p+size]);put(name,parts[-1]);p+=size
assert p==len(stash)

# Restore the vendor runtime and record evidence from inode page caches.
for name,inode in [('core.cjs',0xffff8d6981efa3c0),('journal.sqlite',0xffff8d6981eff850),('objects.bin',0xffff8d6981efe0d0)]:put(name,filecache(inode))
c=sqlite3.connect(out/'journal.sqlite')
rows=[dict(seq=a,document_id=b,payload=d.hex()) for a,b,d in c.execute('select seq,document_id,payload from updates order by seq')]
put('updates.json',json.dumps(rows).encode());c.close()
from codec import decode
original=decode(parts[0]);assert original[:4]==b'LCV3' and original[4]==2
result=original[60:];assert zlib.crc32(result)==struct.unpack_from('<I',original,44)[0]
doclen=int.from_bytes(result[:2],'little');put('pristine-yjs.bin',result[2+doclen:])
objects=(out/'objects.bin').read_bytes();p=0;records=[]
while p<len(objects):
 n=int.from_bytes(objects[p:p+4],'little');env=objects[p+4:p+4+n];records.append((env,decode(env)));p+=4+n
known={};pending=list(enumerate(records));chains=[]
while pending:
 count=len(pending)
 for i,(env,rec) in pending[:]:
  parent=rec[8:40].hex();flags=rec[4]
  if flags&1 and parent not in known:continue
  n,crc,pre,suf,ins=struct.unpack_from('<5I',rec,40);old=known[parent] if flags&1 else b''
  value=old[:pre]+rec[60:60+ins]+(old[-suf:] if suf else b'')
  assert len(value)==n and zlib.crc32(value)==crc
  # Actual parent links hash the sealed DLS3 record, unlike FORMAT.txt's claim.
  known[hashlib.sha256(env).hexdigest()]=value
  chains.append(dict(index=i,flags=flags,digest=hashlib.sha256(value).hexdigest(),hex=value.hex()))
  pending.remove((i,(env,rec)))
 assert len(pending)<count
put('chains.json',json.dumps(chains).encode())
subprocess.run(['node',str(pathlib.Path(__file__).with_name('history.cjs')),str(out)],check=True)
def snd(d,key):
 assert d[:4]==b'SND1' and len(d)==40+int.from_bytes(d[20:24],'little')
 return AES.new(key,AES.MODE_GCM,nonce=d[8:20]).decrypt_and_verify(d[40:],d[24:40])
session=re.search(rb'wrap_session=([0-9a-f]+)',story)[1].decode()
inner=snd(parts[2],hashlib.sha256(('asrn-wrap:'+session+secret).encode()).digest())
for view in json.loads((out/'views.json').read_text()):
 release=view['view'].get('dispatch',{}).get('release_key','')
 if not release:continue
 try:package=snd(inner,hashlib.sha256(release.encode()).digest())
 except ValueError:continue
 put('verified-historical.json',json.dumps(view,indent=2).encode());put('package.zip',package)
 with zipfile.ZipFile(out/'package.zip') as z:
  for item in z.infolist():
   if item.file_size>10000000:continue
   data=z.read(item)
   for match in re.finditer(rb'SOLARCTF\{[^}\r\n]{1,200}\}',data):
    flag=match.group().decode();put('flag.txt',(flag+'\n').encode());put('flag-member.txt',data);print(flag)
 break
else:raise RuntimeError('No historical key authenticated the inner envelope')
assert (out/'flag.txt').exists()
```

### codec.py

```python
"""Inverse of the recovered vendor's three-pass DLS3 WASM encoder."""
import struct,zlib
def rol(x,n):
 n%=8
 return ((x<<n)|(x>>(8-n)))&255
def decode(d):
 assert d[:4]==b'DLS3'
 nonce,n,crc=struct.unpack_from('<III',d,8);a=bytearray(d[24:]);assert len(a)==n
 s=nonce^0xa5c31e27;feedback=n+(nonce>>24)+83
 for i in range(n-1,-1,-1):
  s=(s*1664525+1013904223)&0xffffffff;y=a[i]
  a[i]=rol((y-feedback)&255,((s>>16)&7)+1)^(s>>24)
  feedback=y+(i^150)
 for off in range(0,n,16):
  block=a[off:off+16];size=len(block);idx=off//16
  shift=(size+idx*3+((nonce>>((off>>1)&24))&255))%size
  tmp=bytearray(block[(i+shift)%size] for i in range(size))
  if ((nonce>>(idx&31))^idx)&1:tmp.reverse()
  a[off:off+size]=tmp
 s=nonce^0x6d2b79f5;feedback=nonce^(nonce>>16)^167
 for i in range(n):
  s^=(s<<13)&0xffffffff;s^=s>>17;s^=(s<<5)&0xffffffff;y=a[i]
  a[i]=(rol(y^(s>>24),8-(((s>>8)&7)+1)%8)-feedback)&255
  feedback=y+i+61
 assert zlib.crc32(a)==crc
 return bytes(a)
```

### history.cjs

```js
// Recovered Yjs runtime is supplied by recover.py, not installed from npm.
const fs=require('fs'),path=require('path');
const dir=process.argv[2],Y=require(path.resolve(dir,'core.cjs'));
const doc=new Y.Doc({gc:false});
for(const row of JSON.parse(fs.readFileSync(path.join(dir,'updates.json')))) {
 if(row.document_id==='doc-ef6d002186b9fc6ac4758b6a5ad934a2' && row.seq<94)
  Y.applyUpdate(doc,Buffer.from(row.payload,'hex'));
}
Y.applyUpdate(doc,fs.readFileSync(path.join(dir,'pristine-yjs.bin')));
const views=[];
for(const rec of JSON.parse(fs.readFileSync(path.join(dir,'chains.json')))) {
 if(rec.flags===2)continue;
 try {
  const historical=Y.createDocFromSnapshot(doc,Y.decodeSnapshot(Buffer.from(rec.hex,'hex')));
  historical.getMap('dispatch');historical.getArray('comments');
  views.push({index:rec.index,snapshot_digest:rec.digest,view:historical.toJSON()});
 } catch(e) { /* Other documents' snapshots are irrelevant. */ }
}
fs.writeFileSync(path.join(dir,'views.json'),JSON.stringify(views,null,2));
```

## Флаг

```text
SOLARCTF{v01d_l1nuzz_yjs_cv3_buzzw0rd5}
```
