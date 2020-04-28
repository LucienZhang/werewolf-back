# from datetime import datetime
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.ext.mutable import MutableDict, MutableList

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
