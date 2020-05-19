from .enums import GameEnum
from sqlalchemy.orm import Session


class GameFinished(Exception):
    def __init__(self, gid: int, winner: GameEnum, db: Session):
        self.gid = gid
        self.winner = winner
        self.db = db
