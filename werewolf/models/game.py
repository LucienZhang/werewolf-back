from datetime import datetime, timedelta
from typing import List
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.ext.mutable import MutableDict, MutableList
from werewolf.utils.enums import GameEnum

from .base import Base, EnumType, JSONEncodedType


class Game(Base):
    gid = Column(Integer, primary_key=True, autoincrement=True)
    host_uid = Column(Integer, nullable=False)
    status = Column(EnumType, nullable=False)
    victory_mode = Column(EnumType, nullable=False)
    captain_mode = Column(EnumType, nullable=False)
    witch_mode = Column(EnumType, nullable=False)
    wolf_mode = Column(EnumType, nullable=False)
    end_time = Column(DateTime, nullable=False)
    # updated_on = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    players = Column(MutableList.as_mutable(JSONEncodedType(225)), nullable=False)
    cards = Column(MutableList.as_mutable(JSONEncodedType(1023)), nullable=False)
    days = Column(Integer, nullable=False)
    now_index = Column(Integer, nullable=False)
    step_cnt = Column(Integer, nullable=False)
    steps = Column(MutableList.as_mutable(JSONEncodedType(1023)), nullable=False)
    history = Column(MutableDict.as_mutable(JSONEncodedType(1023)), nullable=False)
    captain_pos = Column(Integer, nullable=False)

    @staticmethod
    def get_wolf_mode_by_cards(cards: List[GameEnum]) -> GameEnum:
        # WOLF_MODE_FIRST if there is no thrid party, else WOLF_MODE_ALL
        if GameEnum.ROLE_TYPE_CUPID in cards:
            return GameEnum.WOLF_MODE_ALL
        else:
            return GameEnum.WOLF_MODE_FIRST

    def init_game(self):
        self.status = GameEnum.GAME_STATUS_WAIT_TO_START
        self.end_time = datetime.utcnow() + timedelta(days=1)
        self.days = 0
        self.now_index = -1
        self.step_cnt = 0
        self.steps = []
        self.history = {}
        self.captain_pos = -1
        self.players = []
        self.reset_history()

    def reset_history(self):
        """
            pos: -1=no one, -2=not acted
            {
                'wolf_kill':{wolf_pos:target_pos,...},
                'wolf_kill_decision':pos,
                'elixir':True / False,
                'guard':pos,
                'toxic':pos,
                'discover':pos,
                'voter_votee':[[voter_pos,...],[votee_pos,...]],
                'vote_result': {voter_pos:votee_pos,...},
                'dying':{pos:True},
            }
        """
        self.history = {
            'wolf_kill': {},
            'wolf_kill_decision': GameEnum.TARGET_NOT_ACTED.value,
            'elixir': False,
            'guard': GameEnum.TARGET_NOT_ACTED.value,
            'toxic': GameEnum.TARGET_NOT_ACTED.value,
            'discover': GameEnum.TARGET_NOT_ACTED.value,
            'voter_votee': [[], []],
            'vote_result': {},
            'dying': {},
        }

    def get_seats_cnt(self):
        cnt = len(self.cards)
        if GameEnum.ROLE_TYPE_THIEF in self.cards:
            cnt -= 2
        return cnt
