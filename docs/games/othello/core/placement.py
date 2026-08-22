from docs.games.othello.bitboard import flips, iter_squares, moves
from docs.games.othello.core.state import BoardState


class Placement:
    """Handles validation logic for Othello piece placements.

    Attributes
    ----------
    _state : BoardState
        The board the placements are checked against

    Notes
    -----
    The eight directions a move can capture along are walked in
    parallel by :mod:`docs.games.othello.bitboard`, so a whole board's
    worth of legal moves comes back from one call.

    """

    def __init__(self, state: BoardState) -> None:
        self._state: BoardState = state

    def get_valid_placements(self, player: int) -> list[tuple[int, int]]:
        """Get all valid placements for the specified player.

        Parameters
        ----------
        player : int
            The player to find placements for

        Returns
        -------
        list[tuple[int, int]]
            Every (row, col) the player may play, empty when none can,
            ordered left to right and top to bottom.

        """
        me, opp = self._state.bitboards_for(player)
        size: int = self._state.size
        return [divmod(square.bit_length() - 1, size) for square in iter_squares(moves(me, opp))]

    def get_placement_mask(self, player: int) -> int:
        """Get all valid placements as a bitboard.

        Parameters
        ----------
        player : int
            The player to find placements for

        Returns
        -------
        int
            A bitboard of the legal moves.

        """
        me, opp = self._state.bitboards_for(player)
        return moves(me, opp)

    def has_valid_placement(self, player: int) -> bool:
        """Check whether a player has any move at all.

        Parameters
        ----------
        player : int
            The player to check

        Returns
        -------
        bool
            True when the player has at least one legal move.

        Notes
        -----
        Cheaper than testing :meth:`get_valid_placements` for
        emptiness, since no list is built.

        """
        me, opp = self._state.bitboards_for(player)
        return moves(me, opp) != 0

    def get_captures(self, target_row: int, target_col: int, current_player: int) -> int:
        """Get the stones a placement would capture.

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
        int
            A bitboard of the opponent stones the placement turns over,
            empty when the placement is illegal.

        """
        if not self._state.is_within_board(target_row, target_col):
            return 0

        me, opp = self._state.bitboards_for(current_player)
        square: int = 1 << (target_row * self._state.size + target_col)

        # Without this the walk would happily bracket a line from an
        # occupied square.
        if (me | opp) & square:
            return 0

        return flips(me, opp, square)

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
        return self.get_captures(target_row, target_col, current_player) != 0
