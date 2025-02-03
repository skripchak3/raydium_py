import asyncio

import uvloop
from solders.solders import Pubkey

from bot.base import RaydiumBot
from bot.ops import Op
from raydium_py.utils.pool_utils import fetch_amm_v4_pool_keys


async def main():
    bot = RaydiumBot()

    pair_address = "2K9bC1TiRiPKP6DXnsLbM1LmhecK4xHXPotHET2tpP1J"
    pool_keys = fetch_amm_v4_pool_keys(bot.client, Pubkey.from_string(pair_address))

    if not pool_keys:
        print("No pool keys. Skipping...")
        return

    profit = 3.5

    await bot.watch_single(
        pool_keys=pool_keys,
        buy_amount_in_sol=0.01,
        # sell_amount_in_percent=profit,
        sell_amount_in_percent=profit,
        min_amount_in_sol=450,
        take_profit=profit,
        stop_loss=-30.0,
        op=Op.BUY,
    )


if __name__ == "__main__":
    uvloop.install()
    asyncio.run(main())
