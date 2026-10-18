#!/usr/bin/env python3
"""solve.py — решение таска «Локпик» (Lattice iCE40 bitstream) одним файлом.

Нужно: Python 3.8+ и собранный Project IceStorm (icepack/iceunpack + icebox/icebox_vlog.py).
Больше ничего: ни gcc, ни SAT-солвера, ни pip-пакетов.

    python3 solve.py --ice ./icestorm lockpick.bin
    python3 solve.py --verilog lockpick.v            # если Verilog уже получен

Как это работает:
 1. bitstream -> .asc -> Verilog-нетлист (IceStorm).
 2. Нетлист разбирается и компилируется в плоский список операций (and/or/not/mux).
 3. Выход «разблокировано» — комбинационная функция только от пинов ключа. Ключ ищется
    bit-slicing-ом на больших целых Python: один проход считает сразу миллион наборов входов.
 4. С найденным ключом симулируется всё устройство; выходы читаются как ASCII, порядок
    пинов определяется по известному префиксу флага.
"""
import argparse
import itertools
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.setrecursionlimit(10000)

# ───────────────────────── выражения ─────────────────────────
TOK = re.compile(r"1'b[01]|[A-Za-z_]\w*|[01]|[()!&|?:]")


class P:
    def __init__(self, s):
        self.t, self.i = TOK.findall(s), 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def nxt(self):
        self.i += 1
        return self.t[self.i - 1]

    def tern(self):
        c = self.or_()
        if self.peek() == '?':
            self.nxt()
            a = self.tern()
            assert self.nxt() == ':'
            return ('?', c, a, self.tern())
        return c

    def or_(self):
        l = self.and_()
        while self.peek() == '|':
            self.nxt()
            l = ('|', l, self.and_())
        return l

    def and_(self):
        l = self.un()
        while self.peek() == '&':
            self.nxt()
            l = ('&', l, self.un())
        return l

    def un(self):
        t = self.nxt()
        if t == '!':
            return ('!', self.un())
        if t == '(':
            r = self.tern()
            self.nxt()
            return r
        if t in ('0', "1'b0"):
            return ('0',)
        if t in ('1', "1'b1"):
            return ('1',)
        return ('v', t)


def parse_expr(s):
    p = P(s)
    r = p.tern()
    assert p.peek() is None, s
    return r


def names_in(e, out):
    if e[0] == 'v':
        out.add(e[1])
    else:
        for x in e[1:]:
            if isinstance(x, tuple):
                names_in(x, out)
    return out


# ───────────────────────── нетлист ─────────────────────────
class Netlist:
    pass


