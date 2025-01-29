#!/usr/bin/env python

import asyncio
import json
import logging
import sys
import webbrowser
from operator import itemgetter
from os import getenv
from pprint import pprint
from time import sleep

import requests
import uvloop
import websockets
from dotenv import load_dotenv
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.rpc.websocket_api import connect
from solders.rpc.config import RpcTransactionLogsFilterMentions
from solders.rpc.responses import (
    SubscriptionResult,
    LogsNotification,
)
from typing_extensions import Optional

from raydium_py.config import payer_keypair
from raydium_py.raydium.amm_v4 import buy, sell
from raydium_py.raydium.constants import RAYDIUM_AMM_V4
from raydium_py.utils.pool_utils import (
    fetch_amm_v4_pool_keys,
    get_amm_v4_reserves,
    AmmV4PoolKeys,
)

ini_price = None

logging.basicConfig(level=logging.CRITICAL, format="[%(asctime)s] %(message)s")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

load_dotenv()

# just emulate real buy
DRY_RUN = False

# you have a force
FORCE = False

# beep-beep
BEEP = True

MIN = 500
PROFIT = 2.9
AMOUNT = 0.02
DEEP = -1.0

BUY_SLIPPAGE = 50
SELL_SLIPPAGE = 50

PING_TIMEOUT = 300
PING_INTERVAL = 300

INITIAL_SOL_AMOUNT_PREFIX = "init_pc_amount: "
INITIAL_SOL_AMOUNT_PREFIX_LEN = len(INITIAL_SOL_AMOUNT_PREFIX)
INITIAL_COIN_AMOUNT_PREFIX = "init_pc_amount: "
INITIAL_COIN_AMOUNT_PREFIX_LEN = len(INITIAL_COIN_AMOUNT_PREFIX)
INITIAL_OPEN_TIME_PREFIX = "open_time: "
INITIAL_OPEN_TIME_PREFIX_LEN = len(INITIAL_OPEN_TIME_PREFIX)


COMMITMENT = Confirmed
TOKEN_ADDRESS_IDX = 18
PAIR_ADDRESS_IDX = 2

API_KEY = getenv("RPC_API_KEY")
HTTP_URL = f"https://mainnet.helius-rpc.com/?api-key={API_KEY}"
WS_URL = f"wss://mainnet.helius-rpc.com/?api-key={API_KEY}"
PAIR_CREATED_EVENT = "initialize2"
PAIR_CREATED_EVENT_LOG = "ray_log"

client = AsyncClient(HTTP_URL)


