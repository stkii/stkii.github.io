"""The computer player.

Only :class:`Engine` and :class:`Decision` are meant to be imported
from outside this package; everything behind them is free to change.

This sits beside `core/` rather than inside it because the rules are
settled while everything here is opinion: weights fitted by hand, and
thresholds measured on one machine that will want measuring on another.

"""

from docs.games.othello.strategy.engine import Decision, Engine

__all__ = ["Decision", "Engine"]
