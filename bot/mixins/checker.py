from typing import Optional

from solana.rpc.async_api import AsyncClient
from solders.solders import Pubkey, Mint


class CheckerMixin:
    async def get_account_mint(
        self, client: AsyncClient, address: Pubkey
    ) -> Optional[Mint]:
        account_info = await client.get_account_info(address)
        self.debug(f"Get account info: {account_info}")

        account_data = account_info.value.data
        self.debug(f"Account data: {account_data}")

        return Mint.from_bytes(account_data) if account_data else None

    async def check_mint_and_freeze(
        self, client: AsyncClient, token_address: Pubkey
    ) -> Optional[bool]:
        mint = await self.get_account_mint(client, token_address)
        self.debug(f"Mint: {mint}")
        self.info(f"Mint authority: {mint.mint_authority}")
        self.info(f"Freeze authority: {mint.freeze_authority}")

        return mint.mint_authority is None and mint.freeze_authority is None

    async def check_lp_burned(
        self, client: AsyncClient, lp_token_address: Pubkey
    ) -> Optional[bool]:
        mint = await self.get_account_mint(client, lp_token_address)
        self.debug(f"LP Mint: {mint}")
        self.info(f"LP Freeze authority: {mint.freeze_authority}")
        self.info(f"LP supply: {mint.supply}")

        return mint.freeze_authority is None and mint.supply == 0

    async def check_all(
        self, client: AsyncClient, token_address: Pubkey, lp_token_address: Pubkey
    ) -> Optional[bool]:
        mint_and_freeze_ok = await self.check_mint_and_freeze(client, token_address)
        lp_burned_ok = await self.check_lp_burned(client, lp_token_address)

        if mint_and_freeze_ok is None or lp_burned_ok is None:
            return None

        return mint_and_freeze_ok and lp_burned_ok
