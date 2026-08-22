"""The night sky the board sits on.

Stars, the glow along the top edge and the occasional shooting star,
taken from the background of the page that links to the game. The sky
is a pure function of ``pyxel.frame_count``, and only the margins are
populated: the board covers the middle, and a streak passes behind it
the way the ones on the site pass behind its panels.
"""

from typing import NamedTuple

import pyxel

from docs.games.othello.ui import layout, theme

NO_DITHER: float = 1.0


class Star(NamedTuple):
    """One fixed star in the backdrop.

    Attributes
    ----------
    x : int
        The horizontal position in pixels
    y : int
        The vertical position in pixels
    color : int
        The palette index the star is drawn in while it is lit
    twinkle : int
        Frames spent lit, then the same again dimmed, or 0 for a star
        that holds steady

    """

    x: int
    y: int
    color: int
    twinkle: int


# The site fades a lighter navy in from the top edge. Dithering is the
# only gradient Pyxel has, so the fade is cut into bands.
GLOW_BANDS: tuple[tuple[int, int, float], ...] = (
    (0, 9, 0.6),
    (9, 9, 0.38),
    (18, 10, 0.2),
    (28, 14, 0.08),
)

# A star's position sets its phase, so neighbours never blink together.
PHASE_WEIGHT_X: int = 7
PHASE_WEIGHT_Y: int = 13

# A streak crosses at the angle the site sends its own, from off the
# top right corner down to the left, until the board hides it.
SHOOTING_STAR_PERIOD: int = 430
SHOOTING_STAR_FRAMES: int = 30
SHOOTING_STAR_FADE_FRAMES: int = 9
SHOOTING_STAR_SPEED_X: float = -3.4
SHOOTING_STAR_SPEED_Y: float = 2.9
SHOOTING_STAR_START_X: int = layout.SCREEN_WIDTH + 12
SHOOTING_STAR_START_Y: int = -12
SHOOTING_STAR_TAIL_FRAMES: float = 4.5
SHOOTING_STAR_TAIL_DITHER: float = 0.55

_FAINT: int = theme.COL_STAR_FAINT
_SOFT: int = theme.COL_STAR_SOFT
_LIT: int = theme.COL_STAR_LIT

# Scattered once with a minimum spacing, then frozen here so the same
# sky comes up every run. Ordered top to bottom.
STARS: tuple[Star, ...] = (
    Star(48, 2, _FAINT, 0),
    Star(125, 2, _LIT, 0),
    Star(97, 3, _FAINT, 0),
    Star(15, 4, _FAINT, 0),
    Star(32, 8, _SOFT, 46),
    Star(63, 11, _SOFT, 78),
    Star(87, 11, _FAINT, 0),
    Star(130, 12, _FAINT, 0),
    Star(155, 12, _LIT, 70),
    Star(17, 13, _FAINT, 0),
    Star(141, 17, _SOFT, 78),
    Star(53, 19, _LIT, 70),
    Star(119, 19, _LIT, 70),
    Star(31, 20, _FAINT, 0),
    Star(20, 26, _FAINT, 0),
    Star(124, 32, _FAINT, 0),
    Star(157, 42, _FAINT, 0),
    Star(149, 44, _LIT, 54),
    Star(152, 58, _LIT, 54),
    Star(1, 67, _SOFT, 78),
    Star(2, 76, _LIT, 90),
    Star(156, 86, _SOFT, 62),
    Star(7, 89, _FAINT, 0),
    Star(154, 102, _FAINT, 0),
    Star(2, 107, _FAINT, 0),
    Star(10, 122, _FAINT, 0),
    Star(151, 143, _FAINT, 0),
    Star(10, 146, _FAINT, 0),
    Star(84, 175, _FAINT, 0),
    Star(74, 177, _SOFT, 0),
    Star(119, 179, _FAINT, 0),
    Star(28, 183, _LIT, 54),
    Star(85, 184, _FAINT, 0),
    Star(98, 186, _FAINT, 0),
    Star(144, 186, _FAINT, 0),
    Star(127, 187, _FAINT, 0),
    Star(13, 189, _FAINT, 0),
    Star(50, 190, _SOFT, 46),
    Star(46, 197, _FAINT, 0),
)


def _star_color(star: Star) -> int:
    """Get the color a star is drawn in on the current frame.

    Parameters
    ----------
    star : Star
        The star to be drawn

    Returns
    -------
    int
        The star's own color while lit, the faintest one while not.

    """
    if star.twinkle == 0:
        return star.color

    phase: int = (star.x * PHASE_WEIGHT_X + star.y * PHASE_WEIGHT_Y) % star.twinkle
    if ((pyxel.frame_count + phase) // star.twinkle) % 2 == 0:
        return star.color
    return theme.COL_STAR_FAINT


def _draw_glow() -> None:
    """Fade the sky glow in from the top edge of the screen."""
    for top, height, strength in GLOW_BANDS:
        pyxel.dither(strength)
        pyxel.rect(0, top, layout.SCREEN_WIDTH, height, theme.COL_SKY_GLOW)
    pyxel.dither(NO_DITHER)


def _draw_stars() -> None:
    """Draw every fixed star at its brightness for this frame."""
    for star in STARS:
        pyxel.pset(star.x, star.y, _star_color(star))


def _draw_shooting_star() -> None:
    """Draw the streak, on the frames of its cycle where it is out."""
    elapsed: int = pyxel.frame_count % SHOOTING_STAR_PERIOD
    if elapsed >= SHOOTING_STAR_FRAMES:
        return

    fade: float = min(
        NO_DITHER,
        elapsed / SHOOTING_STAR_FADE_FRAMES,
        (SHOOTING_STAR_FRAMES - elapsed) / SHOOTING_STAR_FADE_FRAMES,
    )
    head_x: float = SHOOTING_STAR_START_X + SHOOTING_STAR_SPEED_X * elapsed
    head_y: float = SHOOTING_STAR_START_Y + SHOOTING_STAR_SPEED_Y * elapsed

    pyxel.dither(fade * SHOOTING_STAR_TAIL_DITHER)
    pyxel.line(
        head_x - SHOOTING_STAR_SPEED_X * SHOOTING_STAR_TAIL_FRAMES,
        head_y - SHOOTING_STAR_SPEED_Y * SHOOTING_STAR_TAIL_FRAMES,
        head_x,
        head_y,
        theme.COL_STAR_SOFT,
    )
    pyxel.dither(fade)
    pyxel.pset(head_x, head_y, theme.COL_STAR_LIT)
    pyxel.dither(NO_DITHER)


def draw() -> None:
    """Draw the whole sky: the glow, the stars and the streak."""
    _draw_glow()
    _draw_stars()
    _draw_shooting_star()
