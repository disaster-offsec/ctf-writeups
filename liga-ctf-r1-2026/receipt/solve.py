#!/usr/bin/env python3
"""
Receipt (liga-ctf-r1-2026) — стеганография в ошибках Рида-Соломона QR-кода.

Идея: QR на чеке сканируется без проблем, но часть его модулей намеренно
перевёрнута («помарки термопринтера»). Декодер QR молча исправляет их кодами
Рида-Соломона, и величина каждого исправления (принятое XOR исправленное)
оказывается ASCII-символом. Символы, упорядоченные по позиции кодового слова
в чередованном потоке, складываются во флаг.

Зависимости: pip install pillow numpy reedsolo
Опционально: opencv-python (для финальной проверки)
Запуск:      python3 solve.py receipt.png
"""
import sys
import numpy as np
from PIL import Image
from reedsolo import RSCodec, ReedSolomonError

# ---------------------------------------------------------------- 1. Матрица
# Чек — чистый 1-битный PNG 520x520: QR версии 10 (57x57 модулей),
# 8 пикселей на модуль, тихая зона 32 px.
N, PX, OFF = 57, 8, 32

im = np.array(Image.open(sys.argv[1] if len(sys.argv) > 1 else 'receipt.png').convert('L'))
mat = np.zeros((N, N), dtype=int)
for r in range(N):
    for c in range(N):
        block = im[OFF + r * PX:OFF + (r + 1) * PX, OFF + c * PX:OFF + (c + 1) * PX]
        mat[r, c] = 1 if block.mean() < 128 else 0

# Карта функциональных модулей (finder+separator+format, timing, alignment,
# version info, dark module). Центры alignment-паттернов v10 — по сетке.
func = np.zeros((N, N), dtype=bool)
def stamp(r0, c0, h, w): func[r0:r0 + h, c0:c0 + w] = True
stamp(0, 0, 9, 9); stamp(0, N - 8, 9, 8); stamp(N - 8, 0, 8, 9)   # finders + format
stamp(6, 0, 1, N); stamp(0, 6, N, 1)                              # timing
for cy, cx in [(6, 28), (28, 6), (28, 28), (28, 50), (50, 28), (50, 50)]:
    stamp(cy - 2, cx - 2, 5, 5)                                   # alignment
stamp(0, N - 11, 6, 3); stamp(N - 11, 0, 3, 6)                    # version info (v>=7)

