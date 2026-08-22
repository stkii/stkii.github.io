"""Bridge between the game core and the user interface.

The core resolves passes and game end silently inside
:meth:`Board.make_move`. :class:`GameSession` recovers what the
interface needs out of that — the stones that flipped, and whether the
opponent had to pass — so the core carries nothing about display.
"""

from dataclasses import dataclass
from enum import Enum, auto

from docs.games.othello.core.board import Board
from docs.games.othello.strategy import Engine

# The human moves first, so the computer takes white.
CPU_PLAYER: int = Board.WHITE

# How long the computer may think about one move. The interface blocks
# while it does, so this is also the longest the window can stop
# responding, and it is picked to stay under a fifth of a second rather
# than to make the engine as strong as it could be.
CPU_TIME_LIMIT: float = 0.25


class TurnEvent(Enum):
    """What the turn order did in response to a move.

    Attributes
    ----------
    MOVED
        The turn passed to the opponent as usual
    PASSED
        The opponent had no valid move, so the turn came straight back
    ENDED
        Neither player can move and the game is over

    """

    MOVED = auto()
    PASSED = auto()
    ENDED = auto()


@dataclass(frozen=True)
class MoveResult:
    """The outcome of a single move.

    Attributes
    ----------
    player : int
        The player who made the move
    opponent : int
        The player who did not, whose stones were captured
    placed : tuple[int, int]
        The (row, col) where the stone was placed
    flipped : tuple[tuple[int, int], ...]
        Every (row, col) that changed owner, excluding ``placed``
    event : TurnEvent
        What happened to the turn order afterwards

    Notes
    -----
    `opponent` is carried along so the interface can name the passing
    player and color the captured stones without deriving it.

    """

    player: int
    opponent: int
    placed: tuple[int, int]
    flipped: tuple[tuple[int, int], ...]
    event: TurnEvent


class GameSession:
    """Holds one game of Othello and the history of its moves.

    Attributes
    ----------
    _board : Board
        The underlying rules engine
    _history : list[MoveResult]
        Every move played so far, in order
    _engine : Engine | None
        The computer player, or None when both sides are human

    Notes
    -----
    The computer lives here rather than in the interface so that a
    computer move and a human move look the same from up there: a call
    that comes back with a :class:`MoveResult`.

    """

    def __init__(self, *, versus_cpu: bool = True) -> None:
        """Start a new game.

        Parameters
        ----------
        versus_cpu : bool, optional
            Whether the second player is the computer

        """
        self._board: Board = Board()
        self._history: list[MoveResult] = []
        self._engine: Engine | None = Engine(time_limit=CPU_TIME_LIMIT) if versus_cpu else None

    def _classify_turn(self, mover: int) -> TurnEvent:
        """Determine what the turn order did after a move.

        Parameters
        ----------
        mover : int
            The player who just moved

        Returns
        -------
        TurnEvent
            The event describing the new turn state.

        Notes
        -----
        The core hands the turn back to the mover on a pass, and sets
        the current player to ``EMPTY`` at game end, so comparing it
        against the mover recovers both cases.

        """
        following_player: int = self._board.current_player

        if following_player == Board.EMPTY:
            return TurnEvent.ENDED
        if following_player == mover:
            return TurnEvent.PASSED
        return TurnEvent.MOVED

    def _diff_flipped(
        self,
        before: list[list[int]],
        placed: tuple[int, int],
    ) -> tuple[tuple[int, int], ...]:
        """Find the stones that changed owner during a move.

        Parameters
        ----------
        before : list[list[int]]
            The board contents from before the move
        placed : tuple[int, int]
            The (row, col) of the new stone, excluded from the result

        Returns
        -------
        tuple[tuple[int, int], ...]
            Every (row, col) whose contents differ from `before`.

        Notes
        -----
        Diffing the board keeps the flip bookkeeping out of the core.

        """
        after: list[list[int]] = self._board.board
        return tuple(
            (row, col)
            for row in range(self._board.size)
            for col in range(self._board.size)
            if before[row][col] != after[row][col] and (row, col) != placed
        )

    @property
    def board(self) -> list[list[int]]:
        """Get a copy of the current board contents."""
        return self._board.board

    @property
    def current_player(self) -> int:
        """Get the player to move, or 0 once the game has ended."""
        return self._board.current_player

    @property
    def is_cpu_turn(self) -> bool:
        """Check whether the computer is the one to move.

        Returns
        -------
        bool
            True when a computer player exists and the turn is theirs.

        """
        return self._engine is not None and self._board.current_player == CPU_PLAYER

    @property
    def is_draw(self) -> bool:
        """Check whether the game finished level on stones."""
        return self._board.get_winner() == Board.EMPTY

    @property
    def is_ended(self) -> bool:
        """Check whether the game has ended."""
        return self._board.is_game_ended()

    @property
    def last_move(self) -> MoveResult | None:
        """Get the most recent move, or None before the first move."""
        if not self._history:
            return None
        return self._history[-1]

    @property
    def score(self) -> tuple[int, int]:
        """Get the current score as (black_count, white_count)."""
        return self._board.get_score()

    @property
    def size(self) -> int:
        """Get the board size."""
        return self._board.size

    @property
    def valid_moves(self) -> list[tuple[int, int]]:
        """Get every legal move for the player to move."""
        if self._board.is_game_ended():
            return []
        return self._board.get_valid_moves()

    @property
    def winner(self) -> int:
        """Get the winner, or 0 for a tie."""
        return self._board.get_winner()

    def play(self, row: int, col: int) -> MoveResult | None:
        """Play a move and report what it changed.

        Parameters
        ----------
        row : int
            The row to place a stone on (0-based)
        col : int
            The column to place a stone on (0-based)

        Returns
        -------
        MoveResult | None
            The outcome of the move, or None when the move was
            rejected as invalid.

        """
        mover: int = self._board.current_player
        before: list[list[int]] = self._board.board

        if not self._board.make_move(row, col):
            return None

        placed: tuple[int, int] = (row, col)
        result: MoveResult = MoveResult(
            player=mover,
            opponent=Board.opponent_of(mover),
            placed=placed,
            flipped=self._diff_flipped(before, placed),
            event=self._classify_turn(mover),
        )
        self._history.append(result)

        return result

    def play_cpu(self) -> MoveResult | None:
        """Let the computer take its turn.

        Returns
        -------
        MoveResult | None
            The outcome of the move, or None when it is not the
            computer's turn to move.

        Notes
        -----
        This blocks for as long as the engine is allowed to think.

        """
        if not self.is_cpu_turn or self._engine is None:
            return None

        move: tuple[int, int] | None = self._engine.choose_move(self._board)
        if move is None:
            return None

        return self.play(*move)

    def reset(self) -> None:
        """Discard the current game and start over."""
        self._board = Board()
        self._history.clear()
