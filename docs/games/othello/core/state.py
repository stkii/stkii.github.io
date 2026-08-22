from enum import Enum

from docs.games.othello.bitboard import popcount, to_index

BOARD_SIZE: int = 8


class Cell(Enum):
    """The content of a single square on the board.

    Notes
    -----
    ``FIRST_PLAYER`` and ``SECONT_PLAYER`` double as player identifiers
    throughout the core. ``EMPTY_CELL`` is only ever a board content,
    never a player.

    """

    EMPTY_CELL = 0
    FIRST_PLAYER = 1
    SECONT_PLAYER = 2


class BoardState:
    """Represents the state of an Othello board.

    Attributes
    ----------
    _black : int
        A bitboard of the first player's stones
    _white : int
        A bitboard of the second player's stones
    _size : int
        The width and height of the square board

    Notes
    -----
    The board is held as two bitboards rather than as a grid of cells,
    because the search plays and retracts millions of moves per turn
    and a bitboard turns a move into a handful of integer operations.

    """

    def __init__(self) -> None:
        self._size: int = BOARD_SIZE
        self._black: int
        self._white: int
        self._black, self._white = self._initialize_board()

    def _initialize_board(self) -> tuple[int, int]:
        """Build the standard starting position.

        Returns
        -------
        tuple[int, int]
            The black and white bitboards, with the four centre stones
            set diagonally.

        """
        center: int = self._size // 2

        black: int = (1 << to_index(center - 1, center)) | (1 << to_index(center, center - 1))
        white: int = (1 << to_index(center - 1, center - 1)) | (1 << to_index(center, center))

        return black, white

    @property
    def board(self) -> list[list[int]]:
        """Get a copy of the board state.

        Returns
        -------
        list[list[int]]
            The rows of the board, each cell holding a :class:`Cell`
            value.

        Notes
        -----
        The grid is rebuilt from the bitboards on every call, so the
        internal state cannot be reached through it.

        """
        black: int = self._black
        white: int = self._white
        black_value: int = Cell.FIRST_PLAYER.value
        white_value: int = Cell.SECONT_PLAYER.value
        empty_value: int = Cell.EMPTY_CELL.value

        grid: list[list[int]] = []
        for row in range(self._size):
            cells: list[int] = []
            for col in range(self._size):
                bit: int = 1 << (row * self._size + col)
                if black & bit:
                    cells.append(black_value)
                elif white & bit:
                    cells.append(white_value)
                else:
                    cells.append(empty_value)
            grid.append(cells)
        return grid

    @property
    def size(self) -> int:
        """Get the board size."""
        return self._size

    def bitboards(self) -> tuple[int, int]:
        """Get the raw bitboards.

        Returns
        -------
        tuple[int, int]
            The stones as (black, white).

        """
        return self._black, self._white

    def bitboards_for(self, player: int) -> tuple[int, int]:
        """Get the bitboards oriented for one player.

        Parameters
        ----------
        player : int
            The player to put first

        Returns
        -------
        tuple[int, int]
            The stones as (player, opponent).

        """
        if player == Cell.FIRST_PLAYER.value:
            return self._black, self._white
        return self._white, self._black

    def set_bitboards(self, black: int, white: int) -> None:
        """Replace the board contents wholesale.

        Parameters
        ----------
        black : int
            A bitboard of the first player's stones
        white : int
            A bitboard of the second player's stones

        """
        self._black = black
        self._white = white

    def apply_move(self, player: int, square: int, captured: int) -> None:
        """Add a stone and turn over what it captured.

        Parameters
        ----------
        player : int
            The player who placed the stone
        square : int
            A bitboard holding the square played on
        captured : int
            A bitboard of the opponent stones being turned over

        """
        if player == Cell.FIRST_PLAYER.value:
            self._black = self._black | captured | square
            self._white ^= captured
        else:
            self._white = self._white | captured | square
            self._black ^= captured

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
        if player == Cell.FIRST_PLAYER.value:
            return popcount(self._black)
        if player == Cell.SECONT_PLAYER.value:
            return popcount(self._white)
        return self._size * self._size - popcount(self._black | self._white)

    def count_empty(self) -> int:
        """Count the squares still free.

        Returns
        -------
        int
            The number of empty squares.

        """
        return self._size * self._size - popcount(self._black | self._white)

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
        bit: int = 1 << (row * self._size + col)
        if self._black & bit:
            return Cell.FIRST_PLAYER.value
        if self._white & bit:
            return Cell.SECONT_PLAYER.value
        return Cell.EMPTY_CELL.value

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
        bit: int = 1 << (row * self._size + col)
        if value == Cell.FIRST_PLAYER.value:
            self._black |= bit
            self._white &= ~bit
        elif value == Cell.SECONT_PLAYER.value:
            self._white |= bit
            self._black &= ~bit
        else:
            self._black &= ~bit
            self._white &= ~bit