# ------------------------------------------------- 2. Format info -> маска
def read_format():
    pos = [(8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
           (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8)]
    f = 0
    for r, c in pos:                       # старший бит первым
        f = (f << 1) | mat[r, c]
    f ^= 0b101010000010010                 # снимаем маску format info
    g = 0b10100110111                      # проверка BCH
    for i in range(14, 9, -1):
        if f & (1 << i):
            f ^= g << (i - 10)
    return f == 0

if not read_format():
    sys.exit('format info не прошёл проверку BCH — сетка снята неверно')
pos = [(8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
       (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8)]
f = 0
for r, c in pos:
    f = (f << 1) | mat[r, c]
f ^= 0b101010000010010
f = int(f)
ec = {0b01: 'L', 0b00: 'M', 0b11: 'Q', 0b10: 'H'}[(f >> 13) & 0b11]
mask_id = int((f >> 10) & 0b111)
print(f'format info: EC level {ec}, маска {mask_id}')
assert ec == 'H', 'ожидаем уровень коррекции H'

def mask_bit(r, c):
    return ((r + c) % 3 == 0) if mask_id == 3 else {
        0: lambda: (r + c) % 2 == 0, 1: lambda: r % 2 == 0,
        2: lambda: c % 3 == 0,       3: lambda: (r + c) % 3 == 0,
        4: lambda: (r // 2 + c // 3) % 2 == 0,
        5: lambda: (r * c) % 2 + (r * c) % 3 == 0,
        6: lambda: ((r * c) % 2 + (r * c) % 3) % 2 == 0,
        7: lambda: ((r + c) % 2 + (r * c) % 3) % 2 == 0}[mask_id]()

# --------------------------- 3. Снять маску, зигзаг, вычитать кодовые слова
u = mat.copy()
for r in range(N):
    for c in range(N):
        if not func[r, c] and mask_bit(r, c):
            u[r, c] ^= 1

order = []                                 # зигзаг: справа налево, колонки парами
col, up = N - 1, True
while col > 0:
    if col == 6:
        col -= 1
    for r in (range(N - 1, -1, -1) if up else range(N)):
        for c in (col, col - 1):
            if not func[r, c]:
                order.append((r, c))
    up = not up
    col -= 2

bits = [u[r, c] for r, c in order]
cw = [int(''.join(map(str, bits[i:i + 8])), 2) for i in range(0, 346 * 8, 8)]
print(f'модулей данных: {len(order)}, кодовых слов: {len(cw)} (v10-H: 122 данных + 224 EC)')

# --------------------------------- 4. Де-чередование: 8 блоков Рида-Соломона
NB, ECN = 8, 28                            # 6 блоков по 15 данных + 2 по 16, 28 EC
db = [[] for _ in range(NB)]; idx = 0
for _ in range(15):
    for b in range(NB):
        db[b].append(cw[idx]); idx += 1
db[6].append(cw[idx]); idx += 1
db[7].append(cw[idx]); idx += 1
eb = [[] for _ in range(NB)]
for _ in range(ECN):
    for b in range(NB):
        eb[b].append(cw[idx]); idx += 1
assert idx == len(cw)

def gindex(b, p):                          # позиция кодового слова в общем потоке
    dlen = 16 if b >= 6 else 15
    if p < dlen:
        return p * 8 + b if p < 15 else 120 + (b - 6)
    return 122 + (p - dlen) * 8 + b

# ------------------------ 5. RS-коррекция: величины ошибок = символы флага
rsc = RSCodec(ECN)
chars, n_flips = [], 0
print('\nисправленные кодовые слова (позиция в потоке: XOR = символ):')
for b in range(NB):
    blk = list(db[b] + eb[b])
    try:
        _, fixed, _ = rsc.decode(bytes(blk))
    except ReedSolomonError:
        print(f'  блок {b}: не декодируется'); continue
    fixed = list(fixed)
    for p in range(len(blk)):
        if blk[p] != fixed[p]:
            x = blk[p] ^ fixed[p]
            gi = gindex(b, p)
            chars.append((gi, x))
            n_flips += bin(x).count('1')
            print(f'  cw#{gi:3d} (блок {b}, поз {p:2d}): {blk[p]:02x}->{fixed[p]:02x}  XOR={x:02x} {chr(x)!r}')

chars.sort(key=lambda t: t[0])
flag = ''.join(chr(x) for _, x in chars)
print(f'\nперевёрнутых модулей всего: {n_flips}')
print('ФЛАГ:', flag)

# ------------------------------------------- 6. Проверка: собрать чистый QR
clean = mat.copy()
for gi, x in chars:                        # к позициям ошибок применяем исправления
    for bit in range(8):                   # bit: индекс модуля, 0 = старший бит слова
        r, c = order[gi * 8 + bit]
        clean[r, c] ^= (x >> (7 - bit)) & 1
big = Image.new('1', (N * PX + 2 * OFF, N * PX + 2 * OFF), 1)
bp = big.load()
for r in range(N):
    for c in range(N):
        v = 0 if clean[r, c] else 1
        for dy in range(PX):
            for dx in range(PX):
                bp[OFF + c * PX + dx, OFF + r * PX + dy] = v
big.save('receipt_clean.png')

try:
    import cv2
    url, _, _ = cv2.QRCodeDetector().detectAndDecode(cv2.imread('receipt_clean.png'))
    print('\nисправленный QR декодируется как:', url)
    print('совпадает с тем, что отдавал сканер:', url != '')
except ImportError:
    print('\n(opencv не установлен — визуальная проверка пропущена)')
