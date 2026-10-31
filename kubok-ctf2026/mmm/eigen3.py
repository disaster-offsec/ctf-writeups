#!/usr/bin/env python3
"""Recover exact integer eigenvector: scale ~125, with per-entry correction."""
import struct
import numpy as np

DATA = open('/home/z/my-project/work/mmm', 'rb').read()
Mf = np.array(struct.unpack('<1600q', DATA[0x3220:0x3220 + 12800]), dtype=np.float64).reshape(40, 40)
Mi = Mf.astype(object)

vals, vecs = np.linalg.eig(Mf)
idx = int(np.argmin(np.abs(vals - 1337.0)))
w = np.real(vecs[:, idx])
wn = w / np.max(np.abs(w))

u = [int(round(x * 125)) for x in wn]
print('lam =', vals[idx])
print('u =', u)
print('signs:', ''.join('+' if x >= 0 else '-' for x in u))
print('residuals (x*125 - round):', [f'{x*125 - r:+.3f}' for x, r in zip(wn, u)])

def mv(u):
    return [sum(Mi[i][j] * u[j] for j in range(40)) for i in range(40)]

t = mv(u)
ratios = set()
for k in range(40):
    if u[k]:
        ratios.add((t[k], u[k], t[k] / u[k]))
print('\nratio t[k]/u[k] distinct:', ratios)

# exact check as in binary
ok = all(u[j] * t[k] == t[j] * u[k] for k in range(40) for j in range(k + 1, 40))
print('exact proportionality (binary check):', ok)

# local search correction if needed
if not ok:
    print('\nlocal search on +/-1 per entry (greedy, exact test)...')
    import itertools, random
    best = None
    u0 = u[:]
    for it in range(200):
        improved = False
        for p in range(40):
            for d in (-2, -1, 1, 2):
                v = u0[:]; v[p] += d
                if min(v) < 32 or max(v) > 126: continue
                tt = mv(v)
                # count violations
                viol = sum(1 for k in range(40) for j in range(k+1, 40) if v[j]*tt[k] != tt[j]*v[k])
                if best is None or viol < best:
                    best = viol; u0 = v[:]; improved = True
                    if viol == 0: break
            if best == 0: break
        if best == 0 or not improved: break
    print('best violations:', best)
    print('candidate:', ''.join(chr(c) for c in u0))
    t2 = mv(u0)
    print('exact now:', all(u0[j]*t2[k] == t2[j]*u0[k] for k in range(40) for j in range(k+1,40)))
