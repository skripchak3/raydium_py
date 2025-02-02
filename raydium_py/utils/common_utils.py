import json
import time
from pprint import pprint
from typing import Optional

from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed, Processed, Commitment
from solana.rpc.types import TokenAccountOpts
from solders.pubkey import Pubkey  # type: ignore
from solders.signature import Signature  # type: ignore


def get_token_balance(
    client: Client,
    sender_address: Pubkey,
    token_address: Pubkey,
    commitment: Commitment = Processed,
) -> Optional[float]:
    try:
        response = client.get_token_accounts_by_owner_json_parsed(
            sender_address, TokenAccountOpts(mint=token_address), commitment=commitment
        )

        if accounts := response.value:
            if token_amount := accounts[0].account.data.parsed["info"]["tokenAmount"][
                "uiAmount"
            ]:
                return float(token_amount)
    except Exception as e:
        print("get_token_balance", e)
        return None


def confirm_txn(
    client: Client,
    txn_sig: Signature,
    max_retries: int = 20,
    retry_interval: int = 0.5,
    commitment: Commitment = Confirmed,
) -> bool:
    retries = 1

    while retries < max_retries:
        try:
            txn_res = client.get_transaction(
                txn_sig,
                commitment=commitment,
                max_supported_transaction_version=0,
            )

            if txn_res:
                if txn_res.value:
                    return True

            # txn_json = json.loads(txn_res.value.transaction.meta.to_json())
            #
            # if txn_json["err"] is None:
            #     print("Transaction confirmed... try count:", retries)
            #     return True
            #
            # print("Error: Transaction not confirmed. Retrying...")
            # if txn_json["err"]:
            #     print("Transaction failed.")
            #     return False
        except Exception as e:
            print("Awaiting confirmation... try count:", retries)
            retries += 1
            time.sleep(retry_interval)

    print("Max retries reached. Transaction confirmation failed.")
    return None
