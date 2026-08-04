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
        """Initialize the game manager."""
        # The black player goes first
        self._current_player: int = Cell.FIRST_PLAYER.value
        self._placement: Placement = placement
        self._state: BoardState = state

    def _flip_stones_in_direction(
        self,
        start_row: int,
        start_col: int,
        row_direction: int,
        col_direction: int,
        current_player: int,
    ) -> None:
        """Flip the captured stones along one direction.

        Parameters
        ----------
        start_row : int
            The row of the newly placed stone
        start_col : int
            The column of the newly placed stone
        row_direction : int
            The row step to walk in (-1, 0, or 1)
        col_direction : int
            The column step to walk in (-1, 0, or 1)
        current_player : int
            The player who placed the stone

        """
        opponent_player: int = get_opponent_player(current_player)
        check_row: int = start_row + row_direction
        check_col: int = start_col + col_direction

        # Flip opponent stones until reaching current player's stone
        while self._state.is_within_board(check_row, check_col):
            cell_value: int = self._state.get_cell_value(check_row, check_col)
            if cell_value == opponent_player:
                self._state.set_cell_value(check_row, check_col, current_player)
                check_row += row_direction
                check_col += col_direction
            elif cell_value == current_player:
                # Reached current player's stone, stop flipping
                break
            else:
                # Empty cell: should not occur when
                # can_flip_in_direction returned True
                break

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

        if not self._placement.get_valid_placements(next_player):
            self._current_player = previous_player
            if not self._placement.get_valid_placements(previous_player):
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

        """
        if current_player is None:
            current_player = self._current_player

        if not self._placement.is_valid_placement(
            target_row=target_row,
            target_col=target_col,
            current_player=current_player,
        ):
            return False

        # Place the stone
        self._state.set_cell_value(
            row=target_row,
            col=target_col,
            value=current_player,
        )

        # Flip stones in all valid directions
        directions: list[tuple[int, int]] = [
            (-1, -1),
            (-1, 0),
            (-1, 1),
            (0, -1),
            (0, 1),
            (1, -1),
            (1, 0),
            (1, 1),
        ]

        for row_direction, col_direction in directions:
            if self._placement.can_flip_in_direction(
                target_row,
                target_col,
                row_direction,
                col_direction,
                current_player,
            ):
                self._flip_stones_in_direction(
                    target_row,
                    target_col,
                    row_direction,
                    col_direction,
                    current_player,
                )

        # Switch to next player
        self._switch_to_next_player(current_player)

        return True
