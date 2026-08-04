from docs.games.othello.core.state import BoardState, Cell


class ScoreCalculator:
    """Handles score calculation and winner determination.

    Attributes
    ----------
    _state : BoardState
        The board whose stones are counted

    """

    def __init__(self, state: BoardState) -> None:
        """Initialize the score calculator."""
        self._state: BoardState = state

    def get_score(self) -> tuple[int, int]:
        """Get the current score of each player.

        Returns
        -------
        tuple[int, int]
            The stone counts as (black, white).

        """
        black_stones_count: int = self._state.count_stones(Cell.FIRST_PLAYER.value)
        white_stones_count: int = self._state.count_stones(Cell.SECONT_PLAYER.value)
        return (black_stones_count, white_stones_count)

    def get_winner(self) -> int:
        """Get the winner of the game.

        Returns
        -------
        int
            The player holding more stones, or ``EMPTY_CELL`` for a tie.

        """
        black_stones_count, white_stones_count = self.get_score()

        if black_stones_count > white_stones_count:
            return Cell.FIRST_PLAYER.value
        # Using `elif` here improves clarity by making mutual
        # exclusivity explicit.
        elif white_stones_count > black_stones_count:  # noqa: RET505
            return Cell.SECONT_PLAYER.value
        else:
            return Cell.EMPTY_CELL.value  # Tie game
