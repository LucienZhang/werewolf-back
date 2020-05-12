from .enums import GameEnum


class GameFinished(Exception):
    def __init__(self, gid: int, winner: GameEnum):
        self.gid = gid
        self.winner = winner
