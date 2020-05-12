from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel
from werewolf.utils.enums import GameEnum


# Shared properties
class UserBase(BaseModel):
    uid: Optional[int]
    username: Optional[str]
    nickname: Optional[str]
    avatar: Optional[int]
    gid: Optional[int]
    is_active: Optional[bool]
    is_superuser: Optional[bool]


class Player(BaseModel):
    pos: int
    nickname: str
    avatar: int


class GameBase(BaseModel):
    gid: Optional[int] = None
    host_uid: Optional[int] = None
    status: Optional[GameEnum] = None
    victoryMode: Optional[GameEnum] = None
    captainMode: Optional[GameEnum] = None
    witchMode: Optional[GameEnum] = None
    wolf_mode: Optional[GameEnum] = None
    end_time: Optional[datetime] = None
    # updated_on :Optional[]=None
    players: Optional[List[Player]] = None
    cards: Optional[Dict[GameEnum, int]] = None
    days: Optional[int] = None
    now_index: Optional[int] = None
    step_cnt: Optional[int] = None
    # steps: Optional[] = None
    # history: Optional[] = None
    captain_pos: Optional[int] = None
    seat_cnt: Optional[int] = None


class RoleBase(BaseModel):
    role_type: Optional[GameEnum] = None
    alive: Optional[bool] = None
    ishost: Optional[bool] = None
    voteable: Optional[bool] = None
    speakable: Optional[bool] = None
    skills: Optional[List[GameEnum]] = None
    nickname: Optional[str] = None
