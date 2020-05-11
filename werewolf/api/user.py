from typing import Any

from fastapi import APIRouter, Depends, HTTPException
# from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from werewolf.schemas import schema_in, schema_out
from werewolf.models import User, Role
from werewolf.api import deps
# from werewolf.core.config import settings
from werewolf.core.security import get_password_hash
from werewolf.utils.enums import GameEnum

router = APIRouter()


# @router.get("/", response_model=List[schemas.User])
# def read_users(
#     db: Session = Depends(deps.get_db),
#     skip: int = 0,
#     limit: int = 100,
#     current_user: models.User = Depends(deps.get_current_active_superuser),
# ) -> Any:
#     """
#     Retrieve users.
#     """
#     users = crud.user.get_multi(db, skip=skip, limit=limit)
#     return users


@router.post("/create", response_model=schema_out.ResponseBase)
def create_user(
    *,
    db: Session = Depends(deps.get_db),
    user_in: schema_in.UserCreateIn,
) -> Any:
    """
    Create new user.
    """
    new_user = User(**{k: v for k, v in user_in.dict().items() if k != 'password'})
    new_user.hashed_password = get_password_hash(user_in.password)
    new_user.gid = -1
    try:
        db.add(new_user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )

    new_role = Role(uid=new_user.uid, nickname=new_user.nickname, avatar=new_user.avatar, gid=-1)
    new_role.reset()
    db.add(new_role)
    db.commit()

    return GameEnum.OK.digest()


@router.get("/check_username", response_model=schema_out.ResponseBase)
def check_username(
    *,
    db: Session = Depends(deps.get_db),
    username: str,
):
    user = db.query(User.uid).filter_by(username=username).first()
    if user:
        return GameEnum.GAME_MESSAGE_USER_EXISTS.digest()
    else:
        return GameEnum.OK.digest()


@router.get("/info", response_model=schema_out.UserInfoOut)
def info(
    *,
    current_user: User = Depends(deps.get_current_active_user),
):
    info = {
        'nickname': current_user.nickname,
        'avatar': current_user.avatar,
        'gid': current_user.gid
    }
    return GameEnum.OK.digest(user=info)

# @router.put("/me", response_model=schemas.User)
# def update_user_me(
#     *,
#     db: Session = Depends(deps.get_db),
#     password: str = Body(None),
#     full_name: str = Body(None),
#     email: EmailStr = Body(None),
#     current_user: models.User = Depends(deps.get_current_active_user),
# ) -> Any:
#     """
#     Update own user.
#     """
#     current_user_data = jsonable_encoder(current_user)
#     user_in = schemas.UserUpdate(**current_user_data)
#     if password is not None:
#         user_in.password = password
#     if full_name is not None:
#         user_in.full_name = full_name
#     if email is not None:
#         user_in.email = email
#     user = crud.user.update(db, db_obj=current_user, obj_in=user_in)
#     return user


# @router.get("/me", response_model=schemas.User)
# def read_user_me(
#     db: Session = Depends(deps.get_db),
#     current_user: models.User = Depends(deps.get_current_active_user),
# ) -> Any:
#     """
#     Get current user.
#     """
#     return current_user


# @router.post("/open", response_model=schemas.User)
# def create_user_open(
#     *,
#     db: Session = Depends(deps.get_db),
#     password: str = Body(...),
#     email: EmailStr = Body(...),
#     full_name: str = Body(None),
# ) -> Any:
#     """
#     Create new user without the need to be logged in.
#     """
#     if not settings.USERS_OPEN_REGISTRATION:
#         raise HTTPException(
#             status_code=403,
#             detail="Open user registration is forbidden on this server",
#         )
#     user = crud.user.get_by_email(db, email=email)
#     if user:
#         raise HTTPException(
#             status_code=400,
#             detail="The user with this username already exists in the system",
#         )
#     user_in = schemas.UserCreate(password=password, email=email, full_name=full_name)
#     user = crud.user.create(db, obj_in=user_in)
#     return user


# @router.get("/{user_id}", response_model=schemas.User)
# def read_user_by_id(
#     user_id: int,
#     current_user: models.User = Depends(deps.get_current_active_user),
#     db: Session = Depends(deps.get_db),
# ) -> Any:
#     """
#     Get a specific user by id.
#     """
#     user = crud.user.get(db, id=user_id)
#     if user == current_user:
#         return user
#     if not crud.user.is_superuser(current_user):
#         raise HTTPException(
#             status_code=400, detail="The user doesn't have enough privileges"
#         )
#     return user


# @router.put("/{user_id}", response_model=schemas.User)
# def update_user(
#     *,
#     db: Session = Depends(deps.get_db),
#     user_id: int,
#     user_in: schemas.UserUpdate,
#     current_user: models.User = Depends(deps.get_current_active_superuser),
# ) -> Any:
#     """
#     Update a user.
#     """
#     user = crud.user.get(db, id=user_id)
#     if not user:
#         raise HTTPException(
#             status_code=404,
#             detail="The user with this username does not exist in the system",
#         )
#     user = crud.user.update(db, db_obj=user, obj_in=user_in)
#     return user
