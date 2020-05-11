from pydantic import BaseModel
from .base import GameBase, RoleBase
from typing import Optional


class ResponseBase(BaseModel):
    code: int
    msg: str


class GameCreateOut(ResponseBase):
    gid: int


class UserInfo(BaseModel):
    nickname: str
    avatar: int
    gid: int


class UserInfoOut(ResponseBase):
    user: UserInfo


class GameInfoOut(ResponseBase):
    game: Optional[GameBase]
    role: Optional[RoleBase]
