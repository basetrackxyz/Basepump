import os

FACTORY_ADDRESS  = "0x273b8fc139617f856fd3da0b89c29912a381901d"
RPC_URL          = "https://sepolia.base.org"
CHAIN_ID         = 84532
PLATFORM_WALLET  = os.environ.get("PLATFORM_WALLET", "0xab0f481fcae15f76af749b6adb699cf5566b45b6")
DEPLOY_FEE       = 500000000000000
PRIVATE_KEY      = os.environ.get("PRIVATE_KEY", "0xb3e3dbbac8c78c0269a1a083bec0f2043bb6fee8ebe80c55ac0174828a1a2262")
