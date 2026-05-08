import os
from Crypto.Hash import keccak as _keccak

CHAIN_ID = 84532

def keccak256(data):
    k = _keccak.new(digest_bits=256)
    k.update(data)
    return k.digest()

def rlp_length(length, offset):
    if length < 56:
        return bytes([offset + length])
    len_bytes = length.to_bytes((length.bit_length() + 7) // 8, 'big')
    return bytes([offset + 55 + len(len_bytes)]) + len_bytes

def rlp_encode(item):
    if isinstance(item, bytes):
        if len(item) == 0:
            return b'\x80'
        if len(item) == 1 and item[0] < 0x80:
            return item
        return rlp_length(len(item), 0x80) + item
    elif isinstance(item, list):
        encoded = b''.join(rlp_encode(i) for i in item)
        return rlp_length(len(encoded), 0xc0) + encoded

def int_to_bytes(n):
    if n == 0:
        return b''
    return n.to_bytes((n.bit_length() + 7) // 8, 'big')

def sign_tx(tx, private_key_hex):
    from wallet import scalar_mult, Gx, Gy, N, P, point_add

    priv_int  = int(private_key_hex, 16)
    to_field  = bytes.fromhex(tx['to'][2:]) if tx.get('to') else b''
    data_bytes = bytes.fromhex(tx['data'][2:]) if tx['data'].startswith('0x') else bytes.fromhex(tx['data'])

    # EIP-155 signing hash
    raw = rlp_encode([
        int_to_bytes(tx['nonce']),
        int_to_bytes(tx['gasPrice']),
        int_to_bytes(tx['gas']),
        to_field,
        int_to_bytes(tx['value']),
        data_bytes,
        int_to_bytes(CHAIN_ID),
        b'',
        b''
    ])
    msg_hash = keccak256(raw)
    z = int.from_bytes(msg_hash, 'big')

    # Sign with deterministic k (RFC 6979 simplified)
    def try_sign():
        for _ in range(10000):
            k = int.from_bytes(os.urandom(32), 'big') % N
            if k == 0:
                continue
            # R = k * G
            R = scalar_mult(k, (Gx, Gy))
            r = R[0] % N
            if r == 0:
                continue
            k_inv = pow(k, N - 2, N)
            s = (k_inv * (z + r * priv_int)) % N
            if s == 0:
                continue
            # Recovery bit
            v = 0 if R[1] % 2 == 0 else 1
            if s > N // 2:
                s = N - s
                v ^= 1
            return r, s, v
        raise Exception("Signing failed")

    r, s, v = try_sign()
    v_final = 35 + 2 * CHAIN_ID + v

    signed_tx = rlp_encode([
        int_to_bytes(tx['nonce']),
        int_to_bytes(tx['gasPrice']),
        int_to_bytes(tx['gas']),
        to_field,
        int_to_bytes(tx['value']),
        data_bytes,
        int_to_bytes(v_final),
        int_to_bytes(r),
        int_to_bytes(s)
    ])

    return '0x' + signed_tx.hex()
