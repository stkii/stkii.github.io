from docs.games.othello.core.state import Cell


def get_opponent_player(player: int) -> int:
    """Get the player opposing the given one.

    Parameters
    ----------
    player : int
        The player to find the opponent of

    Returns
    -------
    int
        The opposing player identifier.

    """
    if player == Cell.FIRST_PLAYER.value:
        return Cell.SECONT_PLAYER.value
    return Cell.FIRST_PLAYER.value
