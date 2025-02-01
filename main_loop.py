#!/usr/bin/env python

import asyncio
import logging
import random
import sys
import webbrowser
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
from solders.pubkey import Pubkey
from solders.rpc.config import RpcTransactionLogsFilterMentions
from solders.rpc.responses import (
    SubscriptionResult,
    LogsNotification,
)
from solders.token.state import Mint
from typing_extensions import Optional

from raydium_py.config import payer_keypair
from raydium_py.raydium.amm_v4 import buy, sell
from raydium_py.raydium.constants import RAYDIUM_AMM_V4
from raydium_py.utils.pool_utils import (
    fetch_amm_v4_pool_keys,
    get_amm_v4_reserves,
    AmmV4PoolKeys,
)

logging.basicConfig(level=logging.CRITICAL, format="[%(asctime)s] %(message)s")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

load_dotenv()

# just emulate real buy
DRY_RUN = False

# open browser tab
OPEN_BROWSER = True

# you have a force
FORCE = False

# buy single on multiple(N) tokens at the same time
MULTI_BUY = False
N = 1

# beep-beep
BEEP = True

MIN = 180
PROFIT = 3.9
AMOUNT = 0.03
DEEP = -60.0

BUY_SLIPPAGE = 50
SELL_SLIPPAGE = 99

MINT_FREEZE_CHECK = True
LP_BURNED_CHECK = False

API_KEY = getenv("RPC_API_KEY")

INITIAL_SOL_AMOUNT_PREFIX = "init_pc_amount: "
INITIAL_SOL_AMOUNT_PREFIX_LEN = len(INITIAL_SOL_AMOUNT_PREFIX)
INITIAL_COIN_AMOUNT_PREFIX = "init_pc_amount: "
INITIAL_COIN_AMOUNT_PREFIX_LEN = len(INITIAL_COIN_AMOUNT_PREFIX)
INITIAL_OPEN_TIME_PREFIX = "open_time: "
INITIAL_OPEN_TIME_PREFIX_LEN = len(INITIAL_OPEN_TIME_PREFIX)

