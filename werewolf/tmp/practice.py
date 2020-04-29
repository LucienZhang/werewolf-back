from sqlalchemy import create_engine
engine = create_engine('sqlite:///:memory:', echo=True)

from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import Column, Integer, String, Boolean


class MySQLBase(object):
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8', 'mysql_collate': 'utf8_general_ci'}


Base = declarative_base(cls=MySQLBase)


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


class Game(Base):
    gid = Column(Integer, primary_key=True, autoincrement=True)


Base.metadata.create_all(engine)
# new_user = User(username='test', hashed_password='test', nickname='test', avatar=1, gid=1)
# new_game = Game()

from sqlalchemy.orm import sessionmaker
Session = sessionmaker(bind=engine)
s = Session()
# s.add(new_user)
# s.add(new_game)
# s.commit()
# u2 = User(username='test', hashed_password='test', nickname='test', avatar=1, gid=1)
# s.add(u2)
# s.commit()

from pydantic import BaseModel
from typing import Optional


class UserBase(BaseModel):
    uid: Optional[int]
    username: Optional[str]
    nickname: Optional[str]
    avatar: Optional[int]
    gid: Optional[int]
    is_active: Optional[bool]
    is_superuser: Optional[bool]


class UserCreate(UserBase):
    username: str
    password: str
    nickname: str
    avatar: Optional[int] = 1
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False


u3 = User(**UserCreate(username="mytest",
                       password="mytest",
                       nickname="mytest").dict())
u3.hashed_password = '123123'
s.add(u3)
s.commit()
print(u3.uid, u3.password)

# print(new_user.uid)
# print('---after addition')
# u1 = s.query(User).get(1)
# u1.nickname = 'something else'
# g1 = s.query(Game).get(1)
# print(u1.nickname)
# s.rollback()
# print('rollback')
# print(u1.nickname)
# u2 = s.query(User).get(1)
# print(u2.nickname)


# print(dir(Base.metadata.tables))
# print(Base.metadata.tables)
