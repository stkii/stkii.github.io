"""Bitboard primitives for the Othello rules.

A board is two 64-bit integers, one per player, each bit standing for
one square. The bit for ``(row, col)`` is ``1 << (row * 8 + col)``.

Everything here is a module-level function taking and returning plain
integers. The search calls these millions of times per move, and in
CPython an attribute lookup costs about as much as the arithmetic it
guards, so there are deliberately no classes and no ``self``.

Shifting by 1 walks along a row and can therefore wrap from one row
into the next. The fix is to strip the squares a walk must never enter
from the *opponent* set before walking it, which is what the masks
below are for. Dropping the far edge as well costs nothing: a stone on
the edge can never be an *inner* stone of a flipped line, because the
line has no room left for the stone that closes it.

The eight direction walks are written out in full rather than looped
over a table of shifts, which is what the ``PLR0915`` suppressions
below are for: the loop would add a tuple unpack and two name lookups
to every step of the innermost code in the program.

"""

from collections.abc import Iterator

# Every square, used to bring Python's unbounded integers back to 64 bits.
FULL: int = 0xFFFFFFFFFFFFFFFF

MASK_H: int = 0x7E7E7E7E7E7E7E7E  # drops columns 0 and 7
MASK_V: int = 0x00FFFFFFFFFFFF00  # drops rows 0 and 7
MASK_D: int = 0x007E7E7E7E7E7E00  # drops both

# The four corners, and the four squares diagonally inside them.
CORNERS: int = 0x8100000000000081
X_SQUARES: int = 0x0042000000004200


def popcount(bits: int) -> int:
    """Count the set bits.

    Parameters
    ----------
    bits : int
        The bitboard to count

    Returns
    -------
    int
        The number of stones it holds.

    """
    return bits.bit_count()


def to_index(row: int, col: int) -> int:
    """Convert a row and column to a bit index.

    Parameters
    ----------
    row : int
        The row index (0-based)
    col : int
        The column index (0-based)

    Returns
    -------
    int
        The bit position the square occupies.

    """
    return row * 8 + col


def moves(me: int, opp: int) -> int:  # noqa: PLR0915
    """Get every square the player to move may play on.

    Parameters
    ----------
    me : int
        The stones of the player to move
    opp : int
        The stones of the opponent

    Returns
    -------
    int
        A bitboard of the legal moves, empty when the player must pass.

    Notes
    -----
    Each direction is walked with the shift-and-or chain known as a
    dumb7fill: ``t`` collects the unbroken run of opponent stones
    leaving every one of the player's stones, and one more shift then
    lands on the square that would close the run.

    """
    empty = ~(me | opp) & FULL
    result = 0

    m = opp & MASK_H
    t = m & (me << 1)
    t |= m & (t << 1)
    t |= m & (t << 1)
    t |= m & (t << 1)
    t |= m & (t << 1)
    t |= m & (t << 1)
    result |= t << 1
    t = m & (me >> 1)
    t |= m & (t >> 1)
    t |= m & (t >> 1)
    t |= m & (t >> 1)
    t |= m & (t >> 1)
    t |= m & (t >> 1)
    result |= t >> 1

    m = opp & MASK_V
    t = m & (me << 8)
    t |= m & (t << 8)
    t |= m & (t << 8)
    t |= m & (t << 8)
    t |= m & (t << 8)
    t |= m & (t << 8)
    result |= t << 8
    t = m & (me >> 8)
    t |= m & (t >> 8)
    t |= m & (t >> 8)
    t |= m & (t >> 8)
    t |= m & (t >> 8)
    t |= m & (t >> 8)
    result |= t >> 8

    m = opp & MASK_D
    t = m & (me << 9)
    t |= m & (t << 9)
    t |= m & (t << 9)
    t |= m & (t << 9)
    t |= m & (t << 9)
    t |= m & (t << 9)
    result |= t << 9
    t = m & (me >> 9)
    t |= m & (t >> 9)
    t |= m & (t >> 9)
    t |= m & (t >> 9)
    t |= m & (t >> 9)
    t |= m & (t >> 9)
    result |= t >> 9

    t = m & (me << 7)
    t |= m & (t << 7)
    t |= m & (t << 7)
    t |= m & (t << 7)
    t |= m & (t << 7)
    t |= m & (t << 7)
    result |= t << 7
    t = m & (me >> 7)
    t |= m & (t >> 7)
    t |= m & (t >> 7)
    t |= m & (t >> 7)
    t |= m & (t >> 7)
    t |= m & (t >> 7)
    result |= t >> 7

    return result & empty


def flips(me: int, opp: int, square: int) -> int:  # noqa: PLR0915
    """Get the stones a move captures.

    Parameters
    ----------
    me : int
        The stones of the player to move
    opp : int
        The stones of the opponent
    square : int
        A bitboard holding the single square being played on

    Returns
    -------
    int
        A bitboard of the opponent stones the move turns over, empty
        when the move is illegal.

    Notes
    -----
    Same walk as :func:`moves`, but starting from the played square
    and kept only when one of the player's own stones closes the run.

    """
    captured = 0

    m = opp & MASK_H
    t = m & (square << 1)
    t |= m & (t << 1)
    t |= m & (t << 1)
    t |= m & (t << 1)
    t |= m & (t << 1)
    t |= m & (t << 1)
    if (t << 1) & me:
        captured |= t
    t = m & (square >> 1)
    t |= m & (t >> 1)
    t |= m & (t >> 1)
    t |= m & (t >> 1)
    t |= m & (t >> 1)
    t |= m & (t >> 1)
    if (t >> 1) & me:
        captured |= t

    m = opp & MASK_V
    t = m & (square << 8)
    t |= m & (t << 8)
    t |= m & (t << 8)
    t |= m & (t << 8)
    t |= m & (t << 8)
    t |= m & (t << 8)
    if (t << 8) & me:
        captured |= t
    t = m & (square >> 8)
    t |= m & (t >> 8)
    t |= m & (t >> 8)
    t |= m & (t >> 8)
    t |= m & (t >> 8)
    t |= m & (t >> 8)
    if (t >> 8) & me:
        captured |= t

    m = opp & MASK_D
    t = m & (square << 9)
    t |= m & (t << 9)
    t |= m & (t << 9)
    t |= m & (t << 9)
    t |= m & (t << 9)
    t |= m & (t << 9)
    if (t << 9) & me:
        captured |= t
    t = m & (square >> 9)
    t |= m & (t >> 9)
    t |= m & (t >> 9)
    t |= m & (t >> 9)
    t |= m & (t >> 9)
    t |= m & (t >> 9)
    if (t >> 9) & me:
        captured |= t

    t = m & (square << 7)
    t |= m & (t << 7)
    t |= m & (t << 7)
    t |= m & (t << 7)
    t |= m & (t << 7)
    t |= m & (t << 7)
    if (t << 7) & me:
        captured |= t
    t = m & (square >> 7)
    t |= m & (t >> 7)
    t |= m & (t >> 7)
    t |= m & (t >> 7)
    t |= m & (t >> 7)
    t |= m & (t >> 7)
    if (t >> 7) & me:
        captured |= t

    return captured


def iter_squares(bits: int) -> Iterator[int]:
    """Iterate the set bits, one isolated bitboard at a time.

    Parameters
    ----------
    bits : int
        The bitboard to walk

    Yields
    ------
    int
        A bitboard holding one square, lowest square first.

    """
    while bits:
        low = bits & -bits
        yield low
        bits ^= low
