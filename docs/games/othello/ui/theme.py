"""Color definitions for the Othello user interface.

Pyxel's fixed 16 color palette is overwritten entirely, with values
taken from the stylesheet of the page that links to the game. The
stones stay black and white; everything around them is sky.
"""

import pyxel

# Palette indices used by the renderer.
COL_STONE_BLACK: int = 0
COL_BACKDROP: int = 1
COL_SKY_GLOW: int = 2
COL_BOARD: int = 3
COL_BOARD_LINE: int = 4
COL_BOARD_EDGE: int = 5
COL_STAR_FAINT: int = 6
COL_STONE_WHITE: int = 7
COL_TEXT_DIM: int = 8
COL_STAR_SOFT: int = 9
COL_HINT: int = 10
COL_TEXT: int = 11
COL_TEXT_BRIGHT: int = 12
COL_ACCENT: int = 13
COL_STAR_LIT: int = 14
COL_SHADOW: int = 15

# One pale rim on both stones. Without it the black stone sinks into
# the board, and into the backdrop behind the score icons.
COL_STONE_EDGE: int = COL_STAR_SOFT

# The star points have to read against the grid, not blend into it.
COL_BOARD_STAR: int = COL_STAR_FAINT

# The hovered cell has to outrank the move hints sitting next to it.
COL_HOVER: int = COL_STAR_LIT

# Each comment names where on the site the color comes from.
_PALETTE: dict[int, int] = {
    COL_STONE_BLACK: 0x090D1E,  # near black, tinted toward the sky
    COL_BACKDROP: 0x070B1A,  # page background
    COL_SKY_GLOW: 0x16224A,  # top of the page background gradient
    COL_BOARD: 0x131C43,  # panel fill over that gradient
    COL_BOARD_LINE: 0x243059,
    COL_BOARD_EDGE: 0x3D4A7A,  # panel border
    COL_STAR_FAINT: 0x4A5A96,  # spent meter marks
    COL_STONE_WHITE: 0xF2F6FF,
    COL_TEXT_DIM: 0x6F83BD,  # table headers, muted labels
    COL_STAR_SOFT: 0x8EA3DC,  # panel captions
    COL_HINT: 0xA9BDFF,  # accent blue, the hovered row fill
    COL_TEXT: 0xC6D3F5,  # body text
    COL_TEXT_BRIGHT: 0xEEF2FF,  # headings
    COL_ACCENT: 0xFFD9A0,  # the gold coin mark on the game center panel
    COL_STAR_LIT: 0xDCE6FF,  # the brightest stars in the background
    COL_SHADOW: 0x03050C,
}


def apply_palette() -> None:
    """Write the night sky palette over Pyxel's default one.

    Notes
    -----
    Must be called after ``pyxel.init()``, since the palette does not
    exist before the engine is initialized.

    """
    for index, rgb in _PALETTE.items():
        pyxel.colors[index] = rgb
