"""Drawing routines for the Othello user interface.

Every function draws into the current Pyxel frame and holds no state,
leaving the scene code to decide what goes on screen and in what order.
"""

import pyxel

from docs.games.othello.core.board import Board
from docs.games.othello.ui import layout, starfield, theme
from docs.games.othello.ui.animation import AnimatedStone, FlipAnimation

# Dither strength used to darken the board behind an overlay panel.
# Kept high: a weaker dim leaves the white stones as a loud checker.
DIM_STRENGTH: float = 0.78
NO_DITHER: float = 1.0

# Below this width a stone is a sliver and an outline would swallow it.
EDGE_MIN_WIDTH: int = 2


def _draw_sparkle(center_x: int, center_y: int, radius: int, color: int) -> None:
    """Draw the four pointed star the site uses as its bullet.

    Parameters
    ----------
    center_x : int
        The horizontal center in pixels
    center_y : int
        The vertical center in pixels
    radius : int
        The length of each arm in pixels
    color : int
        The palette index to draw the star in

    """
    pyxel.line(center_x - radius, center_y, center_x + radius, center_y, color)
    pyxel.line(center_x, center_y - radius, center_x, center_y + radius, color)


def _draw_corner_ticks(
    origin_x: int,
    origin_y: int,
    size: int,
    length: int,
    color: int,
) -> None:
    """Bracket a square with a short right angle at each corner.

    Parameters
    ----------
    origin_x : int
        The left of the square in pixels
    origin_y : int
        The top of the square in pixels
    size : int
        The side length of the square in pixels
    length : int
        How far each arm runs from its corner in pixels
    color : int
        The palette index to draw the brackets in

    """
    for corner_x, step_x in ((origin_x, 1), (origin_x + size, -1)):
        for corner_y, step_y in ((origin_y, 1), (origin_y + size, -1)):
            pyxel.line(corner_x, corner_y, corner_x + step_x * length, corner_y, color)
            pyxel.line(corner_x, corner_y, corner_x, corner_y + step_y * length, color)


def _stone_color(player: int) -> int:
    """Get the fill color for a player's stones.

    Parameters
    ----------
    player : int
        The player identifier

    Returns
    -------
    int
        The palette index to fill the stone with.

    """
    if player == Board.BLACK:
        return theme.COL_STONE_BLACK
    return theme.COL_STONE_WHITE


def _draw_stone_at(
    center_x: int,
    center_y: int,
    width: int,
    height: int,
    player: int,
) -> None:
    """Draw one stone as an ellipse around a center point.

    Parameters
    ----------
    center_x : int
        The horizontal center in pixels
    center_y : int
        The vertical center in pixels
    width : int
        The horizontal diameter in pixels
    height : int
        The vertical diameter in pixels
    player : int
        The player whose color the stone is drawn in

    Notes
    -----
    Settled and animating stones both go through this function so a
    stone does not change shape when its animation ends.

    """
    left: int = center_x - width // 2
    top: int = center_y - height // 2

    pyxel.elli(left, top, width, height, _stone_color(player))

    if width > EDGE_MIN_WIDTH:
        pyxel.ellib(left, top, width, height, theme.COL_STONE_EDGE)


def player_label(player: int) -> str:
    """Get the display name of a player.

    Parameters
    ----------
    player : int
        The player identifier

    Returns
    -------
    str
        Either "BLACK" or "WHITE".

    """
    if player == Board.BLACK:
        return "BLACK"
    return "WHITE"


def text_center(pixel_y: int, text: str, color: int) -> None:
    """Draw a horizontally centered line of text.

    Parameters
    ----------
    pixel_y : int
        The top of the text in pixels
    text : str
        The text to draw
    color : int
        The palette index to draw the text in

    """
    pyxel.text(layout.centered_x(text), pixel_y, text, color)


def draw_backdrop() -> None:
    """Clear the frame and lay the night sky behind the board."""
    pyxel.cls(theme.COL_BACKDROP)
    starfield.draw()


