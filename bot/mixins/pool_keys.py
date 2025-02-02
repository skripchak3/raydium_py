from typing import Optional

from solders.solders import Pubkey

from raydium_py.utils.pool_utils import AmmV4PoolKeys, fetch_amm_v4_pool_keys


class PoolKeysMixin:
    def get_pool_keys(self, pair_address: Pubkey) -> Optional[AmmV4PoolKeys]:
        return fetch_amm_v4_pool_keys(client=self.client, amm_id=pair_address)
