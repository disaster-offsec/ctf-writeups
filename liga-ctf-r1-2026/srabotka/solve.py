#!/usr/bin/env python3
# Сработка (632): traffic.pcap + note.txt -> сигнатура стенда -> флаг.
# deps: pip install scapy
import base64, json, re, sys, zlib
from collections import defaultdict
from scapy.all import rdpcap, TCP, IP, Raw

M32 = 0xFFFFFFFF
WIRE = {"1": {"order": [2,0,1], "bias": 3,  "step": 5, "salt": [73,35,167]},
        "2": {"order": [1,2,0], "bias": 11, "step": 7, "salt": [211,86,29]},
        "3": {"order": [0,2,1], "bias": 6,  "step": 3, "salt": [142,61,196]}}

def rol(x, n): return ((x << n) | (x >> (32 - n))) & M32
def xor(a, b): return bytes(p ^ q for p, q in zip(a, b))

# ---------- 1. сборка TCP-потоков (ретрансмиссии: поздний пакет побеждает) ----------
def streams(pcap):
    segs = defaultdict(dict)
    for p in rdpcap(pcap):
        if TCP in p and Raw in p and IP in p:
            d = bytes(p[Raw].load)
            if d: segs[(p[IP].src, p[TCP].sport, p[TCP].dport)][p[TCP].seq] = d
    out = {}
    for k, s in segs.items():
        buf, nxt = bytearray(), None
        for seq in sorted(s):
            d = s[seq]
            if nxt is None: nxt = seq
            if seq < nxt:                       # перекрытие ретрансмиссии
                if nxt - seq < len(d): d = d[nxt - seq:]
                else: continue
            buf += d; nxt = seq + len(d)
        out[k] = bytes(buf)
    return out

# ---------- 2. HTTP-обмены в порядке следования ----------
def parse_requests(s):
    reqs, pos = [], 0
    while True:
        h = s.find(b'\r\n\r\n', pos)
        if h == -1: break
        head = s[pos:h].decode('latin1')
        clen = int(re.search(r'Content-Length:\s*(\d+)', head, re.I).group(1)
                   if re.search(r'Content-Length:\s*(\d+)', head, re.I) else 0)
        reqs.append((head, s[h+4:h+4+clen])); pos = h + 4 + clen
    return reqs

def parse_responses(s):
    resps, pos = [], 0
    while pos < len(s):
        h = s.find(b'\r\n\r\n', pos)
        if h == -1: break
        head = s[pos:h].decode('latin1'); lines = head.split('\r\n')
        status = int(lines[0].split()[1])
        hd = {}
        for ln in lines[1:]:
            if ':' in ln: k, v = ln.split(':', 1); hd[k.strip().lower()] = v.strip()
        body, raw = b'', 0
        if 'chunked' in hd.get('transfer-encoding', ''):
            data, consumed = s[h+4:], 0
            while data:
                e = data.find(b'\r\n')
                if e == -1: break
                n = int(data[:e].split(b';')[0], 16)
                if n == 0: consumed = len(s) - (h + 4); break   # хвостовые чанки/трейлеры до конца
                body += data[e+2:e+2+n]; consumed += e + 2 + n + 2
                data = data[e+2+n+2:]
            raw = consumed
        elif status not in (204, 304) and 'content-length' in hd:
            body = s[h+4:h+4+int(hd['content-length'])]; raw = len(body)
        resps.append((status, hd, body)); pos = h + 4 + raw
    return resps

def exchanges(pcap, ports):
    st = streams(pcap)
    exs = {}
    for port in ports:
        reqs = parse_requests(st.get(('10.8.0.50', port, 80), b''))
        resps = parse_responses(st.get(('10.8.0.1', 80, port), b''))
        lst = []
        for (head, body), (status, hd, rbody) in zip(reqs, resps):
            lst.append({'path': head.split('\r\n')[0].split()[1],
                        'id': (re.search(r'X-Request-ID:\s*(\S+)', head) or [None, '-'])[1] if re.search(r'X-Request-ID:\s*(\S+)', head) else '-',
                        'req': body, 'status': status, 'headers': hd, 'resp': rbody})
        exs[port] = lst
    return exs

# ---------- 3. проигрывание сессии и инверсия pack() ----------
def unpack(out, mode, seed, seq):
    cfg = WIRE[str(mode)]; raw = bytearray(48); k = 0
    x = (seed ^ ((seq + 1) * 0x9E3779B9 & M32)) & M32
    xs = []
    for _ in range(48):
        x = ((x * 1664525 & M32) + 1013904223) & M32; xs.append(x)
    for slot in range(3):
        shift = (seq + cfg['bias'] + cfg['step']*slot + (seed >> ((slot+1)*3) & 15)) & 15
        for i in range(16):
            raw[16*cfg['order'][slot] + (i+shift & 15)] = out[16*slot+i] ^ (xs[k] >> 24) ^ cfg['salt'][slot]; k += 1
    return bytes(raw)

