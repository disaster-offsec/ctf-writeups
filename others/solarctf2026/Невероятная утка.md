---
title: "Невероятная утка (Unreal Duck)"
ctf: "SolarCTF"
date: 2026-10-18
category: reverse
difficulty: medium-hard
flag_format: "solarctf{...}"
---

# Невероятная утка

**Флаг: `solarctf{unr34l_3ng1n3_p4th_f1nding_0n_w1nd0ws}`**

## Summary

Unreal Engine игра с зашитым в нативный код скрытым маршрутом. В pak-контенте ничего нет: три невидимые зоны и финиш спавнятся конструктором `APawn*-GameMode` (адрес `0x144387770`) в рантайме по мировым координатам. Игрок должен попасть в каждую зону и, стоя в ней, набрать скрытое 5-буквенное слово; на выходе из зоны клиент кадрирует статистику ввода в 32-битный хеш и сверяет его с константой профиля. Три верных кадра → ник **золотеет** (ready) → вход на финиш отдаёт награду. Слова восстановлены не словарём, а полным анализом криптоподобного преобразования фрейма + z3: **ILOVE / DUCKS / ALOTT** («i love ducks a lot»).

## Solution

### Step 1 — Разведка: маршрут живёт в нативном коде, не в ассетах

- Контент распакован (BootFlow/AssetDump), в ассетах флага/маршрута нет.
- Нативный конструктор GameMode `0x144387770` спавнит 3 `SessionVolume` и `SessionEndpoint`:

| ID | Центр мира (X,Y,Z) | Слово |
|----|--------------------|-------|
| 0  | −1900, −1900, 540  | ILOVE |
| 1  | −1900, +1900, 540  | DUCKS |
| 2  | +1900, +1900, 540  | ALOTT |
| финиш | +1900, −1900, 540 | — |

  Half-extent объёмов `(1000,1000,260)` → зона активна по Z в диапазоне 280…800, поэтому стоять нужно на угловой платформе, а не на нижнем полу.

### Step 2 — Механика ввода и криптокадр

Логика в `AChickenPlayerController` (shipping, без символов):
- буфер «печатной машинки» до 5 букв A–Z (IE_Pressed, нормализация caps-состояния);
- `CapsLock` один раз чистит буфер и снимает seal (байт +2048);
- пятая буква «запечатывает» кадр; на выходе из зоны к `ServerRecordFrame` уходит результат, он же пишется в `outputs[id]` (адрес +2000);
- верность кадра: `mismatch[id] = outputs[id] ^ expected[id] == 0`;
- ready = все 3 id посещены AND все mismatch==0 → ник — цвет `0xFFFFD748`.
- Профиль (3 записи по 28 байт: `N4,I2,E0,P7,X1,K5,D3,V6`) инициализируется в `DuckGameInstance::Init` (`0x1443808DA`) константами `key=0x2f6cb09a, salt=0x2fd2eee2, seed=0x2972e958`; target каждой записи — поле `D3`.

Преобразование кадра (перевёрнуто из нативного кода):

```python
M = 0xffffffff
def rol(x, n): x &= M; return ((x << n) | (x >> (32 - n))) & M
def token(c):                       # буква -> 6-bit
    r = ((KEY ^ 0xE5) + 27 * (1 - ord(c))) & 63
    return (13 * (r ^ (r >> 3)) + 17) & 63
def state(word):
    packed = roll = 0
    for c in word:
        t = token(c)
        packed = ((packed << 6) | t) & 0x3fffffff
        roll = (rol(roll ^ ((t + 1) * 0x54E31F9B), 7) + 0x2C8B91EF) & M
    combined = ((packed * 0x1F5D3B79) ^ rol((packed ^ roll) + 0x7B642D11, 9)) & M
    return packed, roll, combined
def evaluate(rec, word):
    s, h, c = state(word)
    mix = (rol(rec.P7 + c, 11) ^ rol(rec.V6 + s, 5)) + (rec.K5 ^ h)
    return ((rol(rec.N4 ^ mix, 7) + (rec.V6 ^ rol(rec.P7, 3)))
            ^ rol(rec.K5 + s + 0x36D5E22B, 13)) & M
```

