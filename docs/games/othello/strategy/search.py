"""The move search, staged by how many squares are still empty.

While the board is open a position can only be judged; once few enough
squares remain the rest of the game fits in a search, and judging it
would throw away certainty that was there for the taking.

Two details follow Takizawa's proof that Othello is a draw
(arXiv:2310.19387), which splits the game the same way far higher up.
The endgame settles win/draw/loss before refining the score, because
the narrowest window that answers the question is much cheaper than
the exact margin. And the solver uses no aspiration windows: they help
a search that is guessing and hurt one that is proving.

"""

import time

from docs.games.othello.bitboard import flips, moves, popcount
from docs.games.othello.strategy.evaluation import WIN_SCORE, evaluate

# One stone, on the hundredths-of-a-stone scale the evaluation uses.
STONE: int = 100

# How often to look at the clock, in nodes. Reading the clock costs
# about as much as searching a node, so it cannot be done every time;
# but a node that sorts its moves costs many times a node that does
# not, so a long interval lets the overshoot grow well past the budget.
_CLOCK_INTERVAL: int = 1024

# Entries to keep before the table stops growing. Bounded because a
# deep endgame solve would otherwise fill the browser tab's memory;
# at roughly a few hundred bytes an entry this is tens of megabytes.
_MAX_TABLE: int = 150_000

# Bound kinds stored alongside a transposition table score.
_EXACT: int = 0
_LOWER: int = 1
_UPPER: int = 2

# Static square preferences, used to break ties in move ordering.
# Corners are worth taking, the squares beside them are worth avoiding.
_SQUARE_VALUE: tuple[int, ...] = (
    120, -20,  20,   5,   5,  20, -20, 120,
    -20, -40,  -5,  -5,  -5,  -5, -40, -20,
     20,  -5,  15,   3,   3,  15,  -5,  20,
      5,  -5,   3,   3,   3,   3,  -5,   5,
      5,  -5,   3,   3,   3,   3,  -5,   5,
     20,  -5,  15,   3,   3,  15,  -5,  20,
    -20, -40,  -5,  -5,  -5,  -5, -40, -20,
    120, -20,  20,   5,   5,  20, -20, 120,
)  # fmt: skip

# Below this many empties the ordering work costs more than it saves.
_ORDER_UNTIL: int = 8

# Stands in for the legal moves of a child whose parent skipped the
# ordering and so never generated them. Not a bitboard any position can
# hold, which an empty board would be: 0 means "must pass".
_UNSCOUTED: int = -1

# Remaining depth from which ordering by mobility pays for itself. One
# below this the children are leaves, so the ordering costs a move
# generation per move to save an evaluation per move, and alpha-beta
# has too little left to prune. Gating any higher loses more to the
# wider tree than it saves.
_SCOUT_FROM: int = 2

# How far a difference of one reply outranks every tie-breaker. Chosen
# so that the tie-breakers below cannot add up to one whole reply.
_MOBILITY_SHIFT: int = 10

# Ceiling on the learned ordering bonus, to keep it a tie-breaker.
_HISTORY_CAP: int = 400


class SearchTimeout(Exception):  # noqa: N818
    """Raised inside the search when the time budget has run out."""


