from dataclasses import dataclass, asdict

from raydium_py.raydium.amm_v4 import sell
from raydium_py.raydium.gas import GasConfig
from raydium_py.utils.pool_utils import AmmV4PoolKeys


@dataclass
class SellParams:
    percentage: float
    slippage: int
    gas_config: GasConfig


class SellerMixin:
    async def sell(self, pool_keys: AmmV4PoolKeys, params: SellParams) -> bool:
        if self.dry_run:
            self.info("DRY RUN MODE! Not really selling...")
            return True

        self.info(f"<<< TRY SELL {params.percentage:.{self.profit_precision}f}% TOKEN")
        return sell(
            client=self.client,
            sender=self.sender,
            pool_keys=pool_keys,
            **asdict(params),
        )
