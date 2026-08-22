"""Stone flipping animation.

The placed stone grows into its cell; each captured stone is squashed
horizontally until edge-on, then grows back in the other color. The
further a stone sits from the placed one, the later it starts, which
makes the capture read as a wave travelling outwards.
"""

import math
from typing import NamedTuple

from docs.games.othello.ui import layout

DROP_FRAMES: int = 5
FLIP_FRAMES: int = 8
WAVE_DELAY_FRAMES: int = 2
MIN_STONE_WIDTH: int = 1

# The spin shows the far side of the stone past its halfway point.
HALF_TURN: float = 0.5


class AnimatedStone(NamedTuple):
    """A stone captured mid-animation, ready to be drawn.

    Attributes
    ----------
    row : int
        The row the stone sits on (0-based)
    col : int
        The column the stone sits on (0-based)
    width : int
        The horizontal diameter in pixels
    height : int
        The vertical diameter in pixels
    player : int
        The color to draw the stone in right now

    """

    row: int
    col: int
    width: int
    height: int
    player: int


def _clamp_progress(value: float) -> float:
    """Clamp an animation progress value into the 0.0-1.0 range.

    Parameters
    ----------
    value : float
        The raw progress value

    Returns
    -------
    float
        The value limited to the closed interval [0.0, 1.0].

    """
    return min(max(value, 0.0), 1.0)


class FlipAnimation:
    """Plays back a single move as a stone drop and a capture wave.

    Attributes
    ----------
    _placed : tuple[int, int]
        The (row, col) of the newly placed stone
    _flipped : tuple[tuple[int, int], ...]
        Every (row, col) that changes owner
    _player : int
        The player who made the move
    _opponent : int
        The color the captured stones are turning away from
    _delays : dict[tuple[int, int], int]
        Frames each captured stone waits before it starts spinning
    _frame : int
        Frames elapsed since the animation started
    _duration : int
        Total frames the animation runs for

    """

    def __init__(
        self,
        placed: tuple[int, int],
        flipped: tuple[tuple[int, int], ...],
        player: int,
        opponent: int,
    ) -> None:
        """Set up the animation for one move.

        Parameters
        ----------
        placed : tuple[int, int]
            The (row, col) of the newly placed stone
        flipped : tuple[tuple[int, int], ...]
            Every (row, col) that changes owner
        player : int
            The player who made the move
        opponent : int
            The color the captured stones are turning away from

        """
        self._placed: tuple[int, int] = placed
        self._flipped: tuple[tuple[int, int], ...] = flipped
        self._player: int = player
        self._opponent: int = opponent
        self._delays: dict[tuple[int, int], int] = {cell: self._delay_of(cell) for cell in flipped}
        self._frame: int = 0
        # Passing a single list keeps `max` safe even for the
        # hypothetical move that captures nothing.
        self._duration: int = max(
            [
                DROP_FRAMES,
                *(delay + FLIP_FRAMES for delay in self._delays.values()),
            ],
        )

    def _delay_of(self, cell: tuple[int, int]) -> int:
        """Get how long a captured stone waits before it spins.

        Parameters
        ----------
        cell : tuple[int, int]
            The (row, col) of the captured stone

        Returns
        -------
        int
            The delay in frames, proportional to the stone's distance
            from the placed stone.

        """
        row, col = cell
        placed_row, placed_col = self._placed
        distance: int = max(abs(row - placed_row), abs(col - placed_col))
        return distance * WAVE_DELAY_FRAMES

    def _drop_stone(self) -> AnimatedStone:
        """Get the placed stone growing into its cell.

        Returns
        -------
        AnimatedStone
            The placed stone at its current size.

        """
        progress: float = _clamp_progress(self._frame / DROP_FRAMES)
        size: int = max(
            MIN_STONE_WIDTH,
            round(layout.STONE_DIAMETER * progress),
        )
        row, col = self._placed
        return AnimatedStone(row, col, size, size, self._player)

    def _spinning_stone(self, cell: tuple[int, int]) -> AnimatedStone:
        """Get a captured stone at its current point in the spin.

        Parameters
        ----------
        cell : tuple[int, int]
            The (row, col) of the captured stone

        Returns
        -------
        AnimatedStone
            The stone squashed to its current width, in whichever
            color faces the player right now.

        """
        elapsed: int = self._frame - self._delays[cell]
        progress: float = _clamp_progress(elapsed / FLIP_FRAMES)

        width: int = max(
            MIN_STONE_WIDTH,
            round(layout.STONE_DIAMETER * abs(math.cos(math.pi * progress))),
        )
        facing: int = self._opponent if progress < HALF_TURN else self._player
        row, col = cell

        return AnimatedStone(row, col, width, layout.STONE_DIAMETER, facing)

    @property
    def cells(self) -> frozenset[tuple[int, int]]:
        """Get every cell this animation draws itself.

        Notes
        -----
        The renderer skips these cells when drawing the settled board,
        so the animation is not drawn on top of a finished stone.

        """
        return frozenset({self._placed, *self._flipped})

    @property
    def is_finished(self) -> bool:
        """Check whether the animation has run to completion."""
        return self._frame >= self._duration

    def stones(self) -> list[AnimatedStone]:
        """Get every stone to draw for the current frame.

        Returns
        -------
        list[AnimatedStone]
            The placed stone followed by every captured stone.

        """
        stones: list[AnimatedStone] = [self._drop_stone()]
        stones.extend(self._spinning_stone(cell) for cell in self._flipped)
        return stones

    def update(self) -> None:
        """Advance the animation by one frame."""
        self._frame += 1
