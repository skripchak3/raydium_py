import argparse

from solana.rpc.commitment import Commitment


class ArgsParser:

    def parse_args(self):
        parser = argparse.ArgumentParser(
            description="CLI tool to trade memes on Raydium V4."
        )

        # only this two is mandatory
        parser.add_argument(
            "--private-key",
            # required=True,
            type=str,
            help="PRIVATE_KEY for the application.",
        )
        # For API_KEY, you might want to allow the user to supply a value or fallback to an environment variable
        parser.add_argument(
            "--api-key",
            # required=True,
            type=str,
            help="API_KEY for the application.",
        )

        # default values
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=True,
            help="Enable DRY_RUN mode (default: True).",
        )
        parser.add_argument(
            "--open-browser",
            action="store_true",
            default=True,
            help="Enable OPEN_BROWSER (default: True).",
        )
        # parser.add_argument(
        #     "--multi-buy",
        #     action="store_true",
        #     default=False,
        #     help="Enable MULTI_BUY (default: False).",
        # )
        # parser.add_argument(
        #     "--n",
        #     type=int,
        #     default=1,
        #     help="N (default: 1).",
        # )
        parser.add_argument(
            "--beep",
            action="store_true",
            default=True,
            help="Enable BEEP (default: True).",
        )
        parser.add_argument(
            "--check",
            action="store_true",
            default=False,
            help="CHECK (default: False).",
        )
        parser.add_argument(
            "--min",
            type=float,
            default=180.0,
            help="MIN (default: 180.0).",
        )
        parser.add_argument(
            "--take-profit",
            type=float,
            default=3.9,
            help="TAKE PROFIT (default: 3.9).",
        )
        parser.add_argument(
            "--stop-loss",
            type=float,
            default=-60.0,
            help="STOP LOSS (default: -60.0).",
        )
        parser.add_argument(
            "--amount",
            type=float,
            default=0.02,
            help="AMOUNT (default: 0.02).",
        )
        parser.add_argument(
            "--buy-slippage",
            type=int,
            default=50,
            help="BUY_SLIPPAGE (default: 50).",
        )
        parser.add_argument(
            "--sell-slippage",
            type=int,
            default=99,
            help="SELL_SLIPPAGE (default: 99).",
        )
        parser.add_argument(
            "---gas-price",
            type=int,
            default=500_000,
            help="GAS_PRICE (default: 500_000).",
        )
        parser.add_argument(
            "--commitment",
            type=str,
            default="confirmed",
            help='COMMITMENT setting (default: "confirmed").',
        )
        parser.add_argument(
            "--pair-address-idx",
            type=int,
            default=2,
            help="PAIR_ADDRESS_IDX (default: 2).",
        )
        parser.add_argument(
            "--http-url",
            type=str,
            default="https://mainnet.helius-rpc.com/?api-key={api_key}",
            help='HTTP_URL (default: "https://mainnet.helius-rpc.com/?api-key={}")',
        )
        parser.add_argument(
            "--ws-url",
            type=str,
            default="wss://mainnet.helius-rpc.com/?api-key={api_key}",
            help='WS_URL (default: "wss://mainnet.helius-rpc.com/?api-key={}")',
        )

        parser.add_argument(
            "--delay",
            type=float,
            default=30.0,
            help="Delay in seconds before each check cycle (default: 30.0)",
        )

        return parser.parse_args()
