"""Screen geometry for the Othello user interface.

Every coordinate the renderer uses comes from here, so the screen can
be resized by changing ``CELL_SIZE`` and the two origin offsets.
"""

from enum import Enum, auto

from docs.games.othello.core.board import Board

CELL_COUNT: int = Board.SIZE
CELL_SIZE: int = 16
BOARD_PIXELS: int = CELL_SIZE * CELL_COUNT
BOARD_ORIGIN_X: int = 16
BOARD_ORIGIN_Y: int = 40
BOARD_BOTTOM: int = BOARD_ORIGIN_Y + BOARD_PIXELS

# The outermost grid lines sit one pixel past the filled area, so a
# frame drawn around the board has to cover one pixel more than it.
BOARD_FRAME: int = BOARD_PIXELS + 1
CELL_FRAME: int = CELL_SIZE + 1

SCREEN_WIDTH: int = BOARD_ORIGIN_X * 2 + BOARD_PIXELS
SCREEN_HEIGHT: int = BOARD_BOTTOM + 32

# Built-in Pyxel font metrics
FONT_WIDTH: int = 4
FONT_HEIGHT: int = 6
LINE_HEIGHT: int = 12

STONE_RADIUS: int = 6
STONE_DIAMETER: int = STONE_RADIUS * 2 + 1

# Sparkle geometry: the arm length of the four pointed star the site
# uses as its bullet, at the three sizes the game draws it.
HINT_RADIUS: int = 2
BOARD_STAR_RADIUS: int = 1
HEADLINE_STAR_RADIUS: int = 2

# The last move is marked at the corners of its cell, not on the stone
LAST_MOVE_TICK: int = 3

# Board decoration: the four star points of a standard 8x8 board,
# expressed as the grid intersections they sit on.
STAR_POINTS: tuple[tuple[int, int], ...] = ((2, 2), (2, 6), (6, 2), (6, 6))

SCORE_CENTER_Y: int = 16
SCORE_TEXT_Y: int = 13
BLACK_ICON_X: int = 34
WHITE_ICON_X: int = SCREEN_WIDTH - BLACK_ICON_X
SCORE_TEXT_GAP: int = 10
SCORE_TEXT_WIDTH: int = FONT_WIDTH * 2
BLACK_SCORE_X: int = BLACK_ICON_X + SCORE_TEXT_GAP
WHITE_SCORE_X: int = WHITE_ICON_X - SCORE_TEXT_GAP - SCORE_TEXT_WIDTH
TURN_TEXT_Y: int = 28
TURN_MARKER_RADIUS: int = STONE_RADIUS + 2

MESSAGE_Y: int = 174
FOOTER_Y: int = 186


class FooterButton(Enum):
    """A key hint in the footer, which is also a click target."""

    RESET = auto()
    QUIT = auto()


# The labels live here rather than in the renderer because their length
# is what sets the width of the areas that have to be hit-tested.
FOOTER_RESET_LABEL: str = "R:RESET"
FOOTER_QUIT_LABEL: str = "Q:QUIT"

# Wide enough that a click aimed at one label cannot land on the other.
# Both act at once and one of them leaves the game.
FOOTER_GAP: int = 14

# The labels are 6 pixels tall, which is below what a pointer can be
# aimed at reliably, so the area that answers to a click is grown.
FOOTER_HIT_PADDING: int = 3

_FOOTER_WIDTH: int = (len(FOOTER_RESET_LABEL) + len(FOOTER_QUIT_LABEL)) * FONT_WIDTH + FOOTER_GAP

FOOTER_RESET_X: int = (SCREEN_WIDTH - _FOOTER_WIDTH) // 2
FOOTER_QUIT_X: int = FOOTER_RESET_X + len(FOOTER_RESET_LABEL) * FONT_WIDTH + FOOTER_GAP

FOOTER_BUTTONS: tuple[tuple[FooterButton, int, str], ...] = (
    (FooterButton.RESET, FOOTER_RESET_X, FOOTER_RESET_LABEL),
    (FooterButton.QUIT, FOOTER_QUIT_X, FOOTER_QUIT_LABEL),
)

# Centered overlay panels, framed flush with the board below them
PANEL_X: int = BOARD_ORIGIN_X
PANEL_WIDTH: int = BOARD_FRAME
PANEL_PADDING: int = 10

# The caption that sits astride a panel's top border, as on the site
PANEL_LABEL_X: int = 8
PANEL_LABEL_PADDING: int = 2
PANEL_LABEL_LIFT: int = 2

# Gap between a headline and the sparkle on either side of it
HEADLINE_GAP: int = 6


def cell_origin(row: int, col: int) -> tuple[int, int]:
    """Get the top-left pixel of a board cell.

    Parameters
    ----------
    row : int
        The row index (0-based)
    col : int
        The column index (0-based)

    Returns
    -------
    tuple[int, int]
        The (x, y) pixel coordinate of the cell's top-left corner.

    """
    return (
        BOARD_ORIGIN_X + col * CELL_SIZE,
        BOARD_ORIGIN_Y + row * CELL_SIZE,
    )


def cell_center(row: int, col: int) -> tuple[int, int]:
    """Get the center pixel of a board cell.

    Parameters
    ----------
    row : int
        The row index (0-based)
    col : int
        The column index (0-based)

    Returns
    -------
    tuple[int, int]
        The (x, y) pixel coordinate of the cell's center.

    """
    origin_x, origin_y = cell_origin(row, col)
    half: int = CELL_SIZE // 2
    return (origin_x + half, origin_y + half)


def cell_at(pixel_x: int, pixel_y: int) -> tuple[int, int] | None:
    """Convert a screen position into board coordinates.

    Parameters
    ----------
    pixel_x : int
        The horizontal screen position, typically ``pyxel.mouse_x``
    pixel_y : int
        The vertical screen position, typically ``pyxel.mouse_y``

    Returns
    -------
    tuple[int, int] | None
        The (row, col) the position falls on, or None when the
        position is outside the board.

    """
    col: int = (pixel_x - BOARD_ORIGIN_X) // CELL_SIZE
    row: int = (pixel_y - BOARD_ORIGIN_Y) // CELL_SIZE

    if not (0 <= row < CELL_COUNT and 0 <= col < CELL_COUNT):
        return None

    return (row, col)


def centered_x(text: str) -> int:
    """Get the x position that horizontally centers a line of text.

    Parameters
    ----------
    text : str
        The text to be centered

    Returns
    -------
    int
        The x position to pass to ``pyxel.text``.

    """
    return (SCREEN_WIDTH - len(text) * FONT_WIDTH) // 2


def footer_button_at(pixel_x: int, pixel_y: int) -> FooterButton | None:
    """Convert a screen position into the footer button under it.

    Parameters
    ----------
    pixel_x : int
        The horizontal screen position, typically ``pyxel.mouse_x``
    pixel_y : int
        The vertical screen position, typically ``pyxel.mouse_y``

    Returns
    -------
    FooterButton | None
        The button the position falls on, or None when it falls on
        neither of them.

    """
    top: int = FOOTER_Y - FOOTER_HIT_PADDING
    bottom: int = FOOTER_Y + FONT_HEIGHT + FOOTER_HIT_PADDING
    if not (top <= pixel_y < bottom):
        return None

    for button, origin_x, label in FOOTER_BUTTONS:
        left: int = origin_x - FOOTER_HIT_PADDING
        right: int = origin_x + len(label) * FONT_WIDTH + FOOTER_HIT_PADDING
        if left <= pixel_x < right:
            return button

    return None
