import requests
import json
from Crypto.Hash import keccak as _keccak
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

def get_current_block():
    return int(rpc("eth_blockNumber", []), 16)

def get_selector(sig):
    k = _keccak.new(digest_bits=256)
    k.update(sig.encode())
    return k.digest()[:4].hex()

def get_all_tokens():
    k = _keccak.new(digest_bits=256)
    k.update(b"TokenCreated(address,address,string,string)")
    topic = "0x" + k.digest().hex()

    current = get_current_block()
    from_block = hex(max(0, current - 1900))

    logs = rpc("eth_getLogs", [{
        "address": config.FACTORY_ADDRESS,
        "topics": [topic],
        "fromBlock": from_block,
        "toBlock": "latest"
    }])

    tokens = []
    for log in logs:
        token_address = '0x' + log['topics'][1][-40:]
        creator       = '0x' + log['topics'][2][-40:]
        tokens.append({
            "address": token_address,
            "creator": creator
        })
    return tokens

def get_token_info(token_address):
    def call(sig):
        sel = get_selector(sig)
        return rpc("eth_call", [{
            "to": token_address,
            "data": "0x" + sel
        }, "latest"])

    def decode_string(hex_data):
        if hex_data == "0x" or len(hex_data) < 130:
            return ""
        data = hex_data[2:]
        offset = int(data[:64], 16) * 2
        length = int(data[offset:offset+64], 16)
        raw = data[offset+64:offset+64+length*2]
        return bytes.fromhex(raw).decode('utf-8', errors='replace')

    def decode_uint(hex_data):
        if hex_data == "0x":
            return 0
        return int(hex_data, 16)

    try:
        name         = decode_string(call("name()"))
        symbol       = decode_string(call("symbol()"))
        total_supply = decode_uint(call("totalSupply()"))
        migrated     = decode_uint(call("migrated()"))
        eth_collected = decode_uint(call("ethCollected()"))
        return {
            "name": name,
            "symbol": symbol,
            "total_supply": total_supply / 1e18,
            "migrated": bool(migrated),
            "eth_collected": eth_collected / 1e18
        }
    except Exception as e:
        return {"name": "Unknown", "symbol": "???", "total_supply": 0, "migrated": False, "eth_collected": 0}

def get_tokens_for_eth(token_address, eth_amount_wei):
    sel = get_selector("getTokensForETH(uint256)")
    encoded = eth_amount_wei.to_bytes(32, 'big').hex()
    result = rpc("eth_call", [{
        "to": token_address,
        "data": "0x" + sel + encoded
    }, "latest"])
    return int(result, 16)

def get_token_balance(token_address, wallet_address):
    sel = get_selector("balanceOf(address)")
    encoded = wallet_address[2:].lower().zfill(64)
    result = rpc("eth_call", [{
        "to": token_address,
        "data": "0x" + sel + encoded
    }, "latest"])
    return int(result, 16)
