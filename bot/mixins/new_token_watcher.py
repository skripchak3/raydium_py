import traceback
from typing import Optional

from solana.rpc.websocket_api import connect
from solders.solders import (
    RpcTransactionLogsFilterMentions,
    SubscriptionResult,
    LogsNotification,
    Signature,
    Pubkey,
)

from bot.ops import Op
from main_loop import PAIR_CREATED_EVENT, PAIR_ADDRESS_IDX
from raydium_py.raydium.constants import RAYDIUM_AMM_V4
from raydium_py.utils.pool_utils import AmmV4PoolKeys, fetch_amm_v4_pool_keys


class NewTokenWatcher:

    def is_pair_created(self, message) -> bool:
        try:
            return any(
                log for log in message.result.value.logs if PAIR_CREATED_EVENT in log
            )
        except:
            return False

    def get_transaction_accounts(self, tx_hash: Signature) -> Optional[list[str]]:
        try:
            tx = self.client.get_transaction(
                tx_hash,
                commitment=self.commitment,
                encoding="jsonParsed",
                max_supported_transaction_version=1,
            )
            return tx.value.transaction.transaction.message.account_keys
        except Exception as e:
            traceback.print_exc()
            print(f"Type: {type(e)}")
            print(f"Message: {e}")
            return None

    async def get_transaction_accounts_async(
        self, tx_hash: Signature
    ) -> Optional[list[str]]:
        try:
            tx = await self.async_client.get_transaction(
                tx_hash,
                commitment=self.commitment,
                encoding="jsonParsed",
                max_supported_transaction_version=1,
            )
            return tx.value.transaction.transaction.message.account_keys
        except Exception as e:
            traceback.print_exc()
            print(f"Type: {type(e)}")
            print(f"Message: {e}")
            return None

    def get_pool_keys(self, pair_address: Pubkey) -> Optional[AmmV4PoolKeys]:
        tries = 3
        while tries:
            if pool_keys := fetch_amm_v4_pool_keys(self.client, pair_address):
                return pool_keys

            tries -= 1

        return None

    async def watch_new_tokens(
        self,
        buy_amount_in_sol: float,
        sell_amount_in_percent: float,
        min_amount_in_sol: float,
        take_profit: float,
        stop_loss: float,
        buy_slippage: int = 50,
        sell_slippage: int = 99,
        op: Op = Op.CHECK,
    ):
        while True:
            self.info(
                f"Filter > {min_amount_in_sol} SOL\n"
                f"Take profit {take_profit}%\n"
                f"Stop lost {stop_loss}%\n"
                f"Buy amount {buy_amount_in_sol} SOL\n"
            )

            try:
                async with connect(self.ws_endpoint) as ws:
                    # subscribe to all events from Raydium V4
                    await ws.logs_subscribe(
                        filter_=RpcTransactionLogsFilterMentions(RAYDIUM_AMM_V4),
                        commitment=self.commitment,
                    )

                    # read first message with subscription id
                    match await ws.recv():
                        case [subscription] if isinstance(
                            subscription, SubscriptionResult
                        ):
                            # self.info("Subscription response", subscription)
                            ...

                    # filter only pair created events
                    async for message in ws:
                        match message:
                            case [message] if isinstance(
                                message, LogsNotification
                            ) and self.is_pair_created(message):
                                tx_hash = message.result.value.signature
                                self.info(
                                    f"""Pair created:
                                            https://solscan.io/tx/{tx_hash}"""
                                )

                                if not (
                                    accounts := self.get_transaction_accounts(tx_hash)
                                ):
                                    self.info(
                                        "Unknown transaction. No accounts. Skipping..."
                                    )
                                    continue

                                if not (
                                    pool_keys := self.get_pool_keys(
                                        accounts[PAIR_ADDRESS_IDX].pubkey
                                    )
                                ):
                                    self.info(
                                        "Unknown transaction. No pool keys. Skipping..."
                                    )
                                    continue

                                await self.watch_single(
                                    pool_keys=pool_keys,
                                    buy_amount_in_sol=buy_amount_in_sol,
                                    sell_amount_in_percent=sell_amount_in_percent,
                                    min_amount_in_sol=min_amount_in_sol,
                                    take_profit=take_profit,
                                    stop_loss=stop_loss,
                                    buy_slippage=buy_slippage,
                                    sell_slippage=sell_slippage,
                                    op=op,
                                )

                                self.info("")
                                self.info("=" * 80)
                                self.info("NEXT")
                                self.info("=" * 80)

            except KeyboardInterrupt:
                return
