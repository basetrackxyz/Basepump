import os
import json
import time
import requests
from signer import sign_tx

RPC_URL = "https://sepolia.base.org"

def load_env():
    env = {}
    with open('.env') as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env

def rpc(method, params):
    r = requests.post(RPC_URL, json={
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

def deploy_factory(private_key_hex, platform_wallet):
    with open('factory_bytecode.txt') as f:
        bytecode = f.read().strip()

    constructor_arg = platform_wallet[2:].lower().zfill(64)
    data = '0x' + bytecode + constructor_arg

    from wallet import private_key_to_address
    deployer  = private_key_to_address(private_key_hex)
    nonce     = get_nonce(deployer)
    gas_price = get_gas_price()
    gas_limit = 3_000_000

    print(f"Deployer:  {deployer}")
    print(f"Nonce:     {nonce}")
    print(f"Gas price: {gas_price / 1e9} gwei")
    print(f"Max cost:  {(gas_price * gas_limit) / 1e18:.6f} ETH")

    tx = {
        'nonce':    nonce,
        'gasPrice': gas_price,
        'gas':      gas_limit,
        'to':       None,
        'value':    0,
        'data':     data
    }

    print("Signing...")
    signed = sign_tx(tx, private_key_hex)
    print(f"Signed length: {len(signed)}")

    print("Broadcasting...")
    tx_hash = rpc("eth_sendRawTransaction", [signed])
    print(f"TX Hash: {tx_hash}")
    print(f"Track:   https://sepolia.basescan.org/tx/{tx_hash}")
    print("Waiting for confirmation...")

    for i in range(30):
        time.sleep(3)
        try:
            receipt = rpc("eth_getTransactionReceipt", [tx_hash])
            if receipt:
                print(f"\nFactory deployed at: {receipt['contractAddress']}")
                return receipt['contractAddress'], tx_hash
        except:
            pass
        print(f"  waiting... ({i+1}/30)")

    print("Timed out. Check explorer.")
    return None, tx_hash

if __name__ == "__main__":
    env = load_env()
    deploy_factory(env['PRIVATE_KEY'], env['PLATFORM_WALLET'])
