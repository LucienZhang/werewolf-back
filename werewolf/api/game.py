from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
# from sqlalchemy.exc import IntegrityError

from werewolf import schemas
# from werewolf.models import User
from werewolf.api import deps
# from werewolf.core.config import settings
from werewolf.utils.enums import GameEnum

router = APIRouter()

# @router.post("/create")




# @router.post("/register", response_model=schemas.ResponseBase)
# def create_user(
#     *,
#     db: Session = Depends(deps.get_db),
#     user_in: schemas.UserCreate,
#     current_user: User = Depends(deps.get_current_active_user),
# ) -> Any:
#     """
#     Create new user.
#     """
#     new_user = User(username=user_in.username, hashed_password=get_password_hash(user_in.password),
#                     nickname=user_in.nickname, avatar=1, gid=-1)
#     try:
#         db.add(new_user)
#         db.commit()
#     except IntegrityError:
#         raise HTTPException(
#             status_code=400,
#             detail="The user with this username already exists in the system.",
#         )

#     return GameEnum.OK.digest()
