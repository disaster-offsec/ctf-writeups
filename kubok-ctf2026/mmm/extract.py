#!/usr/bin/env python3
"""Extract MATRIX, FLAG_HASH and SHA-256 tables from the mmm binary."""
import struct

DATA = open('/home/z/my-project/work/mmm', 'rb').read()

# --- SHA-256 K table at 0x3100 (0x100 bytes) ---
K = struct.unpack('<64I', DATA[0x3100:0x3200])
STD_K = [
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]
print('K table standard SHA-256:', 'YES' if list(K) == STD_K else 'NO — modified!')
if list(K) != STD_K:
    for i, (a, b) in enumerate(zip(K, STD_K)):
        if a != b:
            print(f'  K[{i:2d}]: bin={a:#010x}  std={b:#010x}')

# --- init state at 0x3200 (0x20 bytes) ---
init = struct.unpack('<8I', DATA[0x3200:0x3220])
STD_H = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19]
print('init state standard     :', 'YES' if list(init) == STD_H else 'NO — modified!')
if list(init) != STD_H:
    print('  init =', [hex(x) for x in init])

# --- MATRIX at 0x3220: 40x40 int64 ---
M = list(struct.unpack('<1600q', DATA[0x3220:0x3220 + 12800]))
MAT = [M[i*40:(i+1)*40] for i in range(40)]
print('\nMATRIX 40x40 (rows, first 10 cols):')
for i in range(40):
    print('  ', MAT[i][:10])
# stats
flat = M
print('\nvalue range:', min(flat), '..', max(flat))

# --- FLAG_HASH at 0x6420 (up to rodata end 0x6448) ---
fh = DATA[0x6420:0x6448]
print('\nFLAG_HASH bytes (0x6420..0x6448):', fh.hex())
print('as 8 LE u32:', [hex(x) for x in struct.unpack('<8I', fh[:32])])
print('as 8 BE u32:', [hex(x) for x in struct.unpack('>8I', fh[:32])])