Проверка кадра: `evaluate(record, word) == record.D3`.

### Step 3 — z3-солвер и извлечение слов

Полный солвер — в приложении A (зависимости: `pefile`, `z3-solver`). Скелет решения:

```python
import z3
ts = [z3.BitVec(f"t{i}", 6) for i in range(5)]
s = z3.SolverFor("QF_BV")
for t in ts: s.add(z3.Or([t == token(chr(65 + n)) for n in range(26)]))
h = packed = z3.BitVecVal(0, 32)
for t in ts:
    v = z3.ZeroExt(26, t)
    packed = (packed << 6) | v
    h = z3.RotateLeft(h ^ ((v + 1) * 0x54E31F9B), 7) + 0x2C8B91EF
combined = (packed * 0x1F5D3B79) ^ z3.RotateLeft((packed ^ h) + 0x7B642D11, 9)
mix = (z3.RotateLeft(P7 + combined, 11) ^ z3.RotateLeft(V6 + packed, 5)) + (K5 ^ h)
out = (z3.RotateLeft(N4 ^ mix, 7) + (V6 ^ rol(P7, 3))) ^ z3.RotateLeft(K5 + packed + 0x36D5E22B, 13)
s.add(out == D3)          # D3 = 0xB2DCBF59 / 0x2523AB39 / 0xB01E4F4D
```

Результат — единственные 5-буквенные решения для каждой записи:
**ID0 → ILOVE, ID1 → DUCKS, ID2 → ALOTT** (кросс-проверка полным перебором 26⁵ и интерпретатором инструкций — совпадение с z3).

### Step 4 — Проход в игре (проверенный порядок для получения награды)

1. Респавн/старт в арене. Отправиться в угол **ID0** (−X,−Y), подняться на платформу.
2. В зоне, отпустив движение: один раз **CapsLock** → набрать **I L O V E** (англ. раскладка, не в чате, без Enter). Покинуть зону, выйти на центральную круглую площадку.
3. Повторить для **ID1** (−X,+Y): CapsLock → **D U C K S** → вернуться в центр.
4. Повторить для **ID2** (+X,+Y): CapsLock → **A L O T T** → вернуться в центр.
5. Убедиться по окну диагностики, что ник готов (ready/золотой).
6. Выйти на **финиш** (+X,−Y) — получена награда.

Ловушки, подтверждённые живыми проверками:

- **Повторный вход в уже зачётную зону перезаписывает её кадр текущим буфером** (даже по пути через угол с пустым буфером — буквами WASD). Поэтому отработавшие зоны обходить стороной.
- Направления камеры не совпадают с осями мира — координаты важнее «лево/право».
- Буфер чистится только CapsLock; Enter/Tab/чат на маршрут не влияют.

### Step 5 — Диагностика read-only (опционально, идеально для валидации)

Окно-миникарта поверх игры (только `ReadProcessMemory`, 5 Гц): позиция утки, живые центры зон, статус зачёта каждого слова (зелёный/красный), текущий ввод, флаг ready (золотой ник). Диагностика полностью read-only и не влияет на игру.

## Flag

Награда финиша — окно «Message received» с рукописным текстом. Приписки на картинке («all lowercase» — все буквы строчные; «кря-кря» — шутка рисующего утка, decoy) учтены: флаг в нижнем регистре.

```text
solarctf{unr34l_3ng1n3_p4th_f1nding_0n_w1nd0ws}
```

## Приложение A — полный солвер фреймов

