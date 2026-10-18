---
title: "Нейропитомец"
ctf: "SolarCTF"
date: 2026-10-18
category: reverse
flag_format: "SOLARCTF{...}"
---

# Нейропитомец

**Флаг: `SOLARCTF{FR1d0Mp_Sc4n_p4G3s_in_GamEEE}`**

## Кратко

Android Backup содержит APK с зашифрованным скрытым DEX и собственной стековой VM. Статическая расшифровка и воспроизведение скрипта `devroom` восстанавливают четыре части флага без запуска приложения.

## Решение

1. Заголовок `.ab`: `ANDROID BACKUP`, версия `1`, сжатие `1`, шифрование `none`. После четвёртого перевода строки идёт zlib-поток TAR. В нём находится `apps/com.solarlabs.neuropet/a/base.apk`.
2. JADX показывает, что `App.java` расшифровывает `assets/neuro/skin.dat`: первые два байта — little-endian seed; далее `s = (s*1103515245+12345) mod 2^32`, `out = in XOR ((s>>16)&255)`. Восстанавливаются первые четыре байта `dex\n`. Скрытая `LabActivity` вызывает `run("devroom")`. Вход связан с пятью нажатиями за 1500 мс (`Trig.hit`).
3. Ghidra headless декомпилирует `lib/x86_64/libneurocore.so`. `brain.bin` — контейнер NRBC v1: количество скриптов uint16, затем длина имени uint8, имя, seed uint32, размер uint32 и зашифрованный код. Используется тот же LCG. Опкод VM декодируется как `(raw*183)&255`; стековые операции и EMIT воспроизводятся в Python.

Полный автономный решатель (Python 3.12, только stdlib). Он читает исходный `.ab` (или уже распакованный `base.apk`) и печатает флаг:

```python
"""Static neuropet.ab recovery. No challenge code is executed."""
import io
import pathlib
import struct
import sys
import tarfile
import zipfile
import zlib

def lcg_xor(data, seed):
    out = bytearray()
    for b in data:
        seed = (seed * 1103515245 + 12345) & 0xffffffff
        out.append(b ^ ((seed >> 16) & 255))
    return bytes(out)

def recover(path):
    raw = pathlib.Path(path).read_bytes()
    header = raw.split(b'\n', 4)
    assert header[:4] == [b'ANDROID BACKUP', b'1', b'1', b'none']
    with tarfile.open(fileobj=io.BytesIO(zlib.decompress(header[4]))) as tf:
        apk = tf.extractfile('apps/com.solarlabs.neuropet/a/base.apk').read()
    with zipfile.ZipFile(io.BytesIO(apk)) as z:
        brain = z.read('assets/neuro/brain.bin')
        skin = z.read('assets/neuro/skin.dat')
    dex = b'dex\n' + lcg_xor(skin[2:], int.from_bytes(skin[:2], 'little'))[4:]
    assert dex[:8] == b'dex\n038\0'
    assert brain[:6] == b'NRBC\x01\x00'
    pos = 8
    scripts = {}
    for _ in range(int.from_bytes(brain[6:8], 'little')):
        n = brain[pos]; pos += 1
        name = brain[pos:pos+n].decode(); pos += n
        seed, size = struct.unpack_from('<II', brain, pos); pos += 8
        code = lcg_xor(brain[pos:pos+size], seed); pos += size
        scripts[name] = seed, code
        print('script', name, 'seed', hex(seed), 'length', size)
    assert pos == len(brain)
    seed, code = scripts['devroom']
    stack = [0]
    pc = 0
    segments = {}
    for step in range(50_000_000):
        op = (code[pc] * 183) & 255
        pc += 1
        if op == 0x4b:
            print('HALT', step, 'steps')
            break
        elif op == 0x4c:
            stack.append(struct.unpack_from('<I', code, pc)[0]); pc += 4
        elif op == 0x4d: stack.pop()
        elif op == 0x4e: stack.append(stack[-1])
        elif 0x4f <= op <= 0x54 or op == 0x57:
            a, b = stack.pop(), stack.pop()
            v = {0x4f: lambda: a+b, 0x50: lambda: a-b,
                 0x51: lambda: a*b, 0x52: lambda: a^b,
                 0x53: lambda: a << (b&31), 0x54: lambda: a >> (b&31),
                 0x57: lambda: int(a == b)}[op]()
            stack.append(v & 0xffffffff)
        elif op == 0x55:
            n = code[pc] & 7; pc += 1
            a = stack.pop() & 255
            stack.append(((a << n) | (a >> (8-n))) & 255)
        elif op == 0x56:
            stack[-1] = (stack[-1]*1103515245+12345)&0xffffffff
        elif op in (0x58, 0x59):
            dst = struct.unpack_from('<I', code, pc)[0]; pc += 4
            if op == 0x59 or stack.pop() == 0: pc = dst
        elif op == 0x5b:
            slot, size = struct.unpack_from('<BH', code, pc); pc += 3
            data = bytes(v&255 for v in stack[-size:]) if size else b''
            if size: del stack[-size:]
            print('EMIT', slot, repr(data))
            if slot:
                assert slot not in segments
                segments[slot] = data
        else: raise ValueError((hex(op), pc-1))
    else: raise RuntimeError('step limit')
    flag = b''.join(segments[k] for k in sorted(segments))
    print('FLAG:', flag.decode())
    assert len(segments) == 4 and flag.startswith(b'SOLARCTF{') and flag.endswith(b'}')
    return flag

if __name__ == '__main__':
    recover(sys.argv[1])
```

Сохранить код выше как `solve.py`; запуск:

```powershell
python solve.py neuropet.ab
```

Результат:

```text
EMIT 1 b'SOLARCTF{F'
EMIT 2 b'R1d0Mp_Sc4'
EMIT 3 b'n_p4G3s_i'
EMIT 4 b'n_GamEEE}'
HALT 524 steps
FLAG: SOLARCTF{FR1d0Mp_Sc4n_p4G3s_in_GamEEE}
```

Проверка повторена из исходного `.ab` опубликованным решателем. В распакованном APK открытых SOLARCTF-токенов нет; VM формирует один полный токен. На платформу флаг не отправлялся. Пароль для данного незашифрованного backup не требуется.

## Флаг

```text
SOLARCTF{FR1d0Mp_Sc4n_p4G3s_in_GamEEE}
```
