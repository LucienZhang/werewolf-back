from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.ext.mutable import MutableDict, MutableList

from .base import Base, EnumType, JSONEncodedType
from werewolf.utils.enums import GameEnum


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

    def reset(self):
        self.role_type = GameEnum.ROLE_TYPE_UNKNOWN
        self.group_type = GameEnum.GROUP_TYPE_UNKNOWN
        self.alive = True
        # self.iscaptain = False
        self.voteable = True
        self.speakable = True
        self.position = -1
        self.skills = []
        self.tags = []
        self.args = {}

    def prepare(self, captain_mode):
        if self.role_type is GameEnum.ROLE_TYPE_SEER:
            self.group_type = GameEnum.GROUP_TYPE_GODS
        elif self.role_type is GameEnum.ROLE_TYPE_WITCH:
            self.args = {'elixir': True, 'toxic': True}
            self.group_type = GameEnum.GROUP_TYPE_GODS
        elif self.role_type is GameEnum.ROLE_TYPE_HUNTER:
            self.args = {'shootable': True}
            self.group_type = GameEnum.GROUP_TYPE_GODS
        elif self.role_type is GameEnum.ROLE_TYPE_SAVIOR:
            self.args = {'guard': GameEnum.TARGET_NO_ONE.value}
            self.group_type = GameEnum.GROUP_TYPE_GODS
        elif self.role_type is GameEnum.ROLE_TYPE_VILLAGER:
            self.group_type = GameEnum.GROUP_TYPE_VILLAGERS
        elif self.role_type is GameEnum.ROLE_TYPE_NORMAL_WOLF:
            self.group_type = GameEnum.GROUP_TYPE_WOLVES
            self.tags.append(GameEnum.TAG_ATTACKABLE_WOLF)
        elif self.role_type is GameEnum.ROLE_TYPE_IDIOT:
            self.args = {'exposed': False}
            self.group_type = GameEnum.GROUP_TYPE_GODS
        else:
            raise TypeError(f'Cannot prepare for role type {self.role_type}')

        # prepare for skills
        if self.role_type is GameEnum.ROLE_TYPE_UNKNOWN:
            self.skills = []
            return

        skills = [GameEnum.SKILL_VOTE]
        if captain_mode is GameEnum.CAPTAIN_MODE_WITH_CAPTAIN:
            skills.append(GameEnum.SKILL_CAPTAIN)

        if self.role_type is GameEnum.ROLE_TYPE_SEER:
            skills.append(GameEnum.SKILL_DISCOVER)
        if self.role_type is GameEnum.ROLE_TYPE_WITCH:
            skills.append(GameEnum.SKILL_WITCH)
        if self.role_type is GameEnum.ROLE_TYPE_HUNTER:
            skills.append(GameEnum.SKILL_SHOOT)
        if self.role_type is GameEnum.ROLE_TYPE_SAVIOR:
            skills.append(GameEnum.SKILL_GUARD)
        if GameEnum.TAG_ATTACKABLE_WOLF in self.tags:
            skills.append(GameEnum.SKILL_WOLF_KILL)
            skills.append(GameEnum.SKILL_SUICIDE)

        self.skills = skills
        return
