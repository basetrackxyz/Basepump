import requests
import time
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

def buy_tokens(private_key_hex, token_address, eth_amount_wei):
    from Crypto.Hash import keccak as _keccak
    k = _keccak.new(digest_bits=256)
    k.update(b"buy()")
    selector = k.digest()[:4].hex()

    deployer  = private_key_to_address(private_key_hex)
    nonce     = get_nonce(deployer)
    gas_price = get_gas_price()

    tx = {
        'nonce':    nonce,
        'gasPrice': gas_price,
        'gas':      200_000,
        'to':       token_address,
        'value':    eth_amount_wei,
        'data':     '0x' + selector
    }

    signed   = sign_tx(tx, private_key_hex)
    tx_hash  = rpc("eth_sendRawTransaction", [signed])
    print(f"Buy TX: {tx_hash}")

    for i in range(40):
        time.sleep(3)
        try:
            receipt = rpc("eth_getTransactionReceipt", [tx_hash])
            if receipt:
                if receipt.get('status') == '0x0':
                    raise Exception(f"Buy reverted. TX: {tx_hash}")
                return tx_hash
        except Exception as e:
            if "Buy reverted" in str(e):
                raise
        print(f"Waiting... ({i+1}/40)")

    raise Exception(f"Timeout. TX: {tx_hash}")

def sell_tokens(private_key_hex, token_address, token_amount_wei):
    from Crypto.Hash import keccak as _keccak
    k = _keccak.new(digest_bits=256)
    k.update(b"sell(uint256)")
    selector = k.digest()[:4].hex()
    encoded  = token_amount_wei.to_bytes(32, 'big').hex()

    deployer  = private_key_to_address(private_key_hex)
    nonce     = get_nonce(deployer)
    gas_price = get_gas_price()

    tx = {
        'nonce':    nonce,
        'gasPrice': gas_price,
        'gas':      200_000,
        'to':       token_address,
        'value':    0,
        'data':     '0x' + selector + encoded
    }

    signed   = sign_tx(tx, private_key_hex)
    tx_hash  = rpc("eth_sendRawTransaction", [signed])
    print(f"Sell TX: {tx_hash}")

    for i in range(40):
        time.sleep(3)
        try:
            receipt = rpc("eth_getTransactionReceipt", [tx_hash])
            if receipt:
                if receipt.get('status') == '0x0':
                    raise Exception(f"Sell reverted. TX: {tx_hash}")
                return tx_hash
        except Exception as e:
            if "Sell reverted" in str(e):
                raise
        print(f"Waiting... ({i+1}/40)")

    raise Exception(f"Timeout. TX: {tx_hash}")
