from os import path, getenv

from dotenv import load_dotenv
from solana.rpc.api import Client
from solders.keypair import Keypair  # type: ignore

env_path = path.join(path.dirname(path.dirname(__file__)), ".env")
load_dotenv(
    dotenv_path=env_path,
    override=True,
    verbose=True,
    encoding="utf-8",
)

# gas config
UNIT_BUDGET = 200_000
UNIT_PRICE = 1_000_000

# private key
payer_keypair = Keypair.from_base58_string(getenv("PRIVATE_KEY"))

# Heluis API for speed, can be replaced by default Solana endpoint
client = Client(f'https://mainnet.helius-rpc.com/?api-key={getenv("RPC_API_KEY")}')