class RaydiumV4Bot:
    def __init__(self):
        self.client = AsyncClient(HTTP_URL)
        self.payer_keypair = payer_keypair
        self.min_amount_in_sol = 200
        self.profit_threshold = 7
        self.buy_slippage = 50
        self.sell_slippage = 20
        self.buy_amount_in_sol = 0.01
        self.dry_run = DRY_RUN
        self.check = not True

    async def loop(self):
        while True:
            try:
                i = 0
                if self.dry_run:
                    logger.info("DRY RUN MODE!!!")

                logger.info(
                    f"Starting with filter for more than {MIN} SOL and profit target {PROFIT}% for {AMOUNT} SOL"
                )

                async with connect(
                    WS_URL, ping_interval=PING_INTERVAL, ping_timeout=PING_TIMEOUT
                ) as ws:
                    # subscribe to all events from Raydium V4
                    await ws.logs_subscribe(
                        filter_=RpcTransactionLogsFilterMentions(RAYDIUM_AMM_V4),
                        commitment=COMMITMENT,
                    )

                    # read first message with subscription id
                    match await ws.recv():
                        case [subscription] if isinstance(
                            subscription, SubscriptionResult
                        ):
                            # logger.info("Subscription response", subscription)
                            ...

                    # filter only pair created events
                    async for message in ws:
                        match message:
                            case [message] if isinstance(message, LogsNotification):
                                pool_created_logs = [
                                    log
                                    for log in message.result.value.logs
                                    if PAIR_CREATED_EVENT in log
                                ]
                                if pool_created_logs:
                                    tx_hash = message.result.value.signature
                                    logger.info(
                                        f"""Pair created:
                                        https://solscan.io/tx/{tx_hash}"""
                                    )

                                    initial_amount_in_sol = self.initial_amount_in_sol(
                                        pool_created_logs[0]
                                    )
                                    if not initial_amount_in_sol:
                                        logger.debug(
                                            "No initial amount in SOL. Skipping..."
                                        )
                                        continue

                                    if initial_amount_in_sol < MIN:
                                        logger.info(
                                            f"Initial amount in SOL {initial_amount_in_sol} is less than {MIN} SOL. Skipping..."
                                        )
                                        continue
                                    else:
                                        logger.info(
                                            f"Initial amount in SOL {initial_amount_in_sol:.2f}"
                                        )

                                    tx = await client.get_transaction(
                                        tx_hash,
                                        commitment=COMMITMENT,
                                        encoding="jsonParsed",
                                        max_supported_transaction_version=1,
                                    )
                                    # print("RAW TX")
                                    # pprint(tx)
                                    tx = json.loads(tx.to_json())
                                    # logger.info('TX')
                                    # plogger.info(tx)
                                    accounts = tx["result"]["transaction"]["message"][
                                        "accountKeys"
                                    ]
                                    accounts = list(map(itemgetter("pubkey"), accounts))
                                    # logger.info('ACCOUNTS')
                                    # plogger.info(list(enumerate(accounts)))
                                    token_address = accounts[TOKEN_ADDRESS_IDX]
                                    pair_address = accounts[PAIR_ADDRESS_IDX]
                                    logger.info(
                                        f"""Token address:
                                        https://solscan.io/token/{token_address}"""
                                    )
                                    logger.info(
                                        f"""Pair address:
                                        https://photon-sol.tinyastro.io/en/lp/{pair_address}
                                        https://dexscreener.com/solana/{pair_address}"""
                                    )
                                    logger.info(
                                        f"""Me:
                                        {payer_keypair.pubkey()}
                                        https://solscan.io/account/{payer_keypair.pubkey()}"""
                                    )
                                    logger.info("")
                                    i += 1

                                    await self.watch(
                                        i=i,
                                        pair_address=pair_address,
                                        token_address=token_address,
                                        buy_amount_in_sol=AMOUNT,
                                        min_amount_in_sol=MIN,
                                        profit_threshold=PROFIT,
                                        buy_slippage=BUY_SLIPPAGE,
                                        sell_slippage=SELL_SLIPPAGE,
                                    )

                                    logger.info("")
                                    logger.info("=" * 110)
                                    logger.info("NEXT")
                                    logger.info("=" * 110)

            except KeyboardInterrupt:
                return
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Websocket closed. Reconnecting in 0 seconds...")
            except Exception as e:
                logger.info(f"Exception {type(e)}\nRestarting in 0 seconds...")
                _, _, tb = sys.exc_info()
                print(f"Exception occurred at line {tb.tb_lineno}")

    async def watch(
        self,
        /,
        *,
        i,
        pair_address: str,
        token_address: str,
        buy_amount_in_sol: float,
        min_amount_in_sol: int,
        profit_threshold: float,
        buy_slippage: int = 50,
        sell_slippage: int = 20,
    ):
        try:
            pool_keys = fetch_amm_v4_pool_keys(pair_address)

            # if False:
            #     # check
            #
            #     current_price, base_amount = await self.current_price_and_amount_in_sol(
            #         pool_keys
            #     )
            #     init_price = current_price
            #     logger.info(
            #         f"#{i:05d} Token /{token_address}/  [{base_amount:7.2f} SOL]  {{{current_price:.18f}}}  (0.0%)"
            #     )
            #
            #     if base_amount < min_amount_in_sol:
            #         logger.info("Not enough SOL ")
            #         return
            #
            #     if self.check:
            #         report = await self.rug_checker(token_address)
            #         logger.info("Report", report)
            #         (freeze_authority, mint_authority, lp_burned) = report
            #         logger.info("LP Burned: ", lp_burned)
            #
            #         if not freeze_authority:
            #             logger.info(f"Token {token_address} has freeze authority!")
            #             if FORCE:
            #                 logger.info("FORCE mode is on. Proceeding...")
            #             else:
            #                 return
            #
            #         if not mint_authority:
            #             logger.info(f"Token {token_address} has mint authority!")
            #             if FORCE:
            #                 logger.info("FORCE mode is on. Proceeding...")
            #             else:
            #                 return
            #
            #         if not lp_burned:
            #             logger.info(
            #                 f"Liquidity Provider Tokens {token_address} has not been burned!"
            #             )
            #             if FORCE:
            #                 logger.info("FORCE mode is on. Proceeding...")
            #             else:
            #                 return

            swap_sol_for_token = True
            is_failed = False

            number_of_tries_to_buy = 0
            max_number_of_tries_to_buy = 1

            number_of_tries_to_sell = 0
            max_number_of_tries_to_sell = 3

            buy_price = 0
            while pool_keys:
                if swap_sol_for_token:
                    if number_of_tries_to_buy == max_number_of_tries_to_buy:
                        logger.info(
                            f"Failed to buy {max_number_of_tries_to_buy} times, saved as memories"
                        )
                        return
                    # buy tokens for SOL
                    is_bought = await self.try_buy(
                        pool_keys,
                        buy_amount_in_sol,
                        buy_slippage,
                    )
                    number_of_tries_to_buy += 1
                    if is_bought:
                        BEEP and logger.info("\a")
                        BEEP and logger.info("\a")
                        logger.info(">>> BOUGHT")
                        buy_price, _ = await self.current_price_and_amount_in_sol(
                            pool_keys
                        )
                        webbrowser.open(
                            f"https://photon-sol.tinyastro.io/en/lp/{pair_address}"
                        )
                        logger.info(
                            f"Swapped {buy_amount_in_sol} SOL for {token_address} at price {buy_price:.18f} SOL/X"
                        )
                        swap_sol_for_token = False
                else:
                    if number_of_tries_to_sell == max_number_of_tries_to_sell:
                        logger.info(
                            f"Failed to sell {max_number_of_tries_to_sell} times, saved as memories"
                        )
                        return
                    # sell tokens for SOL

                    current_price, base_amount = (
                        await self.current_price_and_amount_in_sol(pool_keys)
                    )
                    logger.debug(f"INI PRICE {ini_price:.18f}")
                    logger.debug(f"BUY PRICE {buy_price:.18f}")
                    logger.debug(f"NOW PRICE {current_price:.18f}")

                    profit = round((current_price / buy_price) * 100 - 100, 2)

                    logger.info(
                        f"#{i:05d} Token /{token_address}/  [{base_amount:7.2f} SOL]  {{{current_price:.18f}}}  ({profit:.2f}%)"
                    )

                    profitable = profit >= profit_threshold

                    if profitable or is_failed:
                        is_sold = await self.try_sell(pool_keys, sell_slippage)
                        number_of_tries_to_sell += 1

                        if is_sold:
                            BEEP and logger.info("\a")
                            sleep(0.12)
                            BEEP and logger.info("\a")
                            logger.info("<<< SOLD")
                            sell_price = current_price
                            logger.info(
                                f"Swapped {token_address} for ~{buy_amount_in_sol} SOL at price {sell_price:.18f} SOL/X!"
                            )
                            return
                        else:
                            is_failed = True
                    else:
                        non_profitable = profit < DEEP
                        if non_profitable:
                            logger.info(f"Big deep {profit}%. SELL !")
                            is_sold = await self.try_sell(pool_keys, sell_slippage)
                            number_of_tries_to_sell += 1

                            if is_sold:
                                logger.info("<<< SOLD")
                                is_failed = False
                                sell_price = current_price
                                logger.info(
                                    f"Swapped {token_address} for ~{buy_amount_in_sol} SOL at price {sell_price:.18f} SOL/X!"
                                )
                                return
                            else:
                                is_failed = True

                await asyncio.sleep(0.5)
        except Exception as e:
            logger.info(f"Exception {type(e)}\nRestarting in 0 seconds...")
            _, _, tb = sys.exc_info()
            print(f"LINE {tb.tb_lineno}")

    async def rug_checker(self, token_address: str):
        n = 2
        url = f"https://api.rugcheck.xyz/v1/tokens/{token_address}/report"
        while n > 0:
            logger.info(f"Checking {url} ...")
            check = requests.get(url)
            logger.info(f"API response: {check.status_code}")
            if check.status_code == 200:
                report = check.json()
                logger.info(report)
                freeze_authority = report["freezeAuthority"] is None

                mint_authority = report["mintAuthority"] is None
                lp_burned = report["markets"][0]["lp"]["lpUnlocked"] == 0
                pprint(report["markets"][0]["lp"])
                return freeze_authority, mint_authority, lp_burned
            else:
                logger.info(f"API returned error: {check.status_code}")

            await asyncio.sleep(1)
            n -= 1

    async def current_price_and_amount_in_sol(
        self,
        pool_keys: Optional[AmmV4PoolKeys],
    ) -> Optional[tuple[float, float]]:
        (quote_amount, base_amount, _) = get_amm_v4_reserves(pool_keys)

        if not (quote_amount and base_amount):
            return None

        logger.debug(f"QUOTE {quote_amount}")
        assert quote_amount != 0

        current_price = base_amount / quote_amount
        return current_price, round(base_amount, 2)

    def initial_amount_in_sol(self, pool_created_log: str) -> Optional[float]:
        try:
            logger.debug(pool_created_log)
            open_time_start = pool_created_log.find(INITIAL_OPEN_TIME_PREFIX)
            open_time_end = pool_created_log.find(",", open_time_start)
            open_time_timestamp = int(
                pool_created_log[
                    open_time_start + INITIAL_OPEN_TIME_PREFIX_LEN : open_time_end
                ]
            )

            logger.debug("OPEN TIME", open_time_timestamp)
            if not open_time_timestamp:
                return None

            amount_start = pool_created_log.find(INITIAL_SOL_AMOUNT_PREFIX)
            amount_end = pool_created_log.find(",", amount_start)
            initial_amount_in_lamports = int(
                pool_created_log[
                    amount_start + INITIAL_SOL_AMOUNT_PREFIX_LEN : amount_end
                ]
            )
            initial_amount_in_sol = initial_amount_in_lamports / 1e9

            if True:
                global ini_price
                coin_start = pool_created_log.find(INITIAL_OPEN_TIME_PREFIX)
                coin_end = pool_created_log.find(",", coin_start)
                coin_amount = int(
                    pool_created_log[
                        coin_start + INITIAL_COIN_AMOUNT_PREFIX_LEN : coin_end
                    ]
                )
                coin_amount_in_sol = coin_amount / 1e6

                logger.info(f"SOL AMOUNT {initial_amount_in_sol:.2f}")
                logger.info(f"COIN AMOUNT {coin_amount_in_sol:.18f}")

                ini_price = coin_amount_in_sol / initial_amount_in_sol

                logger.info(f"INI PRICE {ini_price:.18f}")

            return initial_amount_in_sol

        except Exception as e:
            logger.warning(e)
            return None

    async def try_buy(
        self,
        pool_keys: AmmV4PoolKeys,
        sol_in: float,
        slippage: int = 50,
    ):
        if DRY_RUN:
            logger.info("DRY RUN MODE! Not really buying...")
            return True

        try:
            logger.info(f">>> TRY BUY FOR {sol_in} SOL")
            return bool(buy(sol_in=sol_in, slippage=slippage, pool_keys=pool_keys))
        except:
            return False

    async def try_sell(
        self,
        pool_keys: AmmV4PoolKeys,
        slippage: int = 50,
    ):
        if DRY_RUN:
            logger.info("DRY RUN MODE! Not really selling...")
            return True

        try:
            logger.info(f"<<< TRY SELL FOR X SOL")
            return bool(sell(slippage=slippage, pool_keys=pool_keys))
        except:
            return False


async def main():
    bot = RaydiumV4Bot()
    await bot.loop()


if __name__ == "__main__":
    uvloop.install()
    asyncio.run(main())
