from dataclasses import dataclass, asdict

from raydium_py.raydium.amm_v4 import buy
from raydium_py.raydium.gas import GasConfig
from raydium_py.utils.pool_utils import AmmV4PoolKeys


@dataclass
class BuyParams:
    sol_in: float
    slippage: int
    gas_config: GasConfig


class BuyerMixin:
    async def buy(self, pool_keys: AmmV4PoolKeys, params: BuyParams) -> bool:
        if self.dry_run:
            self.info("DRY RUN MODE! Not really buying...")
            return True

        self.info(f">>> TRY BUY {params.sol_in:.{self.profit_precision}f} SOL")
        return buy(
            client=self.client,
            sender=self.sender,
            pool_keys=pool_keys,
            **asdict(params),
        )
