"""Static evaluation of a position not worth searching further.

Scores are from the point of view of the player to move, in hundredths
of a stone, so the midgame search and the endgame solver share one
scale.

What wins games is not holding stones but taking away the opponent's
choices: for most of the game a stone lead is worth almost nothing and
a move the opponent lacks is worth a great deal, and only as the board
fills does the disc count carry weight. The weights are interpolated
between three anchor phases rather than switched at a boundary, so a
position never jumps in value from a single stone.

"""

from typing import NamedTuple

from docs.games.othello.bitboard import CORNERS, FULL, X_SQUARES, moves, popcount

# Columns and rows on the rim, used to notice that a stone has no
# neighbour on one side and therefore cannot be bracketed from it.
COL_A: int = 0x0101010101010101
COL_H: int = 0x8080808080808080
ROW_1: int = 0x00000000000000FF
ROW_8: int = 0xFF00000000000000
RIM: int = COL_A | COL_H | ROW_1 | ROW_8

NOT_COL_A: int = FULL ^ COL_A
NOT_COL_H: int = FULL ^ COL_H

# A win is worth more than any arrangement of stones can be.
WIN_SCORE: int = 1_000_000

# Below this many empty squares, stability is worth computing.
STABILITY_FROM: int = 44


class Weights(NamedTuple):
    """How much each judgement of a position is worth at one moment.

    Attributes
    ----------
    mobility : int
        Value of holding every legal move on the board
    potential : int
        Value of holding every empty square next to an enemy stone
    frontier : int
        Cost of every own stone that touches an empty square
    corner : int
        Value of holding all four corners
    stability : int
        Value of stones that can no longer be turned over
    discs : int
        Value of the stone count itself

    """

    mobility: int
    potential: int
    frontier: int
    corner: int
    stability: int
    discs: int


# Anchors the live weights are interpolated between.
_OPENING = Weights(1000, 350, 220, 1600, 300, 0)
_MIDGAME = Weights(900, 250, 160, 1500, 900, 40)
_ENDING = Weights(300, 60, 40, 900, 1300, 400)

# The empty counts the anchors are written for.
_OPENING_EMPTIES: int = 44
_MIDGAME_EMPTIES: int = 24


def neighbours(bits: int) -> int:
    """Get the squares touching a set of squares.

    Parameters
    ----------
    bits : int
        The squares to spread out from

    Returns
    -------
    int
        The eight-way neighbourhood, excluding the input squares.

    """
    spread = bits | ((bits & NOT_COL_A) >> 1) | ((bits & NOT_COL_H) << 1)
    spread |= (spread >> 8) | ((spread << 8) & FULL)
    return spread & ~bits & FULL


def stable_discs(me: int) -> int:
    """Get the stones that can never be turned over again.

    Parameters
    ----------
    me : int
        The stones being tested

    Returns
    -------
    int
        A bitboard of the stones that are safe for the rest of the game.

    Notes
    -----
    A stone survives along one direction once the rim or another stone
    already known to be safe closes the line on either side. Corners
    satisfy this in all four directions with nothing to build on, so
    the fixed point grows outwards from them and needs no seeding.

    The test is deliberately one-sided: a stone is only called safe
    when it provably is, so a full line whose safety comes from having
    no empty square left is missed. Undercounting costs a little
    accuracy in the midgame and nothing at the end, where the solver
    plays the position out exactly instead.

    """
    if not me & CORNERS:
        return 0

    stable = 0
    while True:
        horizontal = COL_A | COL_H | ((stable >> 1) & NOT_COL_H) | ((stable << 1) & NOT_COL_A)
        vertical = ROW_1 | ROW_8 | (stable >> 8) | ((stable << 8) & FULL)
        diagonal = RIM | ((stable >> 9) & NOT_COL_H) | ((stable << 9) & NOT_COL_A)
        anti_diagonal = RIM | ((stable >> 7) & NOT_COL_A) | ((stable << 7) & NOT_COL_H)

        grown = me & horizontal & vertical & diagonal & anti_diagonal
        if grown == stable:
            return stable
        stable = grown


def _balance(mine: int, theirs: int, weight: int) -> int:
    """Score one contested quantity, scaled by how lopsided it is.

    Parameters
    ----------
    mine : int
        The count belonging to the player to move
    theirs : int
        The count belonging to the opponent
    weight : int
        The value of holding the quantity outright

    Returns
    -------
    int
        A score running from ``-weight`` to ``+weight``.

    Notes
    -----
    A one move lead matters far more when there are two moves on the
    board than when there are twenty, so the difference is taken as a
    ratio rather than a subtraction.

    """
    total = mine + theirs
    if total == 0:
        return 0
    return weight * (mine - theirs) // total


def weights_for(empties: int) -> Weights:
    """Get the weight vector for how far along the game is.

    Parameters
    ----------
    empties : int
        The number of empty squares left

    Returns
    -------
    Weights
        The weights interpolated between the surrounding anchors.

    """
    if empties >= _OPENING_EMPTIES:
        return _OPENING

    if empties >= _MIDGAME_EMPTIES:
        first, second = _OPENING, _MIDGAME
        span = _OPENING_EMPTIES - _MIDGAME_EMPTIES
        along = _OPENING_EMPTIES - empties
    else:
        first, second = _MIDGAME, _ENDING
        span = _MIDGAME_EMPTIES
        along = min(_MIDGAME_EMPTIES - empties, span)

    return Weights(
        *(start + (end - start) * along // span for start, end in zip(first, second, strict=True))
    )


def evaluate(me: int, opp: int, empties: int, legal: int) -> int:
    """Judge a position without searching it.

    Parameters
    ----------
    me : int
        The stones of the player to move
    opp : int
        The stones of the opponent
    empties : int
        The number of empty squares left
    legal : int
        The moves available to the player to move, which the caller has
        already had to generate to get here

    Returns
    -------
    int
        The value of the position to the player to move, in hundredths
        of a stone.

    """
    empty = ~(me | opp) & FULL
    weights = weights_for(empties)

    score = _balance(popcount(legal), popcount(moves(opp, me)), weights.mobility)

    # Empty squares next to the opponent are moves waiting to be had.
    score += _balance(
        popcount(neighbours(opp) & empty),
        popcount(neighbours(me) & empty),
        weights.potential,
    )

    # Stones touching an empty square are the ones that can be taken,
    # so holding fewer of them is better.
    score -= _balance(
        popcount(neighbours(empty) & me),
        popcount(neighbours(empty) & opp),
        weights.frontier,
    )

    score += weights.corner * (popcount(me & CORNERS) - popcount(opp & CORNERS)) // 4

    # A stone diagonally inside an empty corner hands that corner over,
    # and is the one square that is worse to hold than to leave alone.
    open_corners = CORNERS & empty
    if open_corners:
        exposed = X_SQUARES & neighbours(open_corners)
        score -= weights.corner * (popcount(me & exposed) - popcount(opp & exposed)) // 8

    if empties < STABILITY_FROM:
        safe = popcount(stable_discs(me)) - popcount(stable_discs(opp))
        score += weights.stability * safe // 16

    if weights.discs:
        score += _balance(popcount(me), popcount(opp), weights.discs)

    return score
