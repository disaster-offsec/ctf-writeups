#!/usr/bin/env python3
"""Final verification: flag candidate, SHA-256, binary's exact checks."""
import struct, hashlib, subprocess

DATA = open('/home/z/my-project/work/mmm', 'rb').read()
Mi = list(struct.unpack('<1600q', DATA[0x3220:0x3220 + 12800]))
MAT = [Mi[i*40:(i+1)*40] for i in range(40)]

u = [-c for c in [-99, -116, -102, -99, -117, -112, -123, -57, -57, -97, -101, -97,
                  -102, -54, -99, -49, -102, -98, -49, -100, -49, -53, -54, -101,
                  -52, -49, -57, -52, -98, -101, -54, -51, -56, -56, -50, -53, -101, -54, -102, -125]]
flag = ''.join(chr(c) for c in u)
print('flag        :', flag)
print('length      :', len(flag))

# 1) binary's check() replicated exactly (integer arithmetic)
t = [sum(MAT[i][j] * u[j] for j in range(40)) for i in range(40)]
prop = all(u[j] * t[k] == t[j] * u[k] for k in range(40) for j in range(k + 1, 40))
nonzero = any(x != 0 for x in t)
print('check()     :', prop and nonzero, '(proportional=%s, Mv!=0=%s, eigenvalue=%s)' % (prop, nonzero, t[0] // u[0]))

# 2) hash_check(): SHA-256 vs FLAG_HASH
target = DATA[0x6420:0x6440]
d = hashlib.sha256(flag.encode()).digest()
print('sha256      :', d.hex())
print('target      :', target.hex())
print('hash_check  :', d == target)

# 3) run the real binary
r = subprocess.run(['/home/z/my-project/work/mmm', flag], capture_output=True, text=True)
print('\nbinary says :', r.stdout.strip(), '| rc =', r.returncode)
