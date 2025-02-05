import asyncio

import uvloop

from base import RaydiumBot
from ops import Op


async def main():
    bot = RaydiumBot(dry_run=True, private_key=None)
    profit = 5.0

    await bot.watch_new_tokens(
        buy_amount_in_sol=0.05,
        sell_amount_in_percent=profit,
        min_amount_in_sol=1450,
        take_profit=profit,
        stop_loss=-30.0,
        delay=1.0,
        op=Op.CHECK,
    )


if __name__ == "__main__":
    uvloop.install()
    asyncio.run(main())