class Search:
    """A single think, with its own clock and transposition table.

    Attributes
    ----------
    deadline : float
        The performance counter reading at which to give up
    nodes : int
        How many positions have been visited

    Notes
    -----
    One instance is one move's worth of thinking. The table is kept for
    the whole think so that the iterations of the deepening share their
    work, and dropped afterwards so that a stale evaluation from an
    earlier position can never be believed.

    """

    def __init__(self, time_limit: float) -> None:
        """Start the clock on a new search.

        Parameters
        ----------
        time_limit : float
            How many seconds the search may take

        """
        self.deadline: float = time.perf_counter() + time_limit
        self.nodes: int = 0
        self._table: dict[tuple[int, int], tuple[int, int, int, int]] = {}
        self._history: list[int] = [0] * 64
        self._checkpoint: int = _CLOCK_INTERVAL

    def _tick(self) -> None:
        """Give up on the search once the budget is gone."""
        self._checkpoint = self.nodes + _CLOCK_INTERVAL
        if time.perf_counter() >= self.deadline:
            raise SearchTimeout

    def _ordered_moves(
        self,
        me: int,
        opp: int,
        legal: int,
        best_first: int,
        *,
        scout: bool,
    ) -> list[tuple[int, int, int, int]]:
        """Sort the legal moves by how likely they are to be best.

        Parameters
        ----------
        me : int
            The stones of the player to move
        opp : int
            The stones of the opponent
        legal : int
            A bitboard of the moves to sort
        best_first : int
            A move to put at the front regardless, or 0 for none
        scout : bool
            Whether to work out the opponent's replies to each move,
            which orders far better but is the expensive part

        Returns
        -------
        list[tuple[int, int, int, int]]
            The moves as (square, captured stones, bit index, replies
            left to the opponent), best first.

        Notes
        -----
        Alpha-beta only prunes what it can already beat, so the order
        moves are tried in matters more to the size of the tree than
        anything else in the search. The strongest cheap predictor in
        Othello is how few replies the move leaves the opponent.

        Those replies are also, exactly, the legal moves of the child
        the move leads to, so they are handed back rather than worked
        out a second time down there. What is left of the cost is only
        the moves a cutoff means never visiting, which is what makes
        scouting worth switching off near the leaves.

        """
        scored: list[tuple[int, tuple[int, int, int, int]]] = []
        history = self._history
        remaining = legal
        while remaining:
            square = remaining & -remaining
            remaining ^= square
            index = square.bit_length() - 1
            captured = flips(me, opp, square)

            if scout:
                after_me = (me ^ captured) | square
                replies = moves(opp ^ captured, after_me)
            else:
                replies = _UNSCOUTED

            if square == best_first:
                # The table's move was best when this position was last
                # searched deeper than it is about to be searched now.
                scored.append((1 << 30, (square, captured, index, replies)))
                continue

            # Mobility decides the order outright and the rest only
            # separates moves it ties. Letting a corner bonus outweigh
            # a difference of several replies is what makes an ordering
            # look sensible and search badly.
            rank = -(popcount(replies) << _MOBILITY_SHIFT) if scout else 0
            rank += min(history[index] >> 6, _HISTORY_CAP)
            rank += _SQUARE_VALUE[index]
            scored.append((rank, (square, captured, index, replies)))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [move for _, move in scored]

    def _midgame(  # noqa: C901, PLR0911, PLR0912, PLR0913, PLR0915, PLR0917
        self,
        me: int,
        opp: int,
        depth: int,
        alpha: int,
        beta: int,
        passes: int,
        legal: int,
    ) -> int:
        """Search a position that is still too open to play out.

        Parameters
        ----------
        me : int
            The stones of the player to move
        opp : int
            The stones of the opponent
        depth : int
            How many more moves to look ahead
        alpha : int
            The best score the player to move is already assured of
        beta : int
            The best score the opponent is already assured of
        passes : int
            How many players in a row have just had to pass
        legal : int
            The moves available here, or ``_UNSCOUTED`` when the caller
            did not order its moves and so never worked them out

        Returns
        -------
        int
            The value of the position to the player to move.

        """
        self.nodes += 1
        if self.nodes >= self._checkpoint:
            self._tick()

        if legal == _UNSCOUTED:
            legal = moves(me, opp)

        if not legal:
            if passes:
                return STONE * (popcount(me) - popcount(opp))
            return -self._midgame(opp, me, depth, -beta, -alpha, passes + 1, moves(opp, me))

        empties = 64 - popcount(me | opp)
        if depth <= 0:
            return evaluate(me, opp, empties, legal)

        key = (me, opp)
        best_first = 0
        stored = self._table.get(key)
        if stored is not None:
            kept_depth, score, kind, best_first = stored
            if kept_depth >= depth:
                if kind == _EXACT:
                    return score
                if kind == _LOWER:
                    if score >= beta:
                        return score
                    alpha = max(alpha, score)
                elif score <= alpha:
                    return score
                else:
                    beta = min(beta, score)

        original_alpha = alpha
        best = -WIN_SCORE
        best_square = 0
        first = True

        for square, captured, index, replies in self._ordered_moves(
            me, opp, legal, best_first, scout=depth >= _SCOUT_FROM
        ):
            after_me = (me ^ captured) | square
            after_opp = opp ^ captured

            if first:
                value = -self._midgame(after_opp, after_me, depth - 1, -beta, -alpha, 0, replies)
                first = False
            else:
                # Assume the ordering was right and this move is worse.
                # A null window says so far more cheaply, and is only
                # wrong when the move turns out to beat alpha.
                value = -self._midgame(
                    after_opp, after_me, depth - 1, -alpha - 1, -alpha, 0, replies
                )
                if alpha < value < beta:
                    value = -self._midgame(
                        after_opp, after_me, depth - 1, -beta, -alpha, 0, replies
                    )

            if value > best:
                best = value
                best_square = square
                if value > alpha:
                    alpha = value
                    if alpha >= beta:
                        self._history[index] += depth * depth
                        break

        if len(self._table) < _MAX_TABLE:
            if best <= original_alpha:
                kind = _UPPER
            elif best >= beta:
                kind = _LOWER
            else:
                kind = _EXACT
            self._table[key] = (depth, best, kind, best_square)

        return best

    def _solve(  # noqa: C901, PLR0911, PLR0912, PLR0913, PLR0915, PLR0917
        self,
        me: int,
        opp: int,
        alpha: int,
        beta: int,
        passes: int,
        legal: int,
    ) -> int:
        """Play a position out to the end and return what it is worth.

        Parameters
        ----------
        me : int
            The stones of the player to move
        opp : int
            The stones of the opponent
        alpha : int
            The best margin the player to move is already assured of
        beta : int
            The best margin the opponent is already assured of
        passes : int
            How many players in a row have just had to pass
        legal : int
            The moves available here, or ``_UNSCOUTED`` when the caller
            did not order its moves and so never worked them out

        Returns
        -------
        int
            The final stone difference, in stones, with perfect play by
            both sides.

        Notes
        -----
        Margins here are counted in whole stones rather than on the
        evaluation's scale, because that is what the answer is: no
        judgement enters this function at any point.

        """
        self.nodes += 1
        if self.nodes >= self._checkpoint:
            self._tick()

        if legal == _UNSCOUTED:
            legal = moves(me, opp)

        if not legal:
            if passes:
                return popcount(me) - popcount(opp)
            return -self._solve(opp, me, -beta, -alpha, passes + 1, moves(opp, me))

        empties = 64 - popcount(me | opp)

        key = (me, opp)
        best_first = 0
        stored = self._table.get(key)
        if stored is not None:
            kept_depth, score, kind, best_first = stored
            # A stored solve is valid at any depth: it is not an
            # estimate that a deeper look could improve on.
            if kept_depth < 0:
                if kind == _EXACT:
                    return score
                if kind == _LOWER:
                    if score >= beta:
                        return score
                    alpha = max(alpha, score)
                elif score <= alpha:
                    return score
                else:
                    beta = min(beta, score)

        original_alpha = alpha
        best = -64

        if empties <= _ORDER_UNTIL:
            remaining = legal
            while remaining:
                square = remaining & -remaining
                remaining ^= square
                captured = flips(me, opp, square)
                # Deliberately left unscouted: generating the child's
                # moves here would do it for every move on the list,
                # including the ones a cutoff means never looking at.
                value = -self._solve(
                    opp ^ captured, (me ^ captured) | square, -beta, -alpha, 0, _UNSCOUTED
                )
                if value > best:
                    best = value
                    if value > alpha:
                        alpha = value
                        if alpha >= beta:
                            return best
            return best

        best_square = 0
        for square, captured, _index, replies in self._ordered_moves(
            me, opp, legal, best_first, scout=True
        ):
            value = -self._solve(
                opp ^ captured, (me ^ captured) | square, -beta, -alpha, 0, replies
            )
            if value > best:
                best = value
                best_square = square
                if value > alpha:
                    alpha = value
                    if alpha >= beta:
                        break

        if len(self._table) < _MAX_TABLE:
            if best <= original_alpha:
                kind = _UPPER
            elif best >= beta:
                kind = _LOWER
            else:
                kind = _EXACT
            self._table[key] = (-1, best, kind, best_square)

        return best

    def midgame_root(self, me: int, opp: int, depth: int) -> tuple[int, int]:
        """Search every move at the top of the tree to a fixed depth.

        Parameters
        ----------
        me : int
            The stones of the player to move
        opp : int
            The stones of the opponent
        depth : int
            How many moves to look ahead

        Returns
        -------
        tuple[int, int]
            The best square and its value.

        """
        legal = moves(me, opp)
        stored = self._table.get((me, opp))
        best_first = stored[3] if stored is not None else 0

        alpha = -WIN_SCORE
        best_square = 0
        first = True

        for square, captured, _index, replies in self._ordered_moves(
            me, opp, legal, best_first, scout=True
        ):
            after_me = (me ^ captured) | square
            after_opp = opp ^ captured

            if first:
                value = -self._midgame(
                    after_opp, after_me, depth - 1, -WIN_SCORE, -alpha, 0, replies
                )
                first = False
            else:
                value = -self._midgame(
                    after_opp, after_me, depth - 1, -alpha - 1, -alpha, 0, replies
                )
                if value > alpha:
                    value = -self._midgame(
                        after_opp, after_me, depth - 1, -WIN_SCORE, -alpha, 0, replies
                    )

            if value > alpha or best_square == 0:
                alpha = value
                best_square = square

        self._table[(me, opp)] = (depth, alpha, _EXACT, best_square)
        return best_square, alpha

    def solve_root(self, me: int, opp: int, alpha: int, beta: int) -> tuple[int, int]:
        """Play out every move at the top of the tree.

        Parameters
        ----------
        me : int
            The stones of the player to move
        opp : int
            The stones of the opponent
        alpha : int
            The lowest margin worth distinguishing
        beta : int
            The highest margin worth distinguishing

        Returns
        -------
        tuple[int, int]
            The best square and the final stone difference it leads to.

        Notes
        -----
        A narrow window makes the answer a bound rather than a margin,
        which is all that is needed to pick a move when the question is
        only whether the game is won.

        """
        legal = moves(me, opp)
        stored = self._table.get((me, opp))
        best_first = stored[3] if stored is not None else 0

        best_square = 0
        best = -64

        for square, captured, _index, replies in self._ordered_moves(
            me, opp, legal, best_first, scout=True
        ):
            window_low = max(alpha, best)
            value = -self._solve(
                opp ^ captured,
                (me ^ captured) | square,
                -beta,
                -window_low,
                0,
                replies,
            )
            if value > best or best_square == 0:
                best = value
                best_square = square
                # Nothing left to learn: no later move can beat what
                # the caller already refused to look past.
                if best >= beta:
                    break

        return best_square, best
