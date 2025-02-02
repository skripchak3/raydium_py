import asyncio

from bot.mixins.buyer import BuyParams
from bot.mixins.seller import SellParams
from bot.ops import Op
from raydium_py.raydium.amm_v4 import tokens_for_sol, sol_for_tokens
from raydium_py.utils.pool_utils import AmmV4PoolKeys


class SingleTokenWatcher:
    async def watch_single(
        self,
        pool_keys: AmmV4PoolKeys,
        buy_amount_in_sol: float,
        min_amount_in_sol: float,
        take_profit: float,
        stop_loss: float,
        buy_slippage: int = 50,
        sell_slippage: int = 99,
        op: Op = Op.CHECK,
    ):

        buy_params = BuyParams(
            sol_in=buy_amount_in_sol,
            slippage=buy_slippage,
            gas_config=self.gas_config,
        )
        sell_params = SellParams(
            percentage=100,
            slippage=sell_slippage,
            gas_config=self.gas_config,
        )

        bought_price = None

        pool_state = None

        number_of_tries_to_sell = 0
        while op != Op.EXIT:
            match op:
                case Op.CHECK:
                    if self.check_all(
                        self.async_client,
                        pool_keys.token_address,
                        pool_keys.lp_token_address,
                    ):
                        op = Op.SHOULD_BUY
                    else:
                        self.info("Scam. Skipping.")
                        op = Op.EXIT

                case Op.SHOULD_BUY:
                    pool_state = self.get_pool_state(self.client, pool_keys)
                    self.info(f"POOL STATE: {pool_state}")
                    if pool_state.quote_reserve >= min_amount_in_sol:
                        self.info(
                            f"INITIAL RESERVES BASE {pool_state.base_reserve:_.{self.amount_precision}f}"
                        )
                        self.info(
                            f"INITIAL RESERVES QUOTE {pool_state.quote_reserve:_.{self.amount_precision}f}"
                        )
                        self.info(
                            f"INITIAL PRICE BASE {pool_state.base_price:.{self.price_precision}f}"
                        )
                        self.info(
                            f"INITIAL PRICE QUOTE {pool_state.quote_price:.{self.price_precision}f}"
                        )
                        op = Op.BUY
                    else:
                        op = Op.EXIT

                case Op.BUY:
                    if await self.buy(pool_keys, buy_params):
                        self.info(">>> BOUGHT")
                        pool_state = self.get_pool_state(self.client, pool_keys)
                        bought_price = pool_state.quote_price
                        self.bought_beeper()
                        self.open_browser(pool_keys.pair_address)
                        self.info(
                            f"Swapped {pool_keys.token_address} for {buy_amount_in_sol:.{self.amount_precision}} SOL at price {bought_price:.{self.price_precision}f} XXX/SOL"
                        )
                        op = Op.SHOULD_SELL
                    else:
                        op = Op.EXIT

                case Op.SHOULD_SELL:
                    pool_state = self.get_pool_state(self.client, pool_keys)

                    if not pool_state:
                        self.info(
                            f"{pool_keys.token_address}  [------- SOL]  {{-.------------------}}  (---.--%/{take_profit:.{self.profit_precision}f}%)"
                        )
                        await asyncio.sleep(self.tick)

                    current_price = pool_state.quote_price
                    profit = (current_price / bought_price) * 100 - 100
                    profit = round(profit, self.profit_precision)

                    self.info(
                        f"{pool_keys.token_address}  [{pool_state.quote_reserve:7.2f} SOL]  {{{current_price:.{self.price_precision}f}}}  ({profit:.{self.profit_precision}f}%/{take_profit:.{self.profit_precision}f}%)"
                    )

                    if profit >= take_profit or profit <= stop_loss:
                        op = Op.SELL
                    else:
                        await asyncio.sleep(self.tick)

                case Op.SELL:
                    number_of_tries_to_sell += 1
                    self.info(f"Number of tries to sell: {number_of_tries_to_sell}")
                    if await self.sell(pool_keys, sell_params):
                        self.info("<<< SOLD")
                        pool_state = self.get_pool_state(self.client, pool_keys)
                        sold_price = pool_state.quote_price
                        self.sold_beeper()
                        self.info(
                            f"Swapped {pool_keys.token_address} for ~{buy_amount_in_sol:.{self.amount_precision}f} SOL at price {sold_price:.{self.price_precision}f} SOL/X!"
                        )
                        op = Op.EXIT

                    if number_of_tries_to_sell > 3:
                        self.info(
                            f"Failed to sell {number_of_tries_to_sell} times. Saved as memories."
                        )
                        op = Op.EXIT

                case Op.EXIT:
                    return
