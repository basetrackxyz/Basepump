import os

FACTORY_ADDRESS  = "0x2df4233860b0a9211ad822b4538b1fa9cd224619"
RPC_URL          = "https://sepolia.base.org"
CHAIN_ID         = 84532
PLATFORM_WALLET  = os.environ.get("PLATFORM_WALLET", "0xab0f481fcae15f76af749b6adb699cf5566b45b6")
DEPLOY_FEE       = 0

def get_private_key():
    key = os.environ.get("PRIVATE_KEY", "")
    if key:
        return key
    try:
        with open('.env') as f:
            for line in f:
                if line.startswith('PRIVATE_KEY='):
                    return line.split('=', 1)[1].strip()
    except:
        pass
    return ""

def get_bot_token():
    token = os.environ.get("BOT_TOKEN", "")
    if token:
        return token
    return "8110443376:AAGfKnEel8g_BZoxD22-AnSgkcfeWbp4QVo"

def get_encryption_secret():
    secret = os.environ.get("ENCRYPTION_SECRET", "")
    if secret:
        return secret
    return "GUGA GAGA"
