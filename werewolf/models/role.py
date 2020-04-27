from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.ext.mutable import MutableDict, MutableList

from .base import Base, EnumType, JSONEncodedType


class Role(Base):
    uid = Column(Integer, primary_key=True)
    gid = Column(Integer, nullable=False, index=True)  # gid=-1 means not in game
    nickname = Column(String(length=255), nullable=False)
    avatar = Column(Integer, nullable=False)
    role_type = Column(EnumType, nullable=False)
    group_type = Column(EnumType, nullable=False)
    alive = Column(Boolean, nullable=False)
    # iscaptain = Column(Boolean, nullable=False)
    voteable = Column(Boolean, nullable=False)
    speakable = Column(Boolean, nullable=False)
    position = Column(Integer, nullable=False)
    skills = Column(MutableList.as_mutable(JSONEncodedType(255)), nullable=False)
    tags = Column(MutableList.as_mutable(JSONEncodedType(255)), nullable=False)
    args = Column(MutableDict.as_mutable(JSONEncodedType(255)), nullable=False)
