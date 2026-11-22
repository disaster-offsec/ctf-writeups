#!/usr/bin/env python3
"""
Can YOU handle it? — solver.

Вход: suspicious_full.dmp (полный MDMP-дамп SuspiciousBrief.exe), опционально disk.vhdx.

Суть: процесс открыл telemetry.bin через CreateFileMappingW/MapViewOfFile,
удалил файл прямо под открытым хэндлом (DeleteFileW) и ~90 секунд держал
read-only view в памяти. Флаг никогда не появляется открытым текстом — он
лежит XOR-ом (ключ из argv) в страницах секции-маппинга, окружённый сотнями
decoy-флагов в управляемой куче.

Скрипт делает:
  1) парсит MDMP-хедер и Memory64List;
  2) достаёт --xor-key/--flag-offset/--flag-length: сначала из pinned-строки
     'cfg:xor=...;off=...;len=...;path=...' в куче, затем из командной строки
     процесса (fallback), затем брутит ключ по префиксу 'flag{' (fallback 2);
  3) сканирует память на enc('flag{') = 'flag{' ^ key, декодирует flag-length
     байт и пишет FLAG.txt;
  4) с флагом --disk disk.vhdx ищет те же байты в образе диска (telemetry.bin
     в NTFS внутри VHDX — дамп-маппинг этого файла совпадает байт-в-байт).
"""
import argparse
import re
import struct
import sys

FLAG_PREFIX = b'flag{'
CFG_RE = re.compile(r'cfg:xor=(\d+);off=(\d+);len=(\d+);path=(.*?)\x00')
CMDLINE_RE = re.compile(
    r'--xor-key[= ](\d+).*?--flag-offset[= ](\d+).*?--flag-length[= ](\d+)')


# ---------------------------------------------------------------- minidump ---
def parse_streams(f):
    sig, ver, n, dir_rva = struct.unpack('<4sIII', f.read(16))
    assert sig == b'MDMP', f'not a minidump: {sig!r}'
    f.seek(dir_rva)
    streams = {}
    for _ in range(n):
        t, sz, r = struct.unpack('<III', f.read(12))
        streams.setdefault(t, (sz, r))
    return streams


def parse_memory64(f, streams):
    """MINIDUMP_MEMORY64_LIST -> [(start_va, size, file_rva), ...]"""
    _, rva = streams[9]
    f.seek(rva)
    n_ranges, base_rva = struct.unpack('<QQ', f.read(16))
    ranges, rva = [], base_rva
    for _ in range(n_ranges):
        start, size = struct.unpack('<QQ', f.read(16))
        ranges.append((start, size, rva))
        rva += size
    return ranges


def find_params(data):
    """(xor_key, flag_offset, flag_length, source) из дамп-артефактов."""
    # 1) pinned cfg-строка в куче ('cfg:xor=252;off=7434;len=37;path=...').
    #    Грабелька: Windows кладёт её на НЕЧЁТНОЕ смещение, поэтому цельный
    #    decode('utf-16-le') с начала файла её сдвигает — пробуем оба фазы.
    for shift in (0, 1):
        m = CFG_RE.search(data[shift:].decode('utf-16-le', 'replace'))
        if m:
            return (int(m.group(1)), int(m.group(2)), int(m.group(3)),
                    f'heap cfg-string (align +{shift})')
    # 2) командная строка процесса (PEB), UTF-16 и ASCII
    cmd = data.decode('utf-16-le', 'replace')
    m = CMDLINE_RE.search(cmd) or CMDLINE_RE.search(
        data.decode('latin-1', 'replace'))
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3)), 'cmdline'
    return None, None, None, 'not found'


def decode_flag(data, off, key, length=None):
    """Ищет enc('flag{') и декодирует до '}' (или length байт)."""
    enc = bytes(c ^ key for c in FLAG_PREFIX)
    out = []
    i = data.find(enc)
    while i >= 0:
        blob = bytes(c ^ key for c in data[i:i + (length or 96)])
        if length:
            out.append((i, blob.decode('utf-8', 'replace')))
        else:
            end = blob.find(b'}')
            if end > 0:
                out.append((i, blob[:end + 1].decode('utf-8', 'replace')))
        i = data.find(enc, i + 1)
    return out


# ------------------------------------------------------------------- main ---
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dmp', nargs='?', default='suspicious_full.dmp')
    ap.add_argument('--disk', help='disk.vhdx для corroborating-проверки')
    ap.add_argument('--out', default='FLAG.txt')
    args = ap.parse_args()

    data = open(args.dmp, 'rb').read()

    with open(args.dmp, 'rb') as f:
        streams = parse_streams(f)
        ranges = parse_memory64(f, streams)
    print(f'[+] MDMP: streams={sorted(streams)}, memory ranges={len(ranges)}')

    key, off, length, src = find_params(data)
    print(f'[+] параметры ({src}): key={key} off={off} len={length}')

    hits = []
    if key is not None:
        hits = decode_flag(data, off, key, length)
    if not hits:  # fallback: брут ключа по префиксу 'flag{'
        print('[*] fallback: брут XOR-ключа по префиксу flag{')
        for k in range(1, 256):
            found = decode_flag(data, None, k)
            found = [h for h in found if 'decoy' not in h[1]]
            if found:
                key = k
                hits = found
                print(f'[+] ключ найден брутом: {k}')
                break
    # оставить только попадания в resident-память и реальные флаги
    hits = [(i, s) for i, s in hits if s.startswith(FLAG_PREFIX.decode())]
    print(f'[+] закодированных вхождений в памяти: {len(hits)}')
    for i, s in hits:
        va = next((start + (i - rva) for start, size, rva in ranges
                   if rva <= i < rva + size), None)
        print(f'    file_off={i:#x} VA={va:#x} -> {s}')

    flag = max(hits, key=lambda h: h[0])[1] if hits else None
    # фильтр декой-флагов
    reals = [s for _, s in hits if 'decoy-' not in s]
    if reals:
        flag = reals[0]

    if flag:
        open(args.out, 'w').write(flag + '\n')
        print(f'[+] FLAG: {flag}  (saved to {args.out})')

    if args.disk:
        d = open(args.disk, 'rb').read()
        print(f'[+] disk {args.disk}: {len(d)} bytes')
        if key is not None:
            dhits = decode_flag(d, None, key)
            dhits = [s for _, s in dhits if 'decoy-' not in s]
            for s in dhits:
                print(f'    в VHDX: {s}')
            if flag and dhits:
                print(f'[+] совпадение дамп<->диск: {flag == dhits[0]}')


if __name__ == '__main__':
    main()
