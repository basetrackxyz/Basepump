import json
import time
import requests
from signer import sign_tx
from wallet import private_key_to_address, decrypt_key
import sqlite3
import config

def rpc(method, params):
    r = requests.post(config.RPC_URL, json={
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    }, timeout=30)
    result = r.json()
    if "error" in result:
        raise Exception(f"RPC error: {result['error']}")
    return result["result"]

def get_nonce(address):
    return int(rpc("eth_getTransactionCount", [address, "latest"]), 16)

def get_gas_price():
    raw = int(rpc("eth_gasPrice", []), 16)
    return max(raw, 1_000_000_000)

def encode_string(s):
    """ABI encode a string"""
    b = s.encode('utf-8')
    offset = 32
    length = len(b)
    padded = b + b'\x00' * ((32 - len(b) % 32) % 32)
    return (
        offset.to_bytes(32, 'big') +
        length.to_bytes(32, 'big') +
        padded
    )

def encode_create_token_call(name, symbol, description, image_uri):
    """ABI encode createToken(string,string,string,string)"""
    # Function selector: keccak256("createToken(string,string,string,string)")[:4]
    from Crypto.Hash import keccak as _keccak
    k = _keccak.new(digest_bits=256)
    k.update(b"createToken(string,string,string,string)")
    selector = k.digest()[:4]

    # 4 strings — encode with offsets
    strings = [name, symbol, description, image_uri]
    num = len(strings)
    encoded_strings = [s.encode('utf-8') for s in strings]

    # Calculate offsets
    offsets = []
    base = 32 * num
    for s in encoded_strings:
        offsets.append(base)
        base += 32 + len(s) + (32 - len(s) % 32) % 32

    # Build data
    data = selector
    for o in offsets:
        data += o.to_bytes(32, 'big')
    for s in encoded_strings:
        length = len(s)
        padded = s + b'\x00' * ((32 - len(s) % 32) % 32)
        data += length.to_bytes(32, 'big') + padded

    return '0x' + data.hex()

def deploy_token(private_key_hex, name, symbol, description, image_uri="ipfs://placeholder"):
    deployer  = private_key_to_address(private_key_hex)
    nonce     = get_nonce(deployer)
    gas_price = get_gas_price()
    gas_limit = 2_000_000

    data = encode_create_token_call(name, symbol, description, image_uri)

    tx = {
        'nonce':    nonce,
        'gasPrice': gas_price,
        'gas':      gas_limit,
        'to':       config.FACTORY_ADDRESS,
        'value':    config.DEPLOY_FEE,
        'data':     data
    }

    signed = sign_tx(tx, private_key_hex)
    tx_hash = rpc("eth_sendRawTransaction", [signed])

