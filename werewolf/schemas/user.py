from typing import Optional

from pydantic import BaseModel


# Shared properties
class UserBase(BaseModel):
    username: Optional[str] = None
    nickname: Optional[str] = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False


# Properties to receive via API on creation
class UserCreate(UserBase):
    username: str
    password: str
    nickname: str


# # Properties to receive via API on update
# # class UserUpdate(UserBase):
# #     password: Optional[str] = None


# class UserInDBBase(UserBase):
#     id: Optional[int] = None

#     class Config:
#         orm_mode = True


# # Additional properties to return via API
# class User(UserInDBBase):
#     pass


# # Additional properties stored in DB
# class UserInDB(UserInDBBase):
#     hashed_password: str
