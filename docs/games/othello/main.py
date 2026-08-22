"""Entry point for the Pyxel Othello game.

Run from the repository root::

    python -m docs.games.othello.main

"""

from docs.games.othello.app import App


def main() -> None:
    """Open the game window and run until the player quits."""
    App().run()


if __name__ == "__main__":
    main()
