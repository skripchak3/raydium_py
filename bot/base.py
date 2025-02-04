from solana.rpc.api import Client
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Commitment

from solders.solders import Keypair
from mixins.args_parser import ArgsParser
from mixins.beeper import BeeperMixin
from mixins.browser_opener import BrowserOpenerMixin
from mixins.buyer import BuyerMixin
from mixins.checker import CheckerMixin
from mixins.logger import LoggerMixin
from mixins.new_token_watcher import NewTokenWatcher
from mixins.pool_keys import PoolKeysMixin
from mixins.pool_state import PoolStateMixin
from mixins.seller import SellerMixin
from mixins.single_token_watcher import SingleTokenWatcher
from raydium_py.raydium.gas import GasConfig

DEBUG = True


class RaydiumBot(
    ArgsParser,
    CheckerMixin,
    PoolKeysMixin,
    PoolStateMixin,
    BuyerMixin,
    SellerMixin,
    LoggerMixin,
    SingleTokenWatcher,
    NewTokenWatcher,
    BeeperMixin,
    BrowserOpenerMixin,
):
    def __init__(self):
        super().__init__()
        self.init_logger()

        args = self.parse_args()

        if DEBUG:
            from dotenv import load_dotenv

            load_dotenv()
            from os import getenv

            args.private_key = getenv("PRIVATE_KEY")
            args.api_key = getenv("RPC_API_KEY")
            self.info(f"Started with args {args}")

        self.sender = Keypair.from_base58_string(args.private_key)
        self.me = self.sender.pubkey()
        self.http_endpoint = args.http_url.format(api_key=args.api_key)
        self.ws_endpoint = args.ws_url.format(api_key=args.api_key)
        self.commitment = Commitment(args.commitment)

        self.client = Client(
            endpoint=self.http_endpoint, commitment=self.commitment, timeout=2
        )
        self.async_client = AsyncClient(
            endpoint=self.http_endpoint, commitment=self.commitment, timeout=2
        )

        self.gas_config = GasConfig(limit=100_000, price=args.gas_price)

        self.profit_precision = 3
        self.price_precision = 18
        self.amount_precision = 2

        self.swap_fee = 0.25  # need to figure out
        self.tick = 0.25  # check price every X seconds

        self.dry_run = False
        self.beep = False
        self.browser = False
