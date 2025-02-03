import asyncio

import pandas

from bot.mixins.buyer import BuyParams
from bot.mixins.seller import SellParams
from bot.ops import Op
from raydium_py.utils.pool_utils import AmmV4PoolKeys


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
                    await self.macd()
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
                        await self.macd()
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
                    await self.macd()

                    if not pool_state:
                        self.info(
                            f"{pool_keys.token_address}  [------- SOL]  {{-.------------------}}  (---.--%/{take_profit:.{self.profit_precision}f}%)"
                        )
                        await asyncio.sleep(self.tick)
                    else:
                        current_price = pool_state.quote_price
                        profit = (current_price / bought_price) * 100 - 100
                        profit = round(profit, self.profit_precision)

                        self.info(
                            f"{pool_keys.token_address}  [{pool_state.quote_reserve:7.2f} SOL]  {{{current_price:.{self.price_precision}f}}}  ({profit:.{self.profit_precision}f}%/{take_profit:.{self.profit_precision}f}%)"
                        )

                        if profit >= take_profit:
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
                        number_of_tries_to_sell = 0
                        self.info("<<< SOLD")
                        pool_state = self.get_pool_state(self.client, pool_keys)
                        await self.macd()
                        sold_price = pool_state.quote_price
                        self.sold_beeper()
                        self.info(
                            f"Swapped {pool_keys.token_address} for ~{buy_amount_in_sol:.{self.amount_precision}f} SOL at price {sold_price:.{self.price_precision}f} SOL/X!"
                        )
                        bought_price = pool_state.quote_price

                        if (
                            pool_state.base_reserve <= 1
                            or sell_params.percentage == 100
                        ):
                            op = Op.EXIT
                        else:
                            op = Op.SHOULD_SELL

                    if number_of_tries_to_sell > 3:
                        self.info(
                            f"Failed to sell {number_of_tries_to_sell} times. Saved as memories."
                        )
                        op = Op.EXIT

                case Op.EXIT:
                    return

    async def macd(self):
        # Print the first few entries to verify
        # Now, let's calculate the MACD indicator (you'll need the TA-Lib library for this or implement it manually)
        # Here's a manual implementation for demonstration:

        # MACD parameters
        short_window = 12
        long_window = 26
        signal_window = 9

        # Calculate the short and long EMAs
        short_ema = self.prices.ewm(span=short_window, adjust=False).mean()
        long_ema = self.prices.ewm(span=long_window, adjust=False).mean()

        # Calculate MACD line and signal line
        macd_line = short_ema - long_ema
        signal_line = macd_line.ewm(span=signal_window, adjust=False).mean()

        curr_diff = macd_line - signal_line
        prev_diff = curr_diff.shift(1)

        prev_lt_zero = prev_diff < 0
        curr_gt_zero = curr_diff > 0

        prev_gt_zero = prev_diff > 0
        curr_lt_zero = curr_diff < 0

        buy_signal = curr_gt_zero & prev_lt_zero
        sell_signal = curr_lt_zero & prev_gt_zero

        # Create a DataFrame for visualization or further analysis
        macd_df = pandas.DataFrame(
            {
                "Price": self.prices,
                "MACD": macd_line,
                "Signal": signal_line,
                "BUY": buy_signal,
                "SELL": sell_signal,
            }
        )

        if buy_signal.iloc[-1]:
            print("BUY")
        if sell_signal.iloc[-1]:
            print("SELL")

        # print("BUY = {} | SELL = {}".format(buy_signal.iloc[-1], sell_signal.iloc[-1]))
        pandas.options.display.float_format = "{:.9f}".format

        # Display the last few entries of the MACD DataFrame
        # print(macd_df.tail())
