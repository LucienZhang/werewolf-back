from sqlalchemy import Column, Integer, String, Boolean

from .base import Base


class User(Base):
    uid = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(length=255),
                      nullable=False, unique=True, index=True)
    hashed_password = Column(String(length=255), nullable=False)
    # login_token = Column(String(length=255), nullable=False, index=True)
    nickname = Column(String(length=255), nullable=False)
    avatar = Column(Integer, nullable=False)
    gid = Column(Integer, nullable=False)  # gid=-1 means not in game
    is_active = Column(Boolean, nullable=False, default=True)
    is_superuser = Column(Boolean, nullable=False, default=False)