def parse_netlist(src):
    src = re.sub(r'(?s)/\*.*?\*/', '', src)
    src = re.sub(r'(?m)^//.*$', '', src)
    nl = Netlist()
    nl.assigns, nl.ffs, nl.init_one = {}, [], set()
    nl.mem = [0] * 256
    nl.read_mode = None
    m = re.search(r'(?s)module chip \((.*?)\);', src)
    nl.ins, nl.outs = [], []
    for p in m.group(1).split(','):
        f = p.split()
        (nl.ins if f[0] == 'input' else nl.outs).append(f[-1])
    body = src[m.end():]
    r = re.search(r'(?s)SB_RAM40_4K #\((.*?)\) ram\w+ \((.*?)\);', body)
    if r:
        for h, val in re.findall(r"\.INIT_(\w)\(256'h([0-9a-f]+)\)", r.group(1)):
            for i in range(16):
                nl.mem[int(h, 16) * 16 + i] = (int(val, 16) >> (16 * i)) & 0xFFFF
        rm = re.search(r'\.READ_MODE\((\d)\)', r.group(1))
        nl.read_mode = int(rm.group(1)) if rm else 0
        port = dict(re.findall(r'\.(\w+)\((.*)\)', r.group(2)))

        def lst(s):  # {старший, ..., младший} -> младший первым
            s = s.strip().lstrip('{').rstrip('}')
            return [x.strip() for x in s.split(',')][::-1]
        nl.raddr, nl.rdata = lst(port['RADDR']), lst(port['RDATA'])
        nl.re, nl.rclke = port['RE'], port['RCLKE']
        body = body.replace(r.group(0), '')
    for line in body.split('\n'):
        line = line.strip()
        if not line or line.startswith('endmodule'):
            continue
        m1 = re.match(r'^(?:wire|reg) (\w+)(?: = (\d))?;$', line)
        m2 = re.match(r'^assign\s+(\w+)\s*=\s*(.*);$', line)
        m3 = re.match(r'^always @\(posedge (\w+)\) if \((.*?)\) (\w+) <= (.*);$', line)
        if m1:
            if m1.group(2) == '1':
                nl.init_one.add(m1.group(1))
        elif m2:
            nl.assigns[m2.group(1)] = parse_expr(m2.group(2))
        elif m3:
            rr = re.match(r"^(.*?) \? 1'b0 : (.*)$", m3.group(4))
            nl.ffs.append((m3.group(1), m3.group(3), parse_expr(m3.group(2)),
                           parse_expr(rr.group(1)), parse_expr(rr.group(2))))
        else:
            print('предупреждение: не разобрал строку:', line, file=sys.stderr)
    return nl


# ───────────────────────── компиляция в операции ─────────────────────────
NOT, AND, OR, MUX, COPY = range(5)


class Compiler:
    """Слоты: 0 — константа 0, 1 — константа «все единицы», затем сети, затем временные."""

    def __init__(self, nl):
        self.id = {}
        allnames = list(nl.ins) + list(nl.outs)
        for k, e in nl.assigns.items():
            allnames.append(k)
            allnames += names_in(e, set())
        for clk, q, en, r, d in nl.ffs:
            allnames += [clk, q]
            for e in (en, r, d):
                allnames += names_in(e, set())
        allnames += nl.raddr + nl.rdata + [nl.re, nl.rclke]
        for s in allnames:
            if s in ("1'b0", "1'b1") or s.startswith('open_') or s in self.id:
                continue
            self.id[s] = len(self.id) + 2
        self.base = len(self.id) + 2
        self.ntemp = 0

    def slot(self, name):
        return {"1'b0": 0, "1'b1": 1}.get(name) if name in ("1'b0", "1'b1") else self.id[name]

    def tmp(self):
        self.ntemp += 1
        return self.base + self.ntemp - 1

    def size(self):
        return self.base + self.ntemp + 8

    def emit(self, e, ops):
        k = e[0]
        if k == 'v':
            return self.slot(e[1])
        if k == '0':
            return 0
        if k == '1':
            return 1
        if k == '!':
            a = self.emit(e[1], ops)
            t = self.tmp()
            ops.append((NOT, t, a, 0, 0))
            return t
        if k in '&|':
            a, b = self.emit(e[1], ops), self.emit(e[2], ops)
            t = self.tmp()
            ops.append((AND if k == '&' else OR, t, a, b, 0))
            return t
        c, a, b = self.emit(e[1], ops), self.emit(e[2], ops), self.emit(e[3], ops)
        t = self.tmp()
        ops.append((MUX, t, a, b, c))
        return t


def run(ops, v, M):
    """M — маска всех «линий»: (1<<L)-1. При L=1 это обычная булева логика."""
    for k, d, a, b, c in ops:
        if k == NOT:
            v[d] = v[a] ^ M
        elif k == AND:
            v[d] = v[a] & v[b]
        elif k == OR:
            v[d] = v[a] | v[b]
        elif k == MUX:
            vc = v[c]
            v[d] = (vc & v[a]) | ((vc ^ M) & v[b])
        else:
            v[d] = v[a]


