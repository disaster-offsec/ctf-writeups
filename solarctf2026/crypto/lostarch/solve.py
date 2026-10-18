#!/usr/bin/env python3
"""
SolarCTF "Пропавший архив" — RSA с утечкой старших бит простого.
Решение без Sage: Coppersmith (Howgrave-Graham) + бинарник fplll для LLL.

Зависимости: python3, numpy, fplll (`fplll` в PATH, например `apt install fplll-tools`).
Запуск:  python3 solve.py output.txt            # все 4 инстанса
         python3 solve.py output.txt 1          # только инстанс 1
"""
import os
import subprocess
import sys
import time

import numpy as np

sys.set_int_max_str_digits(0)          # числа в решётке — десятки тысяч цифр
FPLLL = os.environ.get("FPLLL", "fplll")

PRIME_BITS, LEAK_BITS = 1024, 518
GUESS_BITS = 6                         # перебираем 6 бит под утечкой → 64 решётки
M, T = 23, 24                          # параметры решётки: размерность n = M + T = 47


# ---------- полиномы как списки коэффициентов [c0, c1, c2, ...] ----------
def poly_mul(a, b):
    r = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            r[i + j] += x * y
    return r


def poly_eval(c, x):
    r = 0
    for a in reversed(c):
        r = r * x + a
    return r


# ---------- LLL через fplll ----------
def lll(rows):
    text = "[" + "\n".join("[" + " ".join(map(str, r)) + "]" for r in rows) + "]"
    out = subprocess.run([FPLLL, "-a", "lll"], input=text.encode(),
                         capture_output=True, check=True).stdout.decode()
    res = []
    for line in out.replace("[[", "[").replace("]]", "]").split("]"):
        nums = line.replace("[", " ").split()
        if nums:
            res.append([int(v) for v in nums])
    return res


# ---------- целые корни многочлена над Z ----------
def integer_roots(g, X):
    """Приближения корней через numpy (в масштабе y = x/X), затем Ньютон в целых."""
    scale = max(abs(c) * X**i for i, c in enumerate(g))
    approx = [float(c * X**i * 2**60 // scale) for i, c in enumerate(g)]
    while approx and approx[-1] == 0:
        approx.pop()
    dg = [i * c for i, c in enumerate(g)][1:]
    found = set()
    for r in np.roots(approx[::-1]):
        if abs(r.imag) > 1e-3 or abs(r.real) > 1.5:
            continue
        x = int(r.real * X)
        for _ in range(200):            # точность double ~53 бита, Ньютон добивает остальное
            d = poly_eval(dg, x)
            if d == 0:
                break
            nx = x - poly_eval(g, x) // d
            if nx == x:
                break
            x = nx
        found.update(x + dx for dx in range(-3, 4))
    return found


# ---------- одна попытка Копперсмита ----------
def coppersmith(N, a, X, m=M, t=T):
    """Ищет p | N вида p = a + x, |x| < X."""
    n = m + t
    f = [a, 1]                          # f(x) = x + a
    fpow = [[1]]
    for _ in range(m):
        fpow.append(poly_mul(fpow[-1], f))

    polys = [[N ** (m - i) * c for c in fpow[i]] for i in range(m)]   # N^(m-i) f^i
    polys += [[0] * j + fpow[m] for j in range(t)]                     # x^j f^m

    basis = []
    for p in polys:
        p = p + [0] * (n - len(p))
        basis.append([p[k] * X**k for k in range(n)])                  # g(xX)

    for vec in lll(basis)[:3]:          # обычно хватает первого вектора
        g = [vec[k] // X**k for k in range(n)]
        for x in integer_roots(g, X):
            cand = a + x
            if 1 < cand < N and N % cand == 0:
                return cand
    return None


def factor(N, h, log=print):
    unknown = PRIME_BITS - LEAK_BITS - GUESS_BITS      # 500 бит
    X = 1 << (unknown - 1)                              # центрируем: |x| < 2^499
    for guess in range(1 << GUESS_BITS):
        a = (((h << GUESS_BITS) | guess) << unknown) + X
        t0 = time.time()
        p = coppersmith(N, a, X)
        log(f"    guess {guess:2d}: {'FOUND' if p else 'no'} ({time.time() - t0:.0f}s)")
        if p:
            return p
    return None


def main():
    vals = list(map(int, open(sys.argv[1]).read().split()))
    count, e, flag_len = vals[:3]
    records = [vals[3 + 3 * i: 6 + 3 * i] for i in range(count)]
    only = [int(sys.argv[2])] if len(sys.argv) > 2 else range(count)

    chunks = {}
    for i in only:
        N, c, h = records[i]
        print(f"[*] instance {i}")
        p = factor(N, h)
        if p is None:
            print("    не найдено — увеличь M/T или GUESS_BITS")
            continue
        q = N // p
        d = pow(e, -1, (p - 1) * (q - 1))
        msg = pow(c, d, N).to_bytes(32, "big")
        base, extra = divmod(flag_len, count)
        size = base + (i < extra)
        chunks[i] = msg[-size:]
        print(f"    p = {p}\n    chunk = {chunks[i]}")

    print(b"".join(chunks.get(i, b"?") for i in range(count)))


if __name__ == "__main__":
    main()
