from typing import Optional
from .base import UserBase, GameBase


class UserCreate(UserBase):
    username: str
    password: str
    nickname: str
    avatar: Optional[int] = 1
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