def replay(port, exs, log):
    mode, seed, seq, pending, seen = 0, 0, 0, {}, set()
    raws = {}
    for e in exs:
        path, eid, status = e['path'], e['id'], e['status']
        if path == '/gate/v3' and eid.startswith('d'):
            out = base64.b64decode(e['req'])
            if eid not in raws:          # кэш pack(): повторная доставка = то же тело
                raws[eid] = unpack(out, mode, seed, seq)
                log.append((port, eid, mode, seed, seq))
        if path in ('/open', '/reset') and status == 201:
            p = json.loads(e['resp']); mode, seed, seq = p['mode'], int(p['nonce'], 16), 0
            pending.clear(); seen.clear()
        if path == '/switch':
            pending[eid] = json.loads(e['req'].decode())
            if status == 409: pending.pop(eid, None)
        c = e['headers'].get('x-commit')
        if c and c in pending:
            p = pending.pop(c); mode = p['mode']; seed = rol(seed ^ int(p['salt'], 16), 11)
        if path == '/gate/v3' and status == 204 and e['headers'].get('x-receipt') == eid and eid not in seen:
            wire = base64.b64decode(e['req'])          # crc32 по ТЕЛУ ЗАПРОСА, не по пустому ответу!
            seed = (rol(seed ^ zlib.crc32(wire) ^ int(e['headers']['x-ratchet'], 16), 7) + 0x6D2B79F5) & M32
            seq += 1; seen.add(eid)
    return raws

# ---------- 4. сигнатура: 16 байт, общие для сработок, отсутствующие у пропусков ----------
def candidates(b):
    c = {b[i:i+16] for i in range(len(b)-15)}
    bl = [b[0:16], b[16:32], b[32:48]]
    c |= {xor(bl[0],bl[1]), xor(bl[0],bl[2]), xor(bl[1],bl[2]), xor(bl[0],xor(bl[1],bl[2]))}
    return c

def main(pcap, note):
    note = open(note, encoding='utf-8').read()
    hits, misses = set(), set()
    cur = None
    for ln in note.splitlines():
        if ln.startswith('Сработки'): cur = hits
        elif ln.startswith('Пропуски'): cur = misses
        elif cur is not None:
            m = re.match(r'\s*(\d+)\s+(d\d+)\s*$', ln)
            if m: cur.add((int(m.group(1)), m.group(2)))
    ports = sorted({p for p, _ in hits | misses})
    exs = exchanges(pcap, ports)
    raws, log = {}, []
    for p in ports: raws.update({(p, k): v for k, v in replay(p, exs[p], log).items()})
    print(f'[+] {len(raws)} событий декодировано ({len(hits)} сработок, {len(misses)} пропусков)')
    print('[+] состояние сессии (порт, id, mode, seed, seq):')
    for port, eid, mode, seed, seq in log[:4]: print(f'    {port} {eid} mode={mode} seed={seed:08x} seq={seq}')
    print('    ...')
    hset = {c for k in hits for c in candidates(raws[k])}
    for k in hits: hset &= candidates(raws[k])
    for k in misses:
        r = raws[k]
        hset -= candidates(r) | {r[i:i+16] for i in range(33)} | {r}
    sig = sorted(hset, key=lambda s: s.hex())
    for s in sig:
        key = re.search(r'ASCII-ключом\s+(\w+)', note)
        key = (key.group(1) if key else 'TSPU').encode()
        n = int(re.search(r'первые\s+(\d+)\s+байт', note).group(1)) if re.search(r'первые\s+(\d+)\s+байт', note) else 3
        r = xor(s, (key * 4)[:16])
        flag = (r[n:] + r[:n]).decode('latin1')
        print(f'[+] сигнатура: {s.hex()}  (b1^b2 всех сработок, отсутствует у пропусков)')
        print(f'[+] XOR с ключом {key.decode()}: {r!r}  ->  перенос {n} байт в конец')
        print(f'FLAG: {flag}')

if __name__ == '__main__':
    pcap = sys.argv[1] if len(sys.argv) > 1 else '/home/z/my-project/upload/traffic.pcap'
    note = sys.argv[2] if len(sys.argv) > 2 else '/home/z/my-project/upload/note.txt'
    main(pcap, note)
