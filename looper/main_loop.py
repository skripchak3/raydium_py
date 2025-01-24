import asyncio
import json
from asyncio import sleep
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

from raydium_py.config import payer_keypair
from raydium_py.raydium.amm_v4 import buy, sell
from raydium_py.raydium.constants import RAYDIUM_AMM_V4
from raydium_py.utils.pool_utils import fetch_amm_v4_pool_keys, get_amm_v4_reserves

load_dotenv()

MIN = 200
PROFIT = 10
BUY_SLIPPAGE = 50
SELL_SLIPPAGE = 20
API_KEY = getenv("RPC_API_KEY")
HTTP_URL = f"https://mainnet.helius-rpc.com/?api-key={API_KEY}"
WS_URL = f"wss://mainnet.helius-rpc.com/?api-key={API_KEY}"
PAIR_CREATED_EVENT = "initialize2"

client = AsyncClient(HTTP_URL)
helius = TransactionsAPI(API_KEY)


async def watcher(
    pair_address: str,
    token_address: str,
    balance: float,
    buy_amount_in_sol: float = 0.05,
    min_amount_in_sol: int = 200,
    profit_threshold: int = 7,
    buy_slippage: int = 50,
    sell_slippage: int = 20,
):
    pool_keys = fetch_amm_v4_pool_keys(pair_address)

    initial_price = None
    bought = False

    while 1:
        (quote_amount, base_amount, _) = get_amm_v4_reserves(pool_keys)
        current_price = base_amount / quote_amount

        if not initial_price:
            initial_price = current_price
            print(
                f"Token /{token_address}/  [{round(base_amount, 2)} SOL]  {{{current_price}}}  (-%)"
            )
            token_to_buy = base_amount >= min_amount_in_sol
            if token_to_buy and balance > buy_amount_in_sol:
                print(f"Buying 0.05 SOL")
                bought = buy(
                    pair_address, sol_in=buy_amount_in_sol, slippage=buy_slippage
                )
                if not bought:
                    print("Failed to buy")
                    break
            else:
                break

        else:
            profit = (current_price / initial_price) * 100 - 100
            print(
                f"Token /{token_address}/  [{round(base_amount, 2)} SOL]  {{{current_price}}}  ({round(profit, 1)}%)"
            )
            if profit >= profit_threshold and bought:
                print(f"Selling 0.05 SOL")
                sold = sell(pair_address, slippage=sell_slippage)
                if sold:
                    break

        await sleep(0.5)


# This function listens for new pool creation
async def main():
    commitment = Confirmed
    token_address_idx = 18
    pair_address_idx = 2

    balance = await client.get_balance(payer_keypair.pubkey(), commitment=Confirmed)
    balance = balance.value / 10**9
    print(
        f"Starting with balance: {balance} SOL with filter for more than {MIN} SOL and profit target {PROFIT}%"
    )

    try:
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
                            print(
                                f"""Me:
                            {payer_keypair.pubkey()}
                            https://solscan.io/account/{payer_keypair.pubkey()}"""
                            )
                            balance = await client.get_balance(
                                payer_keypair.pubkey(), commitment=Confirmed
                            )
                            balance = balance.value / 10**9
                            await watcher(
                                pair_address,
                                token_address,
                                balance,
                                min_amount_in_sol=MIN,
                                profit_threshold=PROFIT,
                                buy_slippage=BUY_SLIPPAGE,
                                sell_slippage=SELL_SLIPPAGE,
                            )
                            print()
                            print("=" * 120)
                            print("NEXT")
                            print("=" * 120)
    except:
        print('Restarting in 0 seconds...')


if __name__ == "__main__":
    uvloop.install()
    asyncio.run(main())
