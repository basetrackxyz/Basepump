import hmac
import hashlib
import sqlite3
import json
import os
from Crypto.Hash import keccak

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
    k = keccak.new(digest_bits=256)
    k.update(pub_bytes)
    addr = k.hexdigest()[-40:]
    return '0x' + addr

def derive_private_key(secret, telegram_id):
    """Deterministically derive private key from secret + telegram_id"""
    key = hmac.new(
        secret.encode('utf-8'),
        str(telegram_id).encode('utf-8'),
        hashlib.sha256
    ).digest()
    # Ensure valid private key (1 <= key < N)
    priv_int = int.from_bytes(key, 'big') % (N - 1) + 1
    return priv_int.to_bytes(32, 'big').hex()

def get_wallet(telegram_id, secret="GUGA GAGA"):
    """Get wallet for user — derived deterministically, no DB needed"""
    # Check env secret first
    secret = os.environ.get("ENCRYPTION_SECRET", secret)
    priv_hex = derive_private_key(secret, telegram_id)
    address  = private_key_to_address(priv_hex)
    return address, priv_hex

def decrypt_key(telegram_id, secret="GUGA GAGA"):
    """Get private key for user"""
    secret = os.environ.get("ENCRYPTION_SECRET", secret)
    return derive_private_key(secret, telegram_id)

def init_db():
    """No-op — kept for compatibility"""
    pass