def topo(nl, need):
    order, state = [], {}

    def visit(n):
        if n not in nl.assigns or state.get(n) == 2:
            return
        assert state.get(n) != 1, 'комбинационная петля на ' + n
        state[n] = 1
        for d in names_in(nl.assigns[n], set()):
            visit(d)
        state[n] = 2
        order.append(n)
    for n in sorted(need):
        visit(n)
    return order


def cone(nl, e):
    nets, leaves = set(), set()

    def walk_name(s):
        if s in nl.assigns:
            if s in nets:
                return
            nets.add(s)
            walk(nl.assigns[s])
        else:
            leaves.add(s)

    def walk(x):
        if x[0] == 'v':
            walk_name(x[1])
        else:
            for y in x[1:]:
                if isinstance(y, tuple):
                    walk(y)
    walk(e)
    return nets, leaves


def comb_ops(nl, c, nets):
    ops = []
    for n in topo(nl, nets):
        ops.append((COPY, c.slot(n), c.emit(nl.assigns[n], ops), 0, 0))
    return ops


# ───────────────────────── поиск ключа ─────────────────────────
def atoms(nl, e, depth=0):
    """Раскладывает условие «e == 1» на конъюнкты A1 & A2 & ... (раскрывая алиасы и c?a:0)."""
    if depth > 64:
        return [e]
    k = e[0]
    if k == '1':
        return []
    if k == 'v' and e[1] in nl.assigns:
        return atoms(nl, nl.assigns[e[1]], depth + 1)
    if k == '&':
        return atoms(nl, e[1], depth + 1) + atoms(nl, e[2], depth + 1)
    if k == '?':
        c, a, b = e[1], e[2], e[3]
        if b[0] == '0':
            return atoms(nl, c, depth + 1) + atoms(nl, a, depth + 1)
        if a[0] == '0':
            return [('!', c)] + atoms(nl, b, depth + 1)
    return [e]


def pin_set(nl, e, is_in):
    _, lv = cone(nl, e)
    return lv if all(x in is_in for x in lv) else None


def pin_num(p):
    return int(p.split('_')[1])


