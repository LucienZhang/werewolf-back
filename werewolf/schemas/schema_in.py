from typing import Optional, List
from pydantic import BaseModel
from werewolf.utils.enums import GameEnum
# from .base import UserBase, GameBase


class UserCreateIn(BaseModel):
    username: str
    password: str
    nickname: str
    avatar: Optional[int] = 1
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False


class GameCreateIn(BaseModel):
    victoryMode: GameEnum
    captainMode: GameEnum
    witchMode: GameEnum
    villagerCnt: int
    normalWolfCnt: int
    selectedGods: List[GameEnum]
    selectedWolves: List[GameEnum]
