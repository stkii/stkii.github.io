from enum import Enum

# Constants
BOARD_SIZE: int = 8


class Cell(Enum):
    """The content of a single square on the board.

    Notes
    -----
    ``FIRST_PLAYER`` and ``SECONT_PLAYER`` double as player identifiers
    throughout the core.
    ``EMPTY_CELL`` is only ever a board content, never a player.

    """

    EMPTY_CELL = 0
    FIRST_PLAYER = 1
    SECONT_PLAYER = 2


class BoardState:
    """Represents the state of an Othello board.

    Attributes
    ----------
    _board : list[list[int]]
        The rows of the board, each cell holding a :class:`Cell` value
    _size : int
        The width and height of the square board

    """

    def __init__(self) -> None:
        """Initialize the board state with the standard starting position."""
        self._size: int = BOARD_SIZE
        self._board: list[list[int]] = self._initialize_board()

    def _initialize_board(self) -> list[list[int]]:
        """Build the standard starting position.

        Returns
        -------
        list[list[int]]
            A board with the four center stones set diagonally.

        """
        board: list[list[int]] = [
            [Cell.EMPTY_CELL.value for _ in range(self._size)] for _ in range(self._size)
        ]

        # Initial stone placement
        center: int = self._size // 2
        board[center - 1][center - 1] = Cell.SECONT_PLAYER.value
        board[center - 1][center] = Cell.FIRST_PLAYER.value
        board[center][center - 1] = Cell.FIRST_PLAYER.value
        board[center][center] = Cell.SECONT_PLAYER.value

        return board

    @property
    def board(self) -> list[list[int]]:
        """Get a copy of the board state."""
        # Defensive copy: row lists are cloned, and ints are immutable,
        # so this is effectively a deep copy and sufficient to protect
        # the internal state.
        return [row[:] for row in self._board]

    @property
    def size(self) -> int:
        """Get the board size."""
        return self._size

    def count_stones(self, player: int) -> int:
        """Count the stones a player has on the board.

        Parameters
        ----------
        player : int
            The player to count stones for

        Returns
        -------
        int
            The number of stones that player holds.

        """
        return sum(row.count(player) for row in self._board)

    def get_cell_value(self, row: int, col: int) -> int:
        """Get the content of a single cell.

        Parameters
        ----------
        row : int
            The row index (0-based)
        col : int
            The column index (0-based)

        Returns
        -------
        int
            The :class:`Cell` value the position holds.

        Notes
        -----
        The position is not bounds checked. Use `is_within_board`.

        """
        return self._board[row][col]

    def is_within_board(self, row: int, col: int) -> bool:
        """Check whether a position falls inside the board.

        Parameters
        ----------
        row : int
            The row index (0-based)
        col : int
            The column index (0-based)

        Returns
        -------
        bool
            True when the position is on the board.

        """
        return 0 <= row < self._size and 0 <= col < self._size

    def set_cell_value(self, row: int, col: int, value: int) -> None:
        """Write the content of a single cell.

        Parameters
        ----------
        row : int
            The row index (0-based)
        col : int
            The column index (0-based)
        value : int
            The :class:`Cell` value to store

        Notes
        -----
        The position is not bounds checked. Use `is_within_board`.

        """
        self._board[row][col] = value
