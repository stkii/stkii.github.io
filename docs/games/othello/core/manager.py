from docs.games.othello.core.placement import Placement
from docs.games.othello.core.state import BoardState, Cell
from docs.games.othello.core.utils import get_opponent_player


class GameManager:
    """Handles game execution and flow control.

    Attributes
    ----------
    _current_player : int
        The player to move, or ``EMPTY_CELL`` once the game has ended
    _placement : Placement
        The move validator
    _state : BoardState
        The board being played on

    """

    def __init__(
        self,
        placement: Placement,
        state: BoardState,
    ) -> None:
        self._current_player: int = Cell.FIRST_PLAYER.value
        self._placement: Placement = placement
        self._state: BoardState = state

    def _switch_to_next_player(self, previous_player: int) -> None:
        """Hand the turn on, passing or ending the game as needed.

        Parameters
        ----------
        previous_player : int
            The player who just completed their turn

        Notes
        -----
        The turn comes straight back when the opponent has no move,
        and the game ends when neither player has one.

        """
        next_player: int = get_opponent_player(previous_player)
        self._current_player = next_player

        if not self._placement.has_valid_placement(next_player):
            self._current_player = previous_player
            if not self._placement.has_valid_placement(previous_player):
                self._current_player = Cell.EMPTY_CELL.value

    @property
    def current_player(self) -> int:
        """Get the current player."""
        return self._current_player

    def is_game_ended(self) -> bool:
        """Check if the game has ended.

        Returns
        -------
        bool
            True once neither player can move.

        """
        return self._current_player == Cell.EMPTY_CELL.value

    def set_current_player(self, player: int) -> None:
        """Set the current player.

        Parameters
        ----------
        player : int
            The player to move, or ``EMPTY_CELL`` to end the game

        """
        self._current_player = player

    def place_and_flip(
        self,
        target_row: int,
        target_col: int,
        current_player: int | None = None,
    ) -> bool:
        """Place a stone, flip what it captures and hand the turn on.

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
        Validating the move already works out which stones it captures,
        so the placement and the flips are applied together rather than
        walking the eight directions a second time.

        """
        if current_player is None:
            current_player = self._current_player

        captured: int = self._placement.get_captures(
            target_row=target_row,
            target_col=target_col,
            current_player=current_player,
        )
        if not captured:
            return False

        square: int = 1 << (target_row * self._state.size + target_col)
        self._state.apply_move(current_player, square, captured)
        self._switch_to_next_player(current_player)

        return True
