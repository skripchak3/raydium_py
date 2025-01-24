from asyncio import sleep

from raydium_py.utils.pool_utils import fetch_amm_v4_pool_keys, get_amm_v4_reserves

MIN_BASE_AMOUNT = 800


async def is_buy(pair_address: str) -> bool:
    pool_keys = fetch_amm_v4_pool_keys(pair_address)
    (quote_amount, base_amount, quote_decimal) = get_amm_v4_reserves(pool_keys)
    print(f"Token amount in SOL: {base_amount}")
    print(f"Price: {base_amount / quote_amount} X/SOL")
    return base_amount >= MIN_BASE_AMOUNT


async def watcher(pair_address: str):
    pool_keys = fetch_amm_v4_pool_keys(pair_address)
    first_price = True
    price = 0
    while True:
        (quote_amount, base_amount, quote_decimal) = get_amm_v4_reserves(pool_keys)
        print(f"Token amount in SOL: {base_amount}")
        print(f"Price: {base_amount / quote_amount} X/SOL")
        if first_price:
            price = base_amount / quote_amount
            first_price = False
        else:
            print(f"Profit %: {(base_amount / quote_amount) / price}")
        await sleep(1)
