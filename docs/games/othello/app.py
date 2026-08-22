"""Scene handling and input for the Othello application.

A small state machine over :class:`Scene`. The board is drawn in every
scene; the title and result screens lay a panel over it. A move
animation is a state of its own, so no input is accepted while stones
are still turning and a double click cannot slip a second move past it.
"""

import sys
from enum import Enum, auto

import pyxel

from docs.games.othello.session import GameSession, MoveResult, TurnEvent
from docs.games.othello.ui import layout, renderer, theme
from docs.games.othello.ui.animation import FlipAnimation

WINDOW_TITLE: str = "Othello"
FPS: int = 60

IS_WEB: bool = sys.platform == "emscripten"

# Quitting in a browser cannot close anything, and stopping the loop
# would strand the player on a dead canvas. The way out is the page the
# cabinet was clicked on, one level up from <site>/games/othello.html.
SITE_URL: str = "../"

# Frames a transient message stays on screen.
MESSAGE_FRAMES: int = 100

# Frames between blink toggles for prompts and the turn marker.
BLINK_FRAMES: int = 20

TITLE_PANEL_TOP: int = 84
TITLE_PANEL_HEIGHT: int = 38
TITLE_PANEL_LABEL: str = "GAME"
TITLE_TEXT: str = "OTHELLO"
RESULT_PANEL_TOP: int = 74
RESULT_PANEL_HEIGHT: int = 50
RESULT_PANEL_LABEL: str = "RESULT"
THINKING_TEXT: str = "THINKING"


class Scene(Enum):
    """The screen the application is currently showing.

    Attributes
    ----------
    TITLE
        The start screen, waiting for the first click
    PLAYING
        The game itself, including move animations
    RESULT
        The final score, waiting for a click to play again

    """

    TITLE = auto()
    PLAYING = auto()
    RESULT = auto()