COMMITMENT = Confirmed
PAIR_ADDRESS_IDX = 2

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
        i = 0
        tasks = set()
        semaphore = asyncio.Semaphore(N)
        while True:
            try:
                if self.dry_run:
                    logger.info("DRY RUN MODE!!!")

                logger.info(
                    f"Starting with filter for more than {MIN} SOL and profit target {PROFIT}% for {AMOUNT} SOL in {N if MULTI_BUY else 1} buy mode"
                )

                async with connect(WS_URL) as ws:
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
                                    try:
                                        tx = await client.get_transaction(
                                            tx_hash,
                                            commitment=COMMITMENT,
                                            encoding="jsonParsed",
                                            max_supported_transaction_version=1,
                                        )
                                        accounts = (
                                            tx.value.transaction.transaction.message.account_keys
                                        )
                                    except AttributeError:
                                        accounts = []

                                    if not accounts:
                                        logger.info(
                                            "Unknown transaction. No accounts. Skipping..."
                                        )

                                    pair_address = accounts[PAIR_ADDRESS_IDX].pubkey
                                    logger.info(
                                        f"""Pair address:
                                        https://photon-sol.tinyastro.io/en/lp/{pair_address}
                                        https://dexscreener.com/solana/{pair_address}"""
                                    )

                                    tt = 3
                                    while tt > 0:
                                        tt -= 1
                                        pool_keys = fetch_amm_v4_pool_keys(pair_address)

                                        if not pool_keys:
                                            logger.info(
                                                f"No pool keys. Trying again {tt} times..."
                                            )
                                        else:
                                            break
                                    else:
                                        pool_keys = None

                                    if not pool_keys:
                                        logger.info("No pool keys. Skipping...")
                                        continue

                                    token_address = (
                                        pool_keys.base_mint
                                        if str(pool_keys.quote_mint)
                                        == "So11111111111111111111111111111111111111112"
                                        else pool_keys.quote_mint
                                    )
                                    logger.info(
                                        f"""Token address:
                                        https://solscan.io/token/{token_address}"""
                                    )

                                    lp_token_address = pool_keys.lp_mint
                                    logger.info(
                                        f"""LP Token address:
                                        https://solscan.io/token/{lp_token_address}"""
                                    )

                                    logger.info(
                                        f"""Me:
                                        {payer_keypair.pubkey()}
                                        https://solscan.io/account/{payer_keypair.pubkey()}"""
                                    )
                                    logger.info("")
                                    i += 1

                                    if MULTI_BUY:
                                        async with semaphore:
                                            task = asyncio.create_task(
                                                self.watch(
                                                    i=i,
                                                    pair_address=pair_address,
                                                    token_address=token_address,
                                                    lp_token_address=lp_token_address,
                                                    buy_amount_in_sol=AMOUNT,
                                                    min_amount_in_sol=MIN,
                                                    profit_threshold=PROFIT,
                                                    buy_slippage=BUY_SLIPPAGE,
                                                    sell_slippage=SELL_SLIPPAGE,
                                                    semaphore=semaphore,
                                                    pool_keys=pool_keys,
                                                )
                                            )
                                            tasks.add(task)
                                            task.add_done_callback(tasks.discard)
                                    else:
                                        await self.watch(
                                            i=i,
                                            pair_address=pair_address,
                                            token_address=token_address,
                                            lp_token_address=lp_token_address,
                                            buy_amount_in_sol=AMOUNT,
                                            min_amount_in_sol=MIN,
                                            profit_threshold=PROFIT,
                                            buy_slippage=BUY_SLIPPAGE,
                                            sell_slippage=SELL_SLIPPAGE,
                                            semaphore=semaphore,
                                            pool_keys=pool_keys,
                                        )

                                    logger.info("")
                                    logger.info("=" * 110)
                                    logger.info("NEXT")
                                    logger.info("=" * 110)

            except KeyboardInterrupt:
                if MULTI_BUY:
                    for task in tasks:
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
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
        pair_address: Pubkey,
        token_address: Pubkey,
        lp_token_address: Pubkey,
        buy_amount_in_sol: float,
        min_amount_in_sol: int,
        profit_threshold: float,
        semaphore: asyncio.Semaphore,
        pool_keys: AmmV4PoolKeys,
        buy_slippage: int = 50,
        sell_slippage: int = 20,
    ):
        pp = 3
        # for not hardcoded profit point
        # jitter = random.uniform(0.1, 0.5) * 2
        jitter = 0
        profit_threshold -= jitter
        try:
            if MINT_FREEZE_CHECK:
                mint_and_freeze_ok = await self.mint_and_freeze_authorities(
                    token_address
                )
                logger.info(f"Mint and Freeze OK: {mint_and_freeze_ok}")
                if not mint_and_freeze_ok:
                    logger.info("Scam. Skipping.")
                    return

            if LP_BURNED_CHECK:
                lp_burned = await self.lp_tokens_burned(lp_token_address)
                logger.info(f"LP Tokens Burned: {lp_burned}")
                if not lp_burned:
                    logger.info("Scam. Skipping.")
                    return

            swap_sol_for_token = True
            is_failed = False

            number_of_tries_to_buy = 0
            max_number_of_tries_to_buy = 2

            number_of_tries_to_sell = 0
            max_number_of_tries_to_sell = 5

            buy_price = 0
            while pool_keys:
                if swap_sol_for_token:
                    if number_of_tries_to_buy == max_number_of_tries_to_buy:
                        logger.info(f"Failed to buy {max_number_of_tries_to_buy} times")
                        return
                    # buy tokens for SOL

                    current_data = await self.current_price_and_amount_in_sol(pool_keys)

                    if not current_data:
                        logger.info("No current data")
                        await asyncio.sleep(0.5)
                        continue

                    current_price, base_amount = current_data

                    if base_amount < min_amount_in_sol:
                        logger.info(f"Not enough {base_amount:.2f} SOL")
                        return

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
                        buy_price = current_price
                        OPEN_BROWSER and webbrowser.open(
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

                    current_data = await self.current_price_and_amount_in_sol(pool_keys)

                    if not current_data:
                        logger.info("No current data")
                        await asyncio.sleep(0.5)
                        continue

                    current_price, base_amount = current_data

                    logger.debug(f"BUY PRICE {buy_price:.18f}")
                    logger.debug(f"NOW PRICE {current_price:.18f}")

                    profit = round((current_price / buy_price) * 100 - 100, pp)

                    logger.info(
                        f"#{i:03d}  {token_address}  [{base_amount:7.2f} SOL]  {{{current_price:.18f}}}  ({profit:.{pp}f}%/{profit_threshold:.{pp}f}%)"
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
                            is_sold = await self.try_sell(
                                pool_keys,
                                sell_slippage,
                                gas_price_scale=1 + (0.25 * number_of_tries_to_sell),
                            )
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

    async def mint_and_freeze_authorities(self, token_address: Pubkey) -> bool:
        k = 2
        n = k
        while n > 0:
            try:
                mint_account = await client.get_account_info(token_address)
                n -= 1

                logger.debug(f"Token mint account: {mint_account}")
                account_data = mint_account.value.data
                logger.debug(f"Account data: {account_data}")

                if not account_data:
                    logger.info("No mint account data")
                    continue

                mint = Mint.from_bytes(account_data)
                logger.debug(f"Mint: {mint}")
                logger.info(f"Mint authority: {mint.mint_authority}")
                logger.info(f"Freeze authority: {mint.freeze_authority}")
                return mint.mint_authority is None and mint.freeze_authority is None
            except Exception as e:
                logger.error(f"ERROR WHILE CHECK MINT & FREEZE {type(e)}: {e}")
        else:
            logger.error(f"ERROR WHILE CHECK MINT & FREEZE in {k} retries")
            return False

    async def lp_tokens_burned(self, lp_token_address: Pubkey) -> bool:
        n = 2
        while n > 0:
            try:
                lp_mint_account = await client.get_account_info(lp_token_address)
                n -= 1

                logger.debug(f"LP Token mint account: {lp_mint_account}")
                account_data = lp_mint_account.value.data
                logger.debug(f"Account data: {account_data}")

                if not account_data:
                    logger.info("No LP token account data")
                    continue

                mint = Mint.from_bytes(account_data)
                logger.debug(f"LP Mint: {mint}")
                logger.info(f"LP Freeze authority: {mint.freeze_authority}")
                logger.info(f"LP supply: {mint.supply}")
                return mint.freeze_authority is None and mint.supply == 0
            except Exception as e:
                logger.debug(f"ERROR WHILE CHECK LP BURNED {type(e)}: {e}")
        else:
            return False

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
                coin_start = pool_created_log.find(INITIAL_OPEN_TIME_PREFIX)
                coin_end = pool_created_log.find(",", coin_start)
                coin_amount = int(
                    pool_created_log[
                        coin_start + INITIAL_COIN_AMOUNT_PREFIX_LEN : coin_end
                    ]
                )
                coin_amount_in_sol = coin_amount / 1e6

                logger.debug(f"SOL AMOUNT {initial_amount_in_sol:.2f}")
                logger.debug(f"COIN AMOUNT {coin_amount_in_sol:.18f}")

                ini_price = coin_amount_in_sol / initial_amount_in_sol

                logger.debug(f"INI PRICE {ini_price:.18f}")

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
        gas_price_scale: float = 1,
    ):
        if DRY_RUN:
            logger.info("DRY RUN MODE! Not really selling...")
            return True

        try:
            logger.info(f"<<< TRY SELL FOR X SOL")
            return bool(
                sell(
                    slippage=slippage,
                    pool_keys=pool_keys,
                    gas_price_scale=gas_price_scale,
                )
            )
        except:
            return False


async def main():
    bot = RaydiumV4Bot()
    await bot.loop()


if __name__ == "__main__":
    uvloop.install()
    asyncio.run(main())
