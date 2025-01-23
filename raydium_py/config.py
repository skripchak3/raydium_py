import os

from solana.rpc.api import Client
from solders.keypair import Keypair  # type: ignore

# gas config
UNIT_BUDGET = 150_000
UNIT_PRICE = 1_000_000

# private key
payer_keypair = Keypair.from_base58_string(os.getenv("PRIVATE_KEY"))

# Heluis API for speed, can be replaced by default Solana endpoint
client = Client(f'https://mainnet.helius-rpc.com/?api-key={os.getenv("RPC_API_KEY")}')
