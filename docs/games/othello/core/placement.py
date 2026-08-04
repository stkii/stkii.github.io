from docs.games.othello.core.state import BoardState, Cell
from docs.games.othello.core.utils import get_opponent_player


class Placement:
    """Handles validation logic for Othello piece placements.

    Attributes
    ----------
    _state : BoardState
        The board the placements are checked against

    """

    def __init__(self, state: BoardState) -> None:
        """Initialize the placement validator."""
        self._state: BoardState = state

    def can_flip_in_direction(
        self,
        start_row: int,
        start_col: int,
        row_direction: int,
        col_direction: int,
        current_player: int,
    ) -> bool:
        """Check whether a placement captures along one direction.

        Parameters
        ----------
        start_row : int
            The row of the potential placement
        start_col : int
            The column of the potential placement
        row_direction : int
            The row step to walk in (-1, 0, or 1)
        col_direction : int
            The column step to walk in (-1, 0, or 1)
        current_player : int
            The player making the placement

        Returns
        -------
        bool
            True when stones can be flipped in this direction.

        Notes
        -----
        The line leaving the placement has to read one or more opponent
        stones followed by one of the player's own.

        """
        opponent_player: int = get_opponent_player(current_player)
        check_row: int = start_row + row_direction
        check_col: int = start_col + col_direction

        # Check if the adjacent cell contains an opponent stone
        if not self._state.is_within_board(check_row, check_col):
            return False
        if self._state.get_cell_value(check_row, check_col) != opponent_player:
            return False

        # Look for a current player stone that would close the line
        check_row += row_direction
        check_col += col_direction

        while self._state.is_within_board(check_row, check_col):
            cell_value: int = self._state.get_cell_value(check_row, check_col)
            if cell_value == Cell.EMPTY_CELL.value:
                return False
            if cell_value == current_player:  # Found closing stone
                return True
            # Continue through opponent stones
            check_row += row_direction
            check_col += col_direction

        return False

    def get_valid_placements(self, player: int) -> list[tuple[int, int]]:
        """Get all valid placements for the specified player.

        Parameters
        ----------
        player : int
            The player to find placements for

        Returns
        -------
        list[tuple[int, int]]
            Every (row, col) the player may play, empty when none can.

        """
        return [
            (i, j)
            for i in range(self._state.size)
            for j in range(self._state.size)
            if self.is_valid_placement(
                target_row=i,
                target_col=j,
                current_player=player,
            )
        ]

    def is_valid_placement(
        self,
        target_row: int,
        target_col: int,
        current_player: int,
    ) -> bool:
        """Check whether a placement is legal.

        Parameters
        ----------
        target_row : int
            The row the stone would go on (0-based)
        target_col : int
            The column the stone would go on (0-based)
        current_player : int
            The player making the placement

        Returns
        -------
        bool
            True when the target is an empty cell on the board that
            captures in at least one of the eight directions.

        """
        if not self._state.is_within_board(target_row, target_col):
            return False

        # Placement is invalid if target cell is not empty
        if self._state.get_cell_value(target_row, target_col) != Cell.EMPTY_CELL.value:
            return False

        # Check all 8 directions
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
            if self.can_flip_in_direction(
                target_row,
                target_col,
                row_direction,
                col_direction,
                current_player,
            ):
                return True

        return False
