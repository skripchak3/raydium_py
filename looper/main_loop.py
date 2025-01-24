import asyncio
import json
from operator import itemgetter
from os import getenv

import uvloop
from dotenv import load_dotenv
from helius import TransactionsAPI
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.rpc.websocket_api import connect
from solders.rpc.config import RpcTransactionLogsFilterMentions
from solders.rpc.responses import (
    SubscriptionResult,
    LogsNotification,
)

from looper.watcher import is_buy, watcher
from raydium_py.raydium.constants import RAYDIUM_AMM_V4

load_dotenv()

API_KEY = getenv("RPC_API_KEY")
HTTP_URL = f"https://mainnet.helius-rpc.com/?api-key={API_KEY}"
WS_URL = f"wss://mainnet.helius-rpc.com/?api-key={API_KEY}"
PAIR_CREATED_EVENT = "initialize2"

client = AsyncClient(HTTP_URL)
helius = TransactionsAPI(API_KEY)


# This function listens for new pool creation
async def main():

    commitment = Confirmed
    token_address_idx = 18
    pair_address_idx = 2

    async with connect(WS_URL) as ws:
        # subscribe to all events from Raydium V4
        await ws.logs_subscribe(
            filter_=RpcTransactionLogsFilterMentions(RAYDIUM_AMM_V4),
            commitment=commitment,
        )

        # read first message with subscription id
        match await ws.recv():
            case [subscription] if isinstance(subscription, SubscriptionResult):
                # print("Subscription response", subscription)
                ...

        # filter only pair created events
        async for message in ws:
            match message:
                case [message] if isinstance(message, LogsNotification):
                    if any(
                        [PAIR_CREATED_EVENT in log for log in message.result.value.logs]
                    ):
                        tx_hash = message.result.value.signature
                        print(
                            f"""Pair created:
                        https://solscan.io/tx/{tx_hash}"""
                        )
                        tx = json.loads(
                            (
                                await client.get_transaction(
                                    tx_hash,
                                    commitment=commitment,
                                    encoding="jsonParsed",
                                    max_supported_transaction_version=1,
                                )
                            ).to_json()
                        )
                        accounts = tx["result"]["transaction"]["message"]["accountKeys"]
                        accounts = list(map(itemgetter("pubkey"), accounts))
                        token_address = accounts[token_address_idx]
                        pair_address = accounts[pair_address_idx]
                        print(
                            f"""Token address:
                        https://solscan.io/token/{token_address}"""
                        )
                        print(
                            f"""Pair address:
                        https://photon-sol.tinyastro.io/en/lp/{pair_address}
                        https://dexscreener.com/solana/{pair_address}"""
                        )
                        await watcher(pair_address)
                        break


if __name__ == "__main__":
    uvloop.install()
    asyncio.run(main())
