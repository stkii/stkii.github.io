from typing import Any

from docs.games.othello.core.manager import GameManager
from docs.games.othello.core.placement import Placement
from docs.games.othello.core.score import ScoreCalculator
from docs.games.othello.core.state import BOARD_SIZE, BoardState, Cell
from docs.games.othello.core.utils import get_opponent_player


class Board:
    """Facade for the Othello game service.

    Attributes
    ----------
    EMPTY : int
        The value stored in an empty cell
    BLACK : int
        The identifier of the first player, who moves first
    WHITE : int
        The identifier of the second player
    SIZE : int
        The width and height of the square board
    _state : BoardState
        The board contents
    _placement : Placement
        The move validator
    _score_calculator : ScoreCalculator
        The stone counter
    _game_manager : GameManager
        The turn order and move execution

    Notes
    -----
    The cell values and the board size are published as class
    attributes so that callers can read a board, name a player and
    size a grid without importing anything from behind the facade.

    """

    EMPTY: int = Cell.EMPTY_CELL.value
    BLACK: int = Cell.FIRST_PLAYER.value
    WHITE: int = Cell.SECONT_PLAYER.value
    SIZE: int = BOARD_SIZE

    def __init__(self) -> None:
        """Initialize the board at the standard starting position."""
        self._state: BoardState = BoardState()
        self._placement: Placement = Placement(self._state)
        self._score_calculator: ScoreCalculator = ScoreCalculator(self._state)
        self._game_manager: GameManager = GameManager(self._placement, self._state)

    @classmethod
    def create_copy(cls, original: "Board") -> "Board":
        """Create an independent copy of the board, for simulation.

        Parameters
        ----------
        original : Board
            The board to copy

        Returns
        -------
        Board
            A board in the same state, sharing nothing with `original`.

        Notes
        -----
        Kept on the facade so that a caller can branch a game without
        reaching for the internals.

        """
        # Create new instance with default initialization
        copy_board: Board = cls()

        # Copy board state using public interface
        original_board_data: list[list[int]] = original.board
        for row in range(copy_board.size):
            for col in range(copy_board.size):
                copy_board._state.set_cell_value(row, col, original_board_data[row][col])

        # Copy the current player state directly
        copy_board._game_manager.set_current_player(original.current_player)

        return copy_board

    @staticmethod
    def opponent_of(player: int) -> int:
        """Get the player opposing the given one.

        Parameters
        ----------
        player : int
            The player to find the opponent of

        Returns
        -------
        int
            The opposing player identifier.

        """
        return get_opponent_player(player)

    @property
    def board(self) -> list[list[int]]:
        """Get a copy of the board state to prevent direct modification."""
        return self._state.board

    @property
    def size(self) -> int:
        """Get the board size."""
        return self._state.size

    @property
    def current_player(self) -> int:
        """Get the current player."""
        return self._game_manager.current_player

    @current_player.setter
    def current_player(self, player: int) -> None:
        """Set the current player."""
        self._game_manager.set_current_player(player)

    def create_snapshot(self) -> dict[str, Any]:
        """Create a snapshot of the current board state for restoration.

        Returns
        -------
        dict[str, Any]
            The board contents and the player to move.

        """
        return {
            "board": self.board,
            "current_player": self.current_player,
        }

    def is_game_ended(self) -> bool:
        """Check if the game has ended.

        Returns
        -------
        bool
            True once neither player can move.

        """
        return self._game_manager.is_game_ended()

    def is_valid_move(
        self,
        target_row: int,
        target_col: int,
        current_player: int | None = None,
    ) -> bool:
        """Check if a stone may be placed at the specified position.

        Parameters
        ----------
        target_row : int
            The row the stone would go on (0-based)
        target_col : int
            The column the stone would go on (0-based)
        current_player : int, optional
            The player making the move, defaulting to the one to move

        Returns
        -------
        bool
            True when the move captures at least one opponent stone.

        """
        if self._game_manager.is_game_ended():
            return False

        if current_player is None:
            current_player = self._game_manager.current_player

        return self._placement.is_valid_placement(target_row, target_col, current_player)

    def get_score(self) -> tuple[int, int]:
        """Get the current score.

        Returns
        -------
        tuple[int, int]
            The stone counts as (black, white).

        """
        return self._score_calculator.get_score()

    def get_valid_moves(self, player: int | None = None) -> list[tuple[int, int]]:
        """Get all valid moves for the specified player.

        Parameters
        ----------
        player : int, optional
            The player to find moves for, defaulting to the one to move

        Returns
        -------
        list[tuple[int, int]]
            Every (row, col) that player may play.

        """
        if player is None:
            player = self._game_manager.current_player
        return self._placement.get_valid_placements(player)

    def get_winner(self) -> int:
        """Get the winner of the game, once it has ended.

        Returns
        -------
        int
            The player holding more stones, or ``EMPTY`` for a tie.

        """
        return self._score_calculator.get_winner()

    def make_move(
        self,
        target_row: int,
        target_col: int,
        current_player: int | None = None,
    ) -> bool:
        """Place a stone at the specified position and flip captured stones.

        Parameters
        ----------
        target_row : int
            The row to place the stone on (0-based)
        target_col : int
            The column to place the stone on (0-based)
        current_player : int, optional
            The player making the move, defaulting to the one to move

        Returns
        -------
        bool
            True when the move was played, False when it was invalid.

        Notes
        -----
        The turn is advanced here too: a player with no move is passed
        automatically, and the game ends when neither side can move.
        Neither is reported back to the caller.

        """
        if self._game_manager.is_game_ended():
            return False

        return self._game_manager.place_and_flip(target_row, target_col, current_player)

    def restore_from_snapshot(self, snapshot: dict[str, Any]) -> None:
        """Restore the board state from a snapshot.

        Parameters
        ----------
        snapshot : dict[str, Any]
            The snapshot to restore from

        """
        board_data: list[list[int]] = snapshot["board"]
        for row in range(self.size):
            for col in range(self.size):
                self._state.set_cell_value(row, col, board_data[row][col])
        self._game_manager.set_current_player(snapshot["current_player"])