def draw_board() -> None:
    """Draw the empty board: panel, grid, star points and shadow."""
    pyxel.rect(
        layout.BOARD_ORIGIN_X,
        layout.BOARD_ORIGIN_Y,
        layout.BOARD_PIXELS,
        layout.BOARD_PIXELS,
        theme.COL_BOARD,
    )

    board_right: int = layout.BOARD_ORIGIN_X + layout.BOARD_PIXELS
    for index in range(layout.CELL_COUNT + 1):
        offset: int = index * layout.CELL_SIZE
        line_x: int = layout.BOARD_ORIGIN_X + offset
        line_y: int = layout.BOARD_ORIGIN_Y + offset
        pyxel.line(
            line_x,
            layout.BOARD_ORIGIN_Y,
            line_x,
            layout.BOARD_BOTTOM,
            theme.COL_BOARD_LINE,
        )
        pyxel.line(
            layout.BOARD_ORIGIN_X,
            line_y,
            board_right,
            line_y,
            theme.COL_BOARD_LINE,
        )

    for row, col in layout.STAR_POINTS:
        star_x, star_y = layout.cell_origin(row, col)
        _draw_sparkle(
            star_x,
            star_y,
            layout.BOARD_STAR_RADIUS,
            theme.COL_BOARD_STAR,
        )

    # The board is framed like the bordered panels on the site.
    pyxel.rectb(
        layout.BOARD_ORIGIN_X,
        layout.BOARD_ORIGIN_Y,
        layout.BOARD_FRAME,
        layout.BOARD_FRAME,
        theme.COL_BOARD_EDGE,
    )

    # A one pixel shadow lifts the board off the backdrop.
    pyxel.line(
        layout.BOARD_ORIGIN_X + 1,
        layout.BOARD_BOTTOM + 1,
        board_right + 1,
        layout.BOARD_BOTTOM + 1,
        theme.COL_SHADOW,
    )
    pyxel.line(
        board_right + 1,
        layout.BOARD_ORIGIN_Y + 1,
        board_right + 1,
        layout.BOARD_BOTTOM + 1,
        theme.COL_SHADOW,
    )


def draw_stone(center_x: int, center_y: int, player: int) -> None:
    """Draw a full sized stone at a pixel position.

    Parameters
    ----------
    center_x : int
        The horizontal center in pixels
    center_y : int
        The vertical center in pixels
    player : int
        The player whose color the stone is drawn in

    """
    _draw_stone_at(
        center_x,
        center_y,
        layout.STONE_DIAMETER,
        layout.STONE_DIAMETER,
        player,
    )


def draw_stones(
    board: list[list[int]],
    skip: frozenset[tuple[int, int]],
) -> None:
    """Draw every settled stone on the board.

    Parameters
    ----------
    board : list[list[int]]
        The board contents to draw
    skip : frozenset[tuple[int, int]]
        Cells to leave blank, because an animation draws them instead

    """
    for row, values in enumerate(board):
        for col, value in enumerate(values):
            if value == Board.EMPTY or (row, col) in skip:
                continue
            center_x, center_y = layout.cell_center(row, col)
            draw_stone(center_x, center_y, value)


def draw_animation(animation: FlipAnimation) -> None:
    """Draw the current frame of a move animation.

    Parameters
    ----------
    animation : FlipAnimation
        The animation to draw

    """
    stone: AnimatedStone
    for stone in animation.stones():
        center_x, center_y = layout.cell_center(stone.row, stone.col)
        _draw_stone_at(
            center_x,
            center_y,
            stone.width,
            stone.height,
            stone.player,
        )


def draw_hints(moves: list[tuple[int, int]]) -> None:
    """Mark every cell the player to move can play on.

    Parameters
    ----------
    moves : list[tuple[int, int]]
        The legal moves to mark

    """
    for row, col in moves:
        center_x, center_y = layout.cell_center(row, col)
        _draw_sparkle(center_x, center_y, layout.HINT_RADIUS, theme.COL_HINT)


def draw_hover(
    cell: tuple[int, int] | None,
    moves: list[tuple[int, int]],
) -> None:
    """Outline the hovered cell, but only when it is playable.

    Parameters
    ----------
    cell : tuple[int, int] | None
        The hovered cell, or None when the cursor is off the board
    moves : list[tuple[int, int]]
        The legal moves for the player to move

    """
    if cell is None or cell not in moves:
        return

    origin_x, origin_y = layout.cell_origin(cell[0], cell[1])
    pyxel.rectb(
        origin_x,
        origin_y,
        layout.CELL_FRAME,
        layout.CELL_FRAME,
        theme.COL_HOVER,
    )


def draw_last_move(cell: tuple[int, int]) -> None:
    """Bracket the cell that was played most recently.

    Parameters
    ----------
    cell : tuple[int, int]
        The (row, col) of the most recent move

    Notes
    -----
    The corners are marked rather than the stone, so the mark keeps
    its contrast on either color.

    """
    origin_x, origin_y = layout.cell_origin(cell[0], cell[1])
    _draw_corner_ticks(
        origin_x,
        origin_y,
        layout.CELL_SIZE,
        layout.LAST_MOVE_TICK,
        theme.COL_ACCENT,
    )