```python
from pathlib import Path
import struct,json,hashlib,time,sys
import pefile,z3

# Путь внутри папки игры:
EXE=Path('UnrealDuck/Binaries/Win64/UnrealDuckClient-Win64-Shipping.exe')
d=EXE.read_bytes();pe=pefile.PE(data=d,fast_load=True);base=pe.OPTIONAL_HEADER.ImageBase
def memory(a,n):
    p=pe.get_offset_from_rva(a-base);return d[p:p+n]

# Literal scalar stores and two RIP-relative xmm loads in DuckGameInstance::Init.
raw=bytearray(84)
struct.pack_into('<IBBHII',raw,0,0x6f37aa0b,0,0,0,0x112bb232,0x29b1711a)
raw[16:32]=memory(0x14711a990,16)
struct.pack_into('<HHIIIIIIHH',raw,32,1,0,0x42413596,0x73257244,0x57d52250,0x2523ab39,0x203585fc,0x2f48611f,2,0)
raw[64:80]=memory(0x14711aaf0,16)
struct.pack_into('<I',raw,80,0x2b74299a)
records=[]
for pos in range(0,84,28):
    n4,i2,e0,pad,p7,x1,k5,d3,v6=struct.unpack_from('<IBBHIIIII',raw,pos)
    records.append(dict(N4=n4,I2=i2,E0=e0,P7=p7,X1=x1,K5=k5,D3=d3,V6=v6))
assert [r['I2'] for r in records]==[0,1,2]
profile=dict(key=0x2f6cb09a,salt=0x2fd2eee2,seed=0x2972e958,records=records,raw=raw.hex(),exe_sha256=hashlib.sha256(d).hexdigest())
Path('profile.json').write_text(json.dumps(profile,indent=2),encoding='utf8')

M=0xffffffff
def rol(x,n):x&=M;return ((x<<n)|(x>>(32-n)))&M
def token(c):
    r=((profile['key']^0xe5)+27*(1-ord(c)))&63
    return (13*(r^(r>>3))+17)&63
def state(word):
    packed=roll=combined=0
    for c in word:
        t=token(c)
        packed=((packed<<6)|t)&0x3fffffff
        roll=(rol(roll^((t+1)*0x54e31f9b),7)+0x2c8b91ef)&M
        combined=((packed*0x1f5d3b79)^rol((packed^roll)+0x7b642d11,9))&M
    return packed,roll,combined
def evaluate(r,word):
    s,h,c=state(word)
    mix=(rol(r['P7']+c,11)^rol(r['V6']+s,5))+(r['K5']^h)
    out=(rol(r['N4']^mix,7)+(r['V6']^rol(r['P7'],3)))^rol(r['K5']+s+0x36d5e22b,13)
    return out&M

def solve_record(r,timeout=90000):
    # Each variable represents a 6-bit transformed letter, not a network byte.
    ts=[z3.BitVec(f't{r["I2"]}_{i}',6) for i in range(5)]
    letters={token(chr(65+n)):chr(65+n) for n in range(26)}
    assert len(letters)==26
    solver=z3.SolverFor('QF_BV');solver.set(timeout=timeout)
    for t in ts:solver.add(z3.Or([t==v for v in letters]))
    packed=z3.BitVecVal(0,32);h=z3.BitVecVal(0,32)
    for t in ts:
        v=z3.ZeroExt(26,t)
        packed=((packed<<6)|v)&0x3fffffff
        h=z3.RotateLeft(h^((v+1)*0x54e31f9b),7)+0x2c8b91ef
    c=(packed*0x1f5d3b79)^z3.RotateLeft((packed^h)+0x7b642d11,9)
    mix=(z3.RotateLeft(r['P7']+c,11)^z3.RotateLeft(r['V6']+packed,5))+(r['K5']^h)
    out=(z3.RotateLeft(r['N4']^mix,7)+(r['V6']^rol(r['P7'],3)))^z3.RotateLeft(r['K5']+packed+0x36d5e22b,13)
    solver.add(out==r['D3'])
    start=time.monotonic();status=solver.check()
    result={'id':r['I2'],'status':str(status),'seconds':time.monotonic()-start}
    if status==z3.sat:
        model=solver.model();word=''.join(letters[model[t].as_long()] for t in ts)
        actual=evaluate(r,word);assert actual==r['D3']
        result.update(word=word,actual=hex(actual),target=hex(r['D3']),state=list(map(hex,state(word))))
    return result

if __name__=='__main__':
    results=[]
    print('PROFILE',json.dumps(profile),flush=True)
    for r in records:
        result=solve_record(r);print(json.dumps(result),flush=True);results.append(result)
        Path('smt_results.json').write_text(json.dumps(results,indent=2),encoding='utf8')
```