class App:
    """The Pyxel application: owns the session and the current scene.

    Attributes
    ----------
    _session : GameSession
        The game being played
    _scene : Scene
        The screen currently being shown
    _animation : FlipAnimation | None
        The move animation in progress, if any
    _message : str
        The transient notice below the board
    _message_frames : int
        Frames left before the notice disappears
    _is_announced : bool
        Whether the notice that the computer is thinking has been on
        screen for a frame yet

    """

    def __init__(self, *, headless: bool = False) -> None:
        """Initialize the engine and the first scene.

        Parameters
        ----------
        headless : bool, optional
            Run without opening a window, so the loop can be driven
            from a test

        """
        pyxel.init(
            layout.SCREEN_WIDTH,
            layout.SCREEN_HEIGHT,
            title=WINDOW_TITLE,
            fps=FPS,
            # Q is handled in the loop instead, so that leaving means
            # the same thing on the web as it does here.
            quit_key=pyxel.KEY_NONE,
            headless=headless,
        )
        theme.apply_palette()
        pyxel.mouse(visible=True)

        self._session: GameSession = GameSession()
        self._scene: Scene = Scene.TITLE
        self._animation: FlipAnimation | None = None
        self._message: str = ""
        self._message_frames: int = 0
        self._is_announced: bool = False

    @staticmethod
    def _is_blink_on() -> bool:
        """Check whether blinking elements are visible this frame."""
        return (pyxel.frame_count // BLINK_FRAMES) % 2 == 0

    @staticmethod
    def _is_clicked() -> bool:
        """Check whether the left mouse button was pressed this frame."""
        return pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)

    @staticmethod
    def _hovered_button() -> layout.FooterButton | None:
        """Get the footer hint the pointer is over, if any."""
        return layout.footer_button_at(pyxel.mouse_x, pyxel.mouse_y)

    def _handle_footer(self) -> bool:
        """Act on the footer hints, by key or by click.

        Returns
        -------
        bool
            Whether the frame was spent, so the scene should be left
            alone for it.

        """
        pressed: layout.FooterButton | None = None
        if pyxel.btnp(pyxel.KEY_R):
            pressed = layout.FooterButton.RESET
        elif pyxel.btnp(pyxel.KEY_Q):
            pressed = layout.FooterButton.QUIT
        elif self._is_clicked():
            pressed = self._hovered_button()

        if pressed is None:
            return False

        if pressed is layout.FooterButton.RESET:
            self._start_game()
        else:
            self._quit()

        return True

    def _quit(self) -> None:
        """Leave the game, by the only exit the platform offers."""
        if not IS_WEB:
            pyxel.quit()
            return

        # Only importable under Pyodide, so it cannot be imported at
        # the top of a module that also has to run natively.
        import js  # noqa: PLC0415

        js.window.location.href = SITE_URL

    def _set_message(self, text: str) -> None:
        """Show a transient notice below the board.

        Parameters
        ----------
        text : str
            The notice to show

        """
        self._message = text
        self._message_frames = MESSAGE_FRAMES

    def _start_game(self) -> None:
        """Reset the board and enter the playing scene."""
        self._session.reset()
        self._animation = None
        self._message = ""
        self._message_frames = 0
        self._is_announced = False
        self._scene = Scene.PLAYING

    def _resolve_turn(self) -> None:
        """React to the move whose animation just finished.

        Notes
        -----
        Reporting a pass is deferred until the animation ends, so the
        notice does not appear while stones are still turning.

        """
        result: MoveResult | None = self._session.last_move
        if result is None:
            return

        if result.event is TurnEvent.ENDED:
            self._scene = Scene.RESULT
        elif result.event is TurnEvent.PASSED:
            self._set_message(f"{renderer.player_label(result.opponent)} PASSED")

    def _advance_animation(self) -> None:
        """Step the current animation, resolving the turn when it ends."""
        animation: FlipAnimation | None = self._animation
        if animation is None:
            return

        animation.update()
        if not animation.is_finished:
            return

        self._animation = None
        self._resolve_turn()

    def _begin_animation(self, result: MoveResult) -> None:
        """Start turning the stones a move captured.

        Parameters
        ----------
        result : MoveResult
            The move that was just played

        """
        self._message_frames = 0
        self._animation = FlipAnimation(
            result.placed,
            result.flipped,
            result.player,
            result.opponent,
        )

    def _handle_board_click(self) -> None:
        """Play the clicked cell, if it holds a legal move."""
        if not self._is_clicked():
            return

        cell: tuple[int, int] | None = layout.cell_at(pyxel.mouse_x, pyxel.mouse_y)
        if cell is None:
            return

        result: MoveResult | None = self._session.play(cell[0], cell[1])
        if result is None:
            return

        self._begin_animation(result)

    def _take_cpu_turn(self) -> None:
        """Let the computer move, after saying that it is thinking.

        Notes
        -----
        The search blocks the loop, so the frame it runs on is a frame
        that never gets drawn. Claiming this turn without moving on it
        lets the notice reach the screen first, which turns a window
        that has frozen into a window that is visibly busy.

        """
        if not self._is_announced:
            self._is_announced = True
            return

        self._is_announced = False
        result: MoveResult | None = self._session.play_cpu()
        if result is None:
            return

        self._begin_animation(result)

    def _update_title(self) -> None:
        """Wait for the player to start a game."""
        if self._is_clicked() or pyxel.btnp(pyxel.KEY_RETURN):
            self._start_game()

    def _update_playing(self) -> None:
        """Advance the game by one frame."""
        if self._animation is not None:
            self._advance_animation()
            return

        if self._session.is_cpu_turn:
            self._take_cpu_turn()
            return

        self._handle_board_click()

    def _update_result(self) -> None:
        """Wait for the player to start another game."""
        if self._is_clicked():
            self._start_game()

    def _draw_board_contents(self) -> None:
        """Draw the stones, letting any animation own its own cells."""
        animation: FlipAnimation | None = self._animation
        skip: frozenset[tuple[int, int]] = (
            animation.cells if animation is not None else frozenset()
        )

        renderer.draw_stones(self._session.board, skip)

        if animation is not None:
            renderer.draw_animation(animation)

    def _draw_playing_overlay(self) -> None:
        """Draw the move hints, turn label and any transient notice."""
        is_cpu_turn: bool = self._session.is_cpu_turn

        if self._animation is None:
            # The hints belong to whoever is choosing, so they go away
            # while the computer is the one choosing.
            if not is_cpu_turn:
                moves: list[tuple[int, int]] = self._session.valid_moves
                hovered: tuple[int, int] | None = layout.cell_at(
                    pyxel.mouse_x,
                    pyxel.mouse_y,
                )
                renderer.draw_hints(moves)
                renderer.draw_hover(hovered, moves)

            last_move: MoveResult | None = self._session.last_move
            if last_move is not None:
                renderer.draw_last_move(last_move.placed)

        renderer.draw_turn(self._session.current_player)

        if is_cpu_turn and self._animation is None:
            renderer.draw_message(THINKING_TEXT)
        elif self._message_frames > 0:
            renderer.draw_message(self._message)

    def _draw_title_panel(self) -> None:
        """Draw the start screen over the board."""
        renderer.draw_dim_overlay()
        renderer.draw_panel(
            TITLE_PANEL_TOP,
            TITLE_PANEL_HEIGHT,
            TITLE_PANEL_LABEL,
        )

        first_line: int = TITLE_PANEL_TOP + layout.PANEL_PADDING
        renderer.draw_headline(first_line, TITLE_TEXT)

        if self._is_blink_on():
            renderer.text_center(
                first_line + layout.LINE_HEIGHT,
                "CLICK TO START",
                theme.COL_HINT,
            )

    def _result_headline(self) -> str:
        """Get the headline naming the winner.

        Returns
        -------
        str
            Either "<COLOR> WINS" or "DRAW".

        """
        if self._session.is_draw:
            return "DRAW"
        return f"{renderer.player_label(self._session.winner)} WINS"

    def _draw_result_panel(self) -> None:
        """Draw the final score over the board."""
        renderer.draw_dim_overlay()
        renderer.draw_panel(
            RESULT_PANEL_TOP,
            RESULT_PANEL_HEIGHT,
            RESULT_PANEL_LABEL,
        )

        black_count, white_count = self._session.score
        first_line: int = RESULT_PANEL_TOP + layout.PANEL_PADDING

        renderer.draw_headline(first_line, self._result_headline())
        renderer.text_center(
            first_line + layout.LINE_HEIGHT,
            f"{black_count} - {white_count}",
            theme.COL_TEXT,
        )

        if self._is_blink_on():
            renderer.text_center(
                first_line + layout.LINE_HEIGHT * 2,
                "CLICK TO RETRY",
                theme.COL_TEXT_DIM,
            )

    def update(self) -> None:
        """Advance the application by one frame."""
        if self._message_frames > 0:
            self._message_frames -= 1

        # The footer is on screen in every scene, so its two hints are
        # answered before the scene sees the frame. Otherwise the title
        # and result screens, which start a game on a click anywhere,
        # would act on the same click as the footer.
        if self._handle_footer():
            return

        if self._scene is Scene.TITLE:
            self._update_title()
        elif self._scene is Scene.PLAYING:
            self._update_playing()
        else:
            self._update_result()

    def draw(self) -> None:
        """Draw one frame of the application."""
        renderer.draw_backdrop()
        renderer.draw_board()
        self._draw_board_contents()
        # The score has nothing to say before the first move.
        if self._scene is not Scene.TITLE:
            renderer.draw_hud(
                self._session.score,
                self._session.current_player,
                highlight=self._scene is Scene.PLAYING and self._is_blink_on(),
            )

        if self._scene is Scene.TITLE:
            self._draw_title_panel()
        elif self._scene is Scene.PLAYING:
            self._draw_playing_overlay()
        else:
            self._draw_result_panel()

        # Always on screen, so it goes over whatever the scene put up.
        renderer.draw_footer(self._hovered_button())

    def run(self) -> None:
        """Hand control to the Pyxel main loop."""
        pyxel.run(self.update, self.draw)
