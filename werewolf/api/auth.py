from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from werewolf.models import User
from werewolf.schemas.token import Token
from . import deps
from werewolf.core import security
from werewolf.core.config import settings
# from werewolf.utils import (
#     generate_password_reset_token,
#     send_reset_password_email,
#     verify_password_reset_token,
# )

router = APIRouter()


@router.post("/access-token", response_model=Token)
def login_access_token(db: Session = Depends(deps.get_db), form_data: OAuth2PasswordRequestForm = Depends()) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user:
        raise HTTPException(status_code=422, detail="Incorrect email or password")
    if not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=422, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=422, detail="Inactive user")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.uid, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


# @router.post("/login/test-token", response_model=schemas.User)
# def test_token(current_user: models.User = Depends(deps.get_current_user)) -> Any:
#     """
#     Test access token
#     """
#     return current_user


# @router.post("/password-recovery/{email}", response_model=schemas.Msg)
# def recover_password(email: str, db: Session = Depends(deps.get_db)) -> Any:
#     """
#     Password Recovery
#     """
#     user = crud.user.get_by_email(db, email=email)

#     if not user:
#         raise HTTPException(
#             status_code=404,
#             detail="The user with this username does not exist in the system.",
#         )
#     password_reset_token = generate_password_reset_token(email=email)
#     send_reset_password_email(
#         email_to=user.email, email=email, token=password_reset_token
#     )
#     return {"msg": "Password recovery email sent"}


# @router.post("/reset-password/", response_model=schemas.Msg)
# def reset_password(
#     token: str = Body(...),
#     new_password: str = Body(...),
#     db: Session = Depends(deps.get_db),
# ) -> Any:
#     """
#     Reset password
#     """
#     email = verify_password_reset_token(token)
#     if not email:
#         raise HTTPException(status_code=400, detail="Invalid token")
#     user = crud.user.get_by_email(db, email=email)
#     if not user:
#         raise HTTPException(
#             status_code=404,
#             detail="The user with this username does not exist in the system.",
#         )
#     elif not crud.user.is_active(user):
#         raise HTTPException(status_code=400, detail="Inactive user")
#     hashed_password = security.get_password_hash(new_password)
#     user.hashed_password = hashed_password
#     db.add(user)
#     db.commit()
#     return {"msg": "Password updated successfully"}
