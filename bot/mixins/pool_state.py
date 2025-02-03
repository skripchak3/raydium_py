from dataclasses import dataclass
from typing import Optional

from solana.rpc.api import Client

from raydium_py.utils.pool_utils import AmmV4PoolKeys, get_amm_v4_reserves


@dataclass
class PoolState:
    base_reserve: float
    quote_reserve: float
    base_price: float
    quote_price: float
    token_decimal: int


class PoolStateMixin:

    def get_pool_state(
        self,
        client: Client,
        pool_keys: AmmV4PoolKeys,
    ) -> Optional[PoolState]:
        (base_reserve, quote_reserve, token_decimal) = get_amm_v4_reserves(
            client, pool_keys
        )

        if not (base_reserve and quote_reserve):
            return None

        return PoolState(
            base_reserve=base_reserve,
            quote_reserve=quote_reserve,
            base_price=base_reserve / quote_reserve,
            quote_price=quote_reserve / base_reserve,
            token_decimal=token_decimal,
        )
