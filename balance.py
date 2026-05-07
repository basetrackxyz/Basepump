import requests
import json

# Base Sepolia RPC
RPC_URL = "https://sepolia.base.org"

def get_eth_balance(address):
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getBalance",
        "params": [address, "latest"],
        "id": 1
    }
    response = requests.post(RPC_URL, json=payload, timeout=10)
    result = response.json()
    
    if "error" in result:
        raise Exception(f"RPC error: {result['error']}")
    
    # Convert hex wei to ETH
    wei = int(result["result"], 16)
    eth = wei / 10**18
    return eth

def get_eth_price_usd():
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd",
            timeout=10
        )
        return r.json()["ethereum"]["usd"]
    except:
        return None
