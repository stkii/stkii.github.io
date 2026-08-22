"""The facade the rest of the program plays against.

Picks which stage of :mod:`search` a position calls for and hands it a
deadline; the reasoning behind the stages lives there, not here.

"""

import time
from typing import NamedTuple

from docs.games.othello.bitboard import moves, popcount
from docs.games.othello.core.board import Board
from docs.games.othello.strategy.search import STONE, Search, SearchTimeout

# The budget the two boundaries below were measured against. They do
# not survive a change to it, or to the machine: a solve costs about
# three times more per extra empty square, so twice the clock buys well
# under one square.
DEFAULT_TIME_LIMIT: float = 0.25

# Once this few squares remain the exact final margin is refined on top
# of the result. Missing it is free -- the solved move is already in
# hand and a timeout just returns it without the margin -- so what sets
# the boundary is how long the think takes, not what is at stake.
DEFAULT_EXACT_EMPTIES: int = 11

# Once this few squares remain the game is played out rather than
# judged, for the result alone. Missing it costs the ply or two that
# the fallback move is shallower by, which is the cheaper half of the
# trade against reading the rest of the game out exactly, so the
# boundary sits where most positions finish rather than where nearly
# all of them do.
DEFAULT_WLD_EMPTIES: int = 14

# Share of the budget spent finding a move to fall back on before a
# solve is attempted. The rest is left for the solve itself.
_FALLBACK_SHARE: float = 0.25

# An iteration costs several times the one before it, so one started
# with less than this share of the budget left will not finish.
_NEXT_ITERATION_SHARE: float = 0.4


class Decision(NamedTuple):
    """What the engine worked out, and what it cost.

    Attributes
    ----------
    move : tuple[int, int] | None
        The square to play, or None when the player has to pass
    score : int
        The value of the position, in hundredths of a stone
    depth : int
        How many moves ahead the search looked, or the number of empty
        squares when the game was played out to the end
    solved : bool
        Whether the score is the true result rather than a judgement
    exact : bool
        Whether a solved score is the final margin rather than only
        the knowledge of who wins
    nodes : int
        How many positions were visited
    seconds : float
        How long the think took

    """

    move: tuple[int, int] | None
    score: int
    depth: int
    solved: bool
    exact: bool
    nodes: int
    seconds: float