def draw_hud(
    score: tuple[int, int],
    current_player: int,
    *,
    highlight: bool,
) -> None:
    """Draw the score panel above the board.

    Parameters
    ----------
    score : tuple[int, int]
        The current (black_count, white_count)
    current_player : int
        The player to move, whose score gets the turn marker
    highlight : bool
        Whether to draw the turn marker, which the caller toggles to
        make it blink

    """
    black_count, white_count = score

    draw_stone(
        layout.BLACK_ICON_X,
        layout.SCORE_CENTER_Y,
        Board.BLACK,
    )
    pyxel.text(
        layout.BLACK_SCORE_X,
        layout.SCORE_TEXT_Y,
        f"{black_count:2d}",
        theme.COL_TEXT,
    )

    draw_stone(
        layout.WHITE_ICON_X,
        layout.SCORE_CENTER_Y,
        Board.WHITE,
    )
    pyxel.text(
        layout.WHITE_SCORE_X,
        layout.SCORE_TEXT_Y,
        f"{white_count:2d}",
        theme.COL_TEXT,
    )

    if not highlight or current_player == Board.EMPTY:
        return

    marker_x: int = layout.BLACK_ICON_X if current_player == Board.BLACK else layout.WHITE_ICON_X
    pyxel.circb(
        marker_x,
        layout.SCORE_CENTER_Y,
        layout.TURN_MARKER_RADIUS,
        theme.COL_ACCENT,
    )


def draw_turn(player: int) -> None:
    """Name the player to move, below the score panel.

    Parameters
    ----------
    player : int
        The player to move; nothing is drawn once the game has ended

    """
    if player == Board.EMPTY:
        return

    text_center(
        layout.TURN_TEXT_Y,
        f"{player_label(player)} TO MOVE",
        theme.COL_TEXT_DIM,
    )


def draw_message(text: str) -> None:
    """Draw a transient notice below the board.

    Parameters
    ----------
    text : str
        The notice to draw

    """
    text_center(layout.MESSAGE_Y, text, theme.COL_ACCENT)


def draw_footer(hovered: layout.FooterButton | None) -> None:
    """Draw the permanent key hints at the bottom of the screen.

    Parameters
    ----------
    hovered : layout.FooterButton | None
        The hint the pointer is over, lit to show it can be clicked

    """
    for button, origin_x, label in layout.FOOTER_BUTTONS:
        color: int = theme.COL_TEXT_BRIGHT if button is hovered else theme.COL_TEXT_DIM
        pyxel.text(origin_x, layout.FOOTER_Y, label, color)


def draw_dim_overlay() -> None:
    """Darken the board behind an overlay panel.

    Notes
    -----
    Only the board is dimmed: dimming the sky as well would put out
    most of the stars.

    """
    pyxel.dither(DIM_STRENGTH)
    pyxel.rect(
        layout.BOARD_ORIGIN_X,
        layout.BOARD_ORIGIN_Y,
        layout.BOARD_FRAME,
        layout.BOARD_FRAME,
        theme.COL_SHADOW,
    )
    pyxel.dither(NO_DITHER)


def _draw_panel_label(top: int, label: str) -> None:
    """Sit a caption astride a panel's top border.

    Parameters
    ----------
    top : int
        The top of the panel in pixels
    label : str
        The caption to write

    """
    text_x: int = layout.PANEL_X + layout.PANEL_LABEL_X
    text_y: int = top - layout.PANEL_LABEL_LIFT
    width: int = len(label) * layout.FONT_WIDTH + layout.PANEL_LABEL_PADDING * 2

    # The chip is filled first so it cuts the border out behind itself.
    pyxel.rect(
        text_x - layout.PANEL_LABEL_PADDING,
        text_y,
        width,
        layout.FONT_HEIGHT,
        theme.COL_BACKDROP,
    )
    pyxel.text(text_x, text_y, label, theme.COL_STAR_SOFT)


def draw_panel(top: int, height: int, label: str) -> None:
    """Draw an empty overlay panel across the width of the board.

    Parameters
    ----------
    top : int
        The top of the panel in pixels
    height : int
        The height of the panel in pixels
    label : str
        The caption to sit on the panel's top border

    """
    pyxel.rect(
        layout.PANEL_X,
        top,
        layout.PANEL_WIDTH,
        height,
        theme.COL_BACKDROP,
    )
    pyxel.rectb(
        layout.PANEL_X,
        top,
        layout.PANEL_WIDTH,
        height,
        theme.COL_BOARD_EDGE,
    )
    _draw_panel_label(top, label)


def draw_headline(pixel_y: int, text: str) -> None:
    """Draw a centered headline with a sparkle on either side.

    Parameters
    ----------
    pixel_y : int
        The top of the text in pixels
    text : str
        The headline to draw

    """
    text_x: int = layout.centered_x(text)
    text_width: int = len(text) * layout.FONT_WIDTH
    star_y: int = pixel_y + layout.FONT_HEIGHT // 2 - 1

    pyxel.text(text_x, pixel_y, text, theme.COL_TEXT_BRIGHT)
    for star_x in (
        text_x - layout.HEADLINE_GAP,
        text_x + text_width + layout.HEADLINE_GAP - 1,
    ):
        _draw_sparkle(
            star_x,
            star_y,
            layout.HEADLINE_STAR_RADIUS,
            theme.COL_ACCENT,
        )
