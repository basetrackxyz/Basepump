import json
import time
import requests
from signer import sign_tx
from wallet import private_key_to_address
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

def encode_create_token_call(name, symbol, description, image_uri):
    from Crypto.Hash import keccak as _keccak
    k = _keccak.new(digest_bits=256)
    k.update(b"createToken(string,string,string,string)")
    selector = k.digest()[:4]

    strings = [name, symbol, description, image_uri]
    encoded_strings = [s.encode('utf-8') for s in strings]

    offsets = []
    base = 32 * len(strings)
    for s in encoded_strings:
        offsets.append(base)
        padded_len = len(s) + (32 - len(s) % 32) % 32
        base += 32 + padded_len

    data = selector
    for o in offsets:
        data += o.to_bytes(32, 'big')
    for s in encoded_strings:
        length = len(s)
        padded = s + b'\x00' * ((32 - len(s) % 32) % 32)
        data += length.to_bytes(32, 'big') + padded

    return '0x' + data.hex()

def deploy_token(private_key_hex, name, symbol, description="", image_uri="ipfs://placeholder"):
    deployer  = private_key_to_address(private_key_hex)
    nonce     = get_nonce(deployer)
    gas_price = get_gas_price()
    gas_limit = 3_000_000

    print(f"Deploying token: {name} ({symbol})")
    print(f"Deployer: {deployer}")
    print(f"Nonce: {nonce}")

    data = encode_create_token_call(name, symbol, description, image_uri)

    tx = {
        'nonce':    nonce,
        'gasPrice': gas_price,
        'gas':      gas_limit,
        'to':       config.FACTORY_ADDRESS,
        'value':    0,
        'data':     data
    }

    signed   = sign_tx(tx, private_key_hex)
    tx_hash  = rpc("eth_sendRawTransaction", [signed])
    print(f"TX sent: {tx_hash}")

    # Wait for receipt
    for i in range(40):
        time.sleep(3)
        try:
            receipt = rpc("eth_getTransactionReceipt", [tx_hash])
            if receipt:
                print(f"Receipt status: {receipt.get('status')}")
                print(f"Logs count: {len(receipt.get('logs', []))}")

                if receipt.get('status') == '0x0':
                    raise Exception(f"Transaction reverted. TX: {tx_hash}")

                # Get TokenCreated event topic
                from Crypto.Hash import keccak as _keccak
                k = _keccak.new(digest_bits=256)
                k.update(b"TokenCreated(address,address,string,string)")
                topic = '0x' + k.digest().hex()
                print(f"Looking for topic: {topic}")

                for log in receipt.get('logs', []):
                    print(f"Log topic: {log['topics'][0]}")
                    if log['topics'][0].lower() == topic.lower():
                        token_address = '0x' + log['topics'][1][-40:]
                        print(f"Token deployed at: {token_address}")
                        return token_address, tx_hash

                # If no matching log found, return contract address from receipt
                print("No matching log. Logs:", json.dumps(receipt.get('logs', []), indent=2))
                raise Exception(f"Token deployed but address not found in logs. TX: {tx_hash}")
        except Exception as e:
            if "Transaction reverted" in str(e) or "not found in logs" in str(e):
                raise
            print(f"Waiting... ({i+1}/40): {e}")

    raise Exception(f"Timeout waiting for receipt. TX: {tx_hash}")
