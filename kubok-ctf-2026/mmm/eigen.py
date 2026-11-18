#!/usr/bin/env python3
"""Find integer eigenvector of MATRIX with printable-ASCII entries."""
import struct
import numpy as np

DATA = open('/home/z/my-project/work/mmm', 'rb').read()
M = np.array(struct.unpack('<1600q', DATA[0x3220:0x3220 + 12800]), dtype=np.float64).reshape(40, 40)

vals, vecs = np.linalg.eig(M)
print('eigenvalues (nonzero, distinct-ish):')
for i, v in enumerate(vals):
    print(f'  lam{i:2d} = {v:.4f}' if abs(v.imag) < 1e-9 else f'  lam{i:2d} = {v:.6f}')

print('\n--- real eigenvectors: try to scale into printable ASCII [32..126] ---')
for i in range(40):
    lam = vals[i]
    if abs(lam.imag) > 1e-9 or abs(lam) < 1e-9:
        continue
    w = np.real(vecs[:, i])
    # normalize: first nonzero entry to 1, then look at ratios
    idx = np.argmax(np.abs(w) > 1e-9)
    w = w / w[idx]
    # try to scale so that all entries become integers in [32,126]
    # guess denominator from rational reconstruction of w
    from fractions import Fraction
    fr = [Fraction(x).limit_denominator(10**6) for x in w]
    dens = [f.denominator for f in fr]
    L = 1
    for d in dens:
        L = L * d // np.gcd(L, d)
    iv = [int(round(float(f * L))) for f in fr]
    # check it's a good integer vector
    ok = all(abs(float(f) * L - t) < 1e-3 for f, t in zip(fr, iv))
    g = 0
    for t in iv:
        g = np.gcd(g, abs(t))
    if g:
        iv = [t // g for t in iv]
        L = L // g
    # scale candidates: find s such that all s*iv in [32,126]
    pos = [t for t in iv if t != 0]
    if not pos:
        continue
    smin = max(32 / min(pos), 1) if min(pos) > 0 else -float('inf')
    lo = -float('inf'); hi = float('inf')
    for t in iv:
        if t > 0:
            lo = max(lo, 32 / t); hi = min(hi, 126 / t)
        elif t < 0:
            lo = max(lo, -126 / -t); hi = min(hi, -32 / -t)  # s*t in [32,126] -> s in [126/t,32/t] for t<0
        else:
            continue
    # recompute properly
    lo = -float('inf'); hi = float('inf')
    for t in iv:
        a, b = 32 / t, 126 / t
        if a > b: a, b = b, a
        lo = max(lo, a); hi = min(hi, b)
    if lo <= hi and ok:
        s = int(np.ceil(lo))
        cand = [t * s for t in iv]
        txt = ''.join(chr(c) for c in cand)
        print(f'lam={lam:.4f} scale={s} -> {txt!r}')
