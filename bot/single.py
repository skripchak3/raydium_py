import asyncio

import uvloop
from solders.solders import Pubkey

from base import RaydiumBot
from ops import Op
from raydium_py.utils.pool_utils import fetch_amm_v4_pool_keys


async def main():
    bot = RaydiumBot()

    pair_address = ""
    if not pair_address:
        raise Exception("no pair address provided")

    pool_keys = fetch_amm_v4_pool_keys(bot.client, Pubkey.from_string(pair_address))

    if not pool_keys:
        print("No pool keys. Skipping...")
        return

    profit = 5

    await bot.watch_single(
        pool_keys=pool_keys,
        buy_amount_in_sol=0.05,
        sell_amount_in_percent=100,
        # sell_amount_in_percent=profit,
        min_amount_in_sol=450,
        take_profit=profit,
        stop_loss=-30.0,
        delay=0,
        op=Op.SELL,
    )


if __name__ == "__main__":
    uvloop.install()
    asyncio.run(main())
