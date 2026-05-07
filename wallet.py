import os
import sqlite3
import hashlib
import hmac
import struct
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import json

# ── Secp256k1 constants ──────────────────────────────────────────
P  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8

def point_add(P1, P2):
    if P1 is None: return P2
    if P2 is None: return P1
    x1, y1 = P1
    x2, y2 = P2
    if x1 == x2:
        if y1 != y2: return None
        m = (3 * x1 * x1 * pow(2 * y1, P - 2, P)) % P
    else:
        m = ((y2 - y1) * pow(x2 - x1, P - 2, P)) % P
    x3 = (m * m - x1 - x2) % P
    y3 = (m * (x1 - x3) - y1) % P
    return (x3, y3)

def scalar_mult(k, point):
    result = None
    addend = point
    while k:
        if k & 1:
            result = point_add(result, addend)
        addend = point_add(addend, addend)
        k >>= 1
    return result

def private_key_to_address(priv_hex):
    priv_int = int(priv_hex, 16)
    pub = scalar_mult(priv_int, (Gx, Gy))
    x_bytes = pub[0].to_bytes(32, 'big')
    y_bytes = pub[1].to_bytes(32, 'big')
    pub_bytes = x_bytes + y_bytes
    # Keccak-256
    from Crypto.Hash import keccak
    k = keccak.new(digest_bits=256)
    k.update(pub_bytes)
    addr = k.hexdigest()[-40:]
    return '0x' + addr

# ── Encryption ───────────────────────────────────────────────────
def encrypt_key(priv_hex, password):
    salt = get_random_bytes(16)
    key = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    cipher = AES.new(key, AES.MODE_GCM)
    ct, tag = cipher.encrypt_and_digest(priv_hex.encode())
    return json.dumps({
        'salt': salt.hex(),
        'nonce': cipher.nonce.hex(),
        'tag': tag.hex(),
        'ct': ct.hex()
    })

def decrypt_key(encrypted_json, password):
    d = json.loads(encrypted_json)
    salt = bytes.fromhex(d['salt'])
    key = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    cipher = AES.new(key, AES.MODE_GCM, nonce=bytes.fromhex(d['nonce']))
    return cipher.decrypt_and_verify(
        bytes.fromhex(d['ct']),
        bytes.fromhex(d['tag'])
    ).decode()

# ── Database ─────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect('basepump.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS wallets (
            telegram_id TEXT PRIMARY KEY,
            address TEXT NOT NULL,
            encrypted_key TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def create_wallet(telegram_id, password):
    priv_hex = os.urandom(32).hex()
    address = private_key_to_address(priv_hex)
    encrypted = encrypt_key(priv_hex, password)
    conn = sqlite3.connect('basepump.db')
    c = conn.cursor()
    c.execute(
        'INSERT OR IGNORE INTO wallets (telegram_id, address, encrypted_key) VALUES (?, ?, ?)',
        (str(telegram_id), address, encrypted)
    )
    conn.commit()
    conn.close()
    return address, priv_hex

def get_wallet(telegram_id):
    conn = sqlite3.connect('basepump.db')
    c = conn.cursor()
    c.execute('SELECT address, encrypted_key FROM wallets WHERE telegram_id = ?', (str(telegram_id),))
    row = c.fetchone()
    conn.close()
    return row  # (address, encrypted_key) or None
