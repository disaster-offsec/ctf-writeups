# SolarCTF "Пропавший архив" — версия для Sage (та же решётка, что в solve.py).
# Запуск: sage solve.sage output.txt
#
# Почему не f.small_roots(): параметры там выводятся из (beta, epsilon), и чтобы
# дотянуть до 499 бит при beta ~ 0.4995, нужен epsilon ~ 0.004 — Sage строит
# громоздкую решётку с неудачным t. Свою решётку собрать проще и честнее.
import sys

PRIME_BITS, LEAK_BITS, GUESS_BITS = 1024, 518, 6
M, T = 23, 24

def coppersmith(N, a, X, m=M, t=T):
    R.<x> = PolynomialRing(ZZ)
    f = x + a
    polys = [N^(m - i) * f^i for i in range(m)] + [x^j * f^m for j in range(t)]
    n = m + t
    B = matrix(ZZ, n, n)
    for r, g in enumerate(polys):
        for k, c in enumerate(g(x * X).list()):
            B[r, k] = c
    B = B.LLL()
    for row in B.rows()[:3]:
        g = sum(row[k] // X^k * x^k for k in range(n))
        for root, _ in g.roots():
            p = a + root
            if 1 < p < N and N % p == 0:
                return ZZ(p)
    return None

vals = [ZZ(v) for v in open(sys.argv[1]).read().split()]
count, e, flag_len = vals[:3]
flag = b""
for i in range(count):
    N, c, h = vals[3 + 3*i : 6 + 3*i]
    unknown = PRIME_BITS - LEAK_BITS - GUESS_BITS
    X = 2^(unknown - 1)
    for guess in range(2^GUESS_BITS):
        a = (((h << GUESS_BITS) + guess) << unknown) + X
        p = coppersmith(N, a, X)
        if p:
            break
    q = N // p
    d = inverse_mod(e, (p - 1) * (q - 1))
    msg = int(pow(c, d, N)).to_bytes(32, "big")
    size = flag_len // count + (i < flag_len % count)
    flag += msg[-size:]
    print(i, guess, msg[-size:])
print(flag)
