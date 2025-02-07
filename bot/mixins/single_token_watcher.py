import asyncio

from mixins.buyer import BuyParams
from mixins.seller import SellParams
from ops import Op
from raydium_py.utils.pool_utils import AmmV4PoolKeys
from raydium_py.utils.common_utils import get_token_balance


class SingleTokenWatcher:
    async def watch_single(
        self,
        pool_keys: AmmV4PoolKeys,
        buy_amount_in_sol: float,
        sell_amount_in_percent: float,
        min_amount_in_sol: float,
        take_profit: float,
        stop_loss: float,
        buy_slippage: int = 50,
        sell_slippage: int = 99,
        delay: float = 30.0,
        op: Op = Op.CHECK,
    ):
        buy_params = BuyParams(
            sol_in=buy_amount_in_sol,
            slippage=buy_slippage,
            gas_config=self.gas_config,
        )
        sell_params = SellParams(
            percentage=sell_amount_in_percent,
            slippage=sell_slippage,
            gas_config=self.gas_config,
            initial_token_balance=0,
        )

        bought_price = None

        pool_state = None

        initial_token_balance = None
        remaining = None
        all_profit = 0

        self.info(
            f"""Token address:
                    https://solscan.io/token/{pool_keys.token_address}"""
        )

        self.info(
            f"""Pair address:
                    https://photon-sol.tinyastro.io/en/lp/{pool_keys.pair_address}
                    https://dexscreener.com/solana/{pool_keys.pair_address}"""
        )
        self.info(
            f"""Me:
                    {self.me}
                    https://solscan.io/account/{self.me}"""
        )
        self.info("")
        i = 1
        number_of_tries_to_sell = 0
        while op != Op.EXIT:
            match op:
                case Op.CHECK:
                    if delay:
                        self.info(f"Waiting {delay} seconds before checking.")

                    await asyncio.sleep(delay)

                    if await self.check_all(
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
                    # await self.macd()
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
                        self.info('Skiping...')
                        op = Op.EXIT

                case Op.BUY:
                    if await self.buy(pool_keys, buy_params):
                        self.info(">>> BOUGHT")
                        pool_state = self.get_pool_state(self.client, pool_keys)
                        # await self.macd()
                        bought_price = pool_state.quote_price
                        all_profit = 0

                        sender_address = self.sender.pubkey()
                        initial_token_balance = get_token_balance(self.client, sender_address, pool_keys.token_address)
                        sell_params.initial_token_balance = initial_token_balance
                        remaining = initial_token_balance
                        
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
                    # await self.macd()

                    if not pool_state:
                        self.info(
                            f"{pool_keys.token_address}  [------- SOL]  {{-.------------------}}  (---.--%/{take_profit:.{self.profit_precision}f}%)"
                        )
                        await asyncio.sleep(self.tick)
                    else:
                        current_price = pool_state.quote_price
                        profit = ((current_price / bought_price) * 100 - 100) - all_profit
                        profit = round(profit, self.profit_precision)
                        sell_amount_token = initial_token_balance * (take_profit / 100)

                        self.info(
                            f"#{i:03d} {pool_keys.token_address} [{pool_state.quote_reserve:7.2f} SOL]  {{{current_price:.{self.price_precision}f}}}  ({profit:.{self.profit_precision}f}%/{take_profit:.{self.profit_precision}f}%)"
                        )
                        self.info(remaining)
                        if remaining < sell_amount_token:
                            op = Op.BUY

                        if profit >= take_profit:
                            # remaining -= sell_amount_token
                            sell_params.percentage = take_profit
                            op = Op.SELL
                        elif profit <= stop_loss:
                            sell_params.percentage = 100
                            op = Op.SELL
                        elif pool_state.base_reserve <= 1:
                            op = Op.EXIT
                        else:
                            await asyncio.sleep(self.tick)

                case Op.SELL:
                    number_of_tries_to_sell += 1
                    self.info(f"Number of tries to sell: {number_of_tries_to_sell}")
                    if await self.sell(pool_keys, sell_params):
                        i += 1
                        number_of_tries_to_sell = 0
                        self.info("<<< SOLD")
                        pool_state = self.get_pool_state(self.client, pool_keys)
                        # await self.macd()
                        sold_price = pool_state.quote_price
                        self.sold_beeper()
                        self.info(
                            f"Swapped {pool_keys.token_address} for ~{buy_amount_in_sol:.{self.amount_precision}f} SOL at price {sold_price:.{self.price_precision}f} SOL/X!"
                        )
                        # bought_price = pool_state.quote_price
                        all_profit += take_profit
                        remaining -= initial_token_balance * (take_profit / 100)

                        if (
                            pool_state.base_reserve <= 1
                            or sell_params.percentage == 100
                        ):
                            op = Op.EXIT
                        else:
                            op = Op.SHOULD_SELL

                    if number_of_tries_to_sell > 1:
                        self.info(
                            f"Failed to sell {number_of_tries_to_sell} times. Saved as memories."
                        )
                        op = Op.EXIT

                case Op.EXIT:
                    return
