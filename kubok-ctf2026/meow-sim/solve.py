import hashlib, struct

ENCRYPTED_FLAG = [-39, -35, 55, 54, 127, -92, 31, 97, 23, -55, 17, 11,
                  12, -63, 42, -110, 29, 8, -113, 91, -96, 117, 36]
TOKEN = "ny4n-lab-token"  # ObserverStore.DEFAULT_TOKEN

def jb(b):                      # Java пишет булевы как true/false
    return "true" if b else "false"

def sha256_hex(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def sha256_bytes(b):
    return hashlib.sha256(b).digest()

def box_seal(cat_dead, sup, stability):
    return sha256_hex(f"box|{jb(cat_dead)}|{jb(sup)}|{stability}|meowsim-v1")

def derive_key(token, seal, stability, cat_alive, cat_dead, sup, observed):
    s = (f"{token}|{seal}|{stability}|{jb(cat_alive)}|{jb(cat_dead)}"
         f"|{jb(sup)}|{jb(observed)}|meowsim-v1")
    return sha256_bytes(s.encode("utf-8"))

def stream(key, n):
    out, counter = b"", 0
    while len(out) < n:
        out += sha256_bytes(key + struct.pack(">I", counter))  # big-endian int32
        counter += 1
    return out[:n]

def decrypt(key):
    data = bytes(x & 0xFF for x in ENCRYPTED_FLAG)
    ks = stream(key, len(data))
    raw = bytes(a ^ b for a, b in zip(data, ks))
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None

for s in range(90, 101):
    out = decrypt(derive_key(TOKEN, box_seal(True, True, s), s, True, True, True, False))
    if out and out.startswith("ctfcup{"):
        print(f"stability = {s} -> {out}")
        break