class Engine:
    """Picks moves for the computer player.

    Attributes
    ----------
    time_limit : float
        How many seconds a single move may take
    exact_empties : int
        The number of empty squares at which to start playing the
        game out for the exact final margin
    wld_empties : int
        The number of empty squares at which to start playing the
        game out for the result alone

    Notes
    -----
    The engine never changes the board it is given, so the caller stays
    in charge of when and whether the move is actually played.

    """

    def __init__(
        self,
        time_limit: float = DEFAULT_TIME_LIMIT,
        exact_empties: int = DEFAULT_EXACT_EMPTIES,
        wld_empties: int = DEFAULT_WLD_EMPTIES,
    ) -> None:
        self.time_limit: float = time_limit
        self.exact_empties: int = exact_empties
        self.wld_empties: int = wld_empties

    def choose_move(self, board: Board) -> tuple[int, int] | None:
        """Pick the move to play on the given board.

        Parameters
        ----------
        board : Board
            The position to move in

        Returns
        -------
        tuple[int, int] | None
            The (row, col) to play, or None when there is no legal move.

        """
        return self.think(board).move

    def think(self, board: Board) -> Decision:
        """Pick a move and report how the answer was reached.

        Parameters
        ----------
        board : Board
            The position to move in

        Returns
        -------
        Decision
            The chosen move together with the reasoning behind it.

        """
        started = time.perf_counter()
        black, white = board.bitboards()
        player = board.current_player

        me, opp = (black, white) if player == Board.BLACK else (white, black)
        legal = moves(me, opp)
        if not legal:
            return Decision(
                move=None, score=0, depth=0, solved=False, exact=False, nodes=0, seconds=0.0
            )

        empties = 64 - popcount(me | opp)

        # With one move there is nothing to choose between.
        if legal & (legal - 1) == 0:
            return Decision(
                move=self._to_cell(legal),
                score=0,
                depth=0,
                solved=False,
                exact=False,
                nodes=0,
                seconds=0.0,
            )

        search = Search(self.time_limit)
        if empties <= self.wld_empties:
            square, score, solved, exact, depth = self._play_out(search, me, opp, empties)
        else:
            square, score, depth = self._look_ahead(search, me, opp, empties, self.time_limit)
            solved = exact = False

        return Decision(
            move=self._to_cell(square),
            score=score,
            depth=depth,
            solved=solved,
            exact=exact,
            nodes=search.nodes,
            seconds=time.perf_counter() - started,
        )

    def _look_ahead(
        self,
        search: Search,
        me: int,
        opp: int,
        empties: int,
        budget: float,
    ) -> tuple[int, int, int]:
        """Deepen the search until the time runs out.

        Parameters
        ----------
        search : Search
            The search to run, carrying the clock and the table
        me : int
            The stones of the player to move
        opp : int
            The stones of the opponent
        empties : int
            The number of empty squares left
        budget : float
            The seconds this stage may take

        Returns
        -------
        tuple[int, int, int]
            The best square, its value, and the depth it survived to.

        Notes
        -----
        Every iteration leaves its best move in the transposition
        table, and the next one tries that move first, so redoing the
        shallow work costs much less than it saves. The search can then
        be stopped at any moment with a usable answer in hand rather
        than half of a deeper one.

        """
        started = time.perf_counter()
        search.deadline = started + budget

        best_square = 0
        best_score = 0
        reached = 0

        for depth in range(1, empties + 1):
            try:
                square, score = search.midgame_root(me, opp, depth)
            except SearchTimeout:
                break
            best_square, best_score, reached = square, score, depth

            # Starting an iteration that cannot finish only burns the
            # budget that the next stage was going to need.
            if time.perf_counter() - started >= budget * _NEXT_ITERATION_SHARE:
                break

        return best_square, best_score, reached

    def _play_out(
        self,
        search: Search,
        me: int,
        opp: int,
        empties: int,
    ) -> tuple[int, int, bool, bool, int]:
        """Settle the game by playing it out rather than judging it.

        Parameters
        ----------
        search : Search
            The search to run, carrying the clock and the table
        me : int
            The stones of the player to move
        opp : int
            The stones of the opponent
        empties : int
            The number of empty squares left

        Returns
        -------
        tuple[int, int, bool, bool, int]
            The best square, its value, whether the game was solved,
            whether the margin is exact, and the depth reached.

        Notes
        -----
        Three stages, each of which leaves behind an answer the next
        one is free to fail without losing.

        A shallow judged search goes first, purely so that a move is
        always in hand: a solve that runs out of time answers nothing
        at all. Then the result alone, through a window one stone wide,
        which is around a twentieth of the work of asking for the
        margin as well and is the question that decides the game. Only
        then, and only when the position is small enough to afford it,
        is the margin refined on top of the bounds the narrow search
        left in the table.

        """
        started = time.perf_counter()
        best_square, best_score, depth = self._look_ahead(
            search, me, opp, empties, self.time_limit * _FALLBACK_SHARE
        )
        solved = False

        # Whatever the fallback did not use belongs to the solve.
        search.deadline = started + self.time_limit

        try:
            best_square, outcome = search.solve_root(me, opp, -1, 1)
        except SearchTimeout:
            return best_square, best_score, solved, False, depth

        best_score = outcome * STONE
        solved = True
        depth = empties

        if empties > self.exact_empties:
            return best_square, best_score, solved, False, depth

        try:
            square, margin = search.solve_root(me, opp, -64, 64)
        except SearchTimeout:
            return best_square, best_score, solved, False, depth

        return square, margin * STONE, True, True, depth

    @staticmethod
    def _to_cell(square: int) -> tuple[int, int] | None:
        """Turn a one-square bitboard into a row and column.

        Parameters
        ----------
        square : int
            A bitboard holding a single square, or 0 for no move

        Returns
        -------
        tuple[int, int] | None
            The (row, col) of the square, or None when there is none.

        """
        if not square:
            return None
        return divmod(square.bit_length() - 1, Board.SIZE)
