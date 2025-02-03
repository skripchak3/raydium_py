import asyncio

import uvloop
from solders.solders import Pubkey

from bot.base import RaydiumBot
from bot.ops import Op
from raydium_py.utils.pool_utils import fetch_amm_v4_pool_keys


async def main():
    bot = RaydiumBot()
    profit = 5.0

    await bot.watch_new_tokens(
        buy_amount_in_sol=0.1,
        sell_amount_in_percent=profit,
        min_amount_in_sol=1450,
        take_profit=profit,
        stop_loss=-30.0,
        op=Op.CHECK,
    )


if __name__ == "__main__":
    uvloop.install()
    asyncio.run(main())