def find_keys(nl, c, target, is_in, lanes_log2=20):
    ats = []
    for a in atoms(nl, target):
        ps = pin_set(nl, a, is_in)
        if ps is None:
            sys.exit('целевая функция зависит от состояния — нужен другой подход (развёртка по тактам)')
        ats.append((a, ps))
    key_pins = sorted(set().union(*[p for _, p in ats]), key=pin_num)
    print(f'пинов ключа: {len(key_pins)}, конъюнктов: {len(ats)}')

    # Стадия 1: конъюнкты по возрастанию числа пинов, пока объединение <= 29.
    ats.sort(key=lambda x: len(x[1]))
    s1_pins, s1, s2 = set(), [], []
    for a, ps in ats:
        if len(s1_pins | ps) <= 29:
            s1_pins |= ps
            s1.append(a)
        else:
            s2.append(a)
    s1_list = [p for p in key_pins if p in s1_pins]
    free = [p for p in key_pins if p not in s1_pins]
    print(f'стадия 1: {len(s1_list)} пинов, стадия 2: {len(s2)} конъюнктов, свободных пинов: {len(free)}')

    need = set()
    for a in s1:
        need |= cone(nl, a)[0]
    ops1 = comb_ops(nl, c, need)
    res = 1
    for a in s1:
        s = c.emit(a, ops1)
        t = c.tmp()
        ops1.append((AND, t, res, s, 0))
        res = t

    stage2 = None
    for a in s2:
        stage2 = a if stage2 is None else ('&', stage2, a)
    if stage2 is not None:
        ops2 = comb_ops(nl, c, cone(nl, stage2)[0])
        r2 = c.emit(stage2, ops2)

    nlow = min(lanes_log2, len(s1_list))
    L = 1 << nlow
    M = (1 << L) - 1
    # lane-шаблоны: в линии l бит i равен (l >> i) & 1
    pat = []
    for i in range(nlow):
        w = 1 << (i + 1)
        unit = ((1 << (1 << i)) - 1) << (1 << i)
        pat.append(unit * (M // ((1 << w) - 1)))
    outer = 1 << (len(s1_list) - nlow)
    v = [0] * c.size()
    v[1] = M
    found = []
    for o in range(outer):
        for i in range(nlow):
            v[c.slot(s1_list[i])] = pat[i]
        for i in range(nlow, len(s1_list)):
            v[c.slot(s1_list[i])] = M if (o >> (i - nlow)) & 1 else 0
        run(ops1, v, M)
        m = v[res]
        while m:
            low = m & -m
            lane = low.bit_length() - 1
            m ^= low
            for f in range(1 << len(free)):
                key = {}
                for i in range(nlow):
                    key[s1_list[i]] = (lane >> i) & 1
                for i in range(nlow, len(s1_list)):
                    key[s1_list[i]] = (o >> (i - nlow)) & 1
                for i, p in enumerate(free):
                    key[p] = (f >> i) & 1
                ok = True
                if stage2 is not None:
                    v2 = [0] * c.size()
                    v2[1] = 1
                    for p, b in key.items():
                        v2[c.slot(p)] = b
                    run(ops2, v2, 1)
                    ok = v2[r2] != 0
                if ok:
                    found.append(key)
        if o % 64 == 0:
            print(f'  перебор: {o}/{outer}', end='\r', flush=True)
    print(' ' * 40, end='\r')
    return key_pins, found


# ───────────────────────── симуляция ─────────────────────────
class Sim:
    def __init__(self, nl, c):
        self.nl, self.c = nl, c
        self.comb = comb_ops(nl, c, set(nl.assigns))
        self.ffops, self.ffslot = [], []
        for clk, q, en, r, d in nl.ffs:
            self.ffslot.append((c.emit(en, self.ffops), c.emit(r, self.ffops), c.emit(d, self.ffops)))
        self.v = [0] * c.size()
        self.v[1] = 1
        for n in nl.init_one:
            if n in c.id:
                self.v[c.id[n]] = 1
        self.rd = 0

    def ram_out(self):
        for i, name in enumerate(self.nl.rdata):
            if i % 2 == 0 and not name.startswith('open_'):   # режим 512x8: данные на чётных битах
                self.v[self.c.slot(name)] = 1 if (self.rd >> i) & 3 else 0

    def settle(self):
        run(self.comb, self.v, 1)
        self.ram_out()
        run(self.comb, self.v, 1)

    def set(self, pin, x):
        self.v[self.c.slot(pin)] = x

    def get(self, pin):
        return self.v[self.c.slot(pin)]

    def clock(self):
        self.settle()
        run(self.ffops, self.v, 1)
        v, c = self.v, self.c
        nxt = []
        for (clk, q, en, r, d), (se, sr, sd) in zip(self.nl.ffs, self.ffslot):
            nxt.append(v[c.slot(q)] if not v[se] else (0 if v[sr] else v[sd]))
        nrd = self.rd
        if v[c.slot(self.nl.re)] and v[c.slot(self.nl.rclke)]:
            ra = sum(v[c.slot(n)] << i for i, n in enumerate(self.nl.raddr))
            w = self.nl.mem[ra & 255]
            nrd = w & ~(0x5555 if ra & 256 else 0xAAAA) & 0xFFFF
        for (clk, q, *_), x in zip(self.nl.ffs, nxt):
            v[c.slot(q)] = x
        self.rd = nrd
        self.settle()


# ───────────────────────── main ─────────────────────────
def find_tool(ice, sub, name):
    p = os.path.join(ice or '', sub, name)
    if ice and os.path.exists(p):
        return p
    w = shutil.which(name)
    if w:
        return w
    sys.exit(f'не нашёл {name}: укажите --ice /путь/к/icestorm (после make) или положите в PATH')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('bin', nargs='?')
    ap.add_argument('--ice', default=os.environ.get('ICESTORM', ''))
    ap.add_argument('--verilog')
    ap.add_argument('--prefix', default='SOLARCTF{')
    a = ap.parse_args()

    if a.verilog:
        src = open(a.verilog).read()
    elif a.bin:
        with tempfile.TemporaryDirectory() as tmp:
            asc = os.path.join(tmp, 'x.asc')
            subprocess.run([find_tool(a.ice, 'icepack', 'iceunpack'), a.bin, asc], check=True)
            src = subprocess.run([sys.executable, find_tool(a.ice, 'icebox', 'icebox_vlog.py'), '-l', asc],
                                 check=True, capture_output=True, text=True).stdout
    else:
        ap.error('укажите bitstream или --verilog')

    nl = parse_netlist(src)
    if nl.read_mode != 1:
        sys.exit('реализован только READ_MODE=1 (512x8)')
    c = Compiler(nl)
    is_in = set(nl.ins)
    print(f'нетлист: {len(nl.assigns)} LUT, {len(nl.ffs)} триггеров, входов {len(nl.ins)}, выходов {len(nl.outs)}')

    # 1) выход «разблокировано» — триггер-выход, D которого зависит только от пинов
    unlock = target = None
    for clk, q, en, r, d in nl.ffs:
        if q in nl.outs:
            ps = pin_set(nl, d, is_in)
            if ps is not None and len(ps) >= 16:
                unlock, target = q, d
    if target is None:
        sys.exit('не нашёл выход, зависящий только от пинов ключа')
    print('выход «разблокировано»:', unlock)

    # 2) ключ
    key_pins, keys = find_keys(nl, c, target, is_in)
    if not keys:
        sys.exit('ключ не найден')
    print('найдено ключей:', len(keys))
    key = keys[0]
    bits = ''.join(str(key[p]) for p in key_pins)
    print(f'ключ (пины по возрастанию): {bits} = 0x{int(bits, 2):08x}')

    # 3) служебные пины: clk, reset (самый частый reset-пин триггеров), start (оставшийся вход)
    clk = nl.ffs[0][0]
    cnt = {}
    for _, _, _, r, _ in nl.ffs:
        if r[0] == 'v' and r[1] in is_in:
            cnt[r[1]] = cnt.get(r[1], 0) + 1
    rst = max(cnt, key=cnt.get)
    start = [p for p in nl.ins if p not in (clk, rst) and p not in key_pins][0]
    print(f'clk={clk} reset={rst} start={start}')

    # 4) симуляция: сброс, старт, ключ, 60 тактов
    s = Sim(nl, c)
    s.set(rst, 1)
    for _ in range(3):
        s.clock()
    s.set(rst, 0)
    s.set(start, 1)
    for p, b in key.items():
        s.set(p, b)
    rows = []
    for _ in range(60):
        s.clock()
        rows.append({o: s.get(o) for o in nl.outs})
    print(f'{unlock} = {rows[59][unlock]} (ожидали 1)')
    steps = [rows[t] for t in range(2, 60, 2)]   # байт держится 2 такта

    # 5) known-plaintext: для каждого бита байта ищем пины, чей поток совпадает с битом префикса
    pre = a.prefix.encode()
    cand = []
    for b in range(8):
        cs = [o for o in nl.outs if o != unlock
              and all(steps[i][o] == (pre[i] >> b) & 1 for i in range(len(pre)))]
        if not cs:
            sys.exit(f'для бита {b} не нашёл пин — поменяйте --prefix')
        cand.append(cs)
    for pick in itertools.product(*cand):
        if len(set(pick)) < 8:
            continue
        text = bytes(sum(st[pick[b]] << b for b in range(8)) for st in steps)
        if all(32 <= x < 127 for x in text):
            print('порядок пинов (бит0..бит7):', list(pick))
            print('ФЛАГ:', text.decode())


if __name__ == '__main__':
    main()
