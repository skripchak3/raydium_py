from dataclasses import dataclass


@dataclass
class GasConfig:
    limit: int
    price: int
