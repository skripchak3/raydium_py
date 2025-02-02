from enum import Enum


class Op(Enum):
    NOOP = 0
    CHECK = 1
    SHOULD_BUY = 2
    BUY = 3
    SHOULD_SELL = 4
    SELL = 5
    EXIT = 6
