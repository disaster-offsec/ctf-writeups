#!/usr/bin/env python3
"""Find the integer ASCII eigenvector of MATRIX (exact integer verification)."""
import struct
import numpy as np

DATA = open('/home/z/my-project/work/mmm', 'rb').read()
Mf = np.array(struct.unpack('<1600q', DATA[0x3220:0x3220 + 12800]), dtype=np.float64).reshape(40, 40)
Mi = Mf.astype(object)  # exact integer matrix

def exact_eigvec_check(u):
    """Replicates the binary's check(): M·u proportional to u, nonzero."""
    t = [sum(Mi[i][j] * u[j] for j in range(40)) for i in range(40)]
    if all(x == 0 for x in t):
        return None
    # all pairs k<j: u[j]*t[k] == t[j]*u[k]
    for k in range(40):
        for j in range(k + 1, 40):
            if u[j] * t[k] != t[j] * u[k]:
                return None
    lam = None
    for k in range(40):
        if u[k] != 0:
            lam = t[k] / u[k]
            break
    return lam

vals, vecs = np.linalg.eig(Mf)

print('scanning ALL eigenvectors (real & complex) for ASCII-scalable integer vectors...\n')
seen = set()
for i in range(40):
    lam = vals[i]
    if abs(lam.imag) > 1e-6:
        continue
    w = np.real(vecs[:, i])
    # dedupe near-identical vectors
    key = tuple(np.round(w / np.max(np.abs(w)), 6))
    if key in seen:
        continue
    seen.add(key)
    wn = w / np.max(np.abs(w))
    for S in range(1, 4000):
        u = [int(round(x * S)) for x in wn]
        if any(c == 0 for c in u):
            continue
        if min(u) < 32 or max(u) > 126:
            continue
        # refinement: local search +/-1 on each entry for exact fit
        lam = exact_eigvec_check(u)
        if lam is not None:
            txt = ''.join(chr(c) for c in u)
            print(f'*** FOUND lam={lam} S={S}: {txt!r}')
            # try small perturbations to be safe
            break
    else:
        continue

# focused: the 1337 eigenvalue, print raw vector scaled
print('\n--- eigenvalue 1337 vector, normalized, first entries ---')
idx = int(np.argmin(np.abs(vals - 1337.0)))
w = np.real(vecs[:, idx])
wn = w / np.max(np.abs(w))
print('lam found:', vals[idx])
print('wn[:12]:', np.round(wn[:12], 4))
# ratio between first two entries (should be a ratio of small ints / ascii codes)
