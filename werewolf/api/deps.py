from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from werewolf import models, schemas
from werewolf.core import security
from werewolf.core.config import settings
from werewolf.db.session import SessionLocal

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=settings.API_PREFIX + "/auth/access-token"
)


def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
        # db.commit()  commit manually for what warranted
        db.rollback()  # to ensure releasing the lock
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def get_current_user(db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)) -> models.User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])
        token_data = schemas.token.TokenPayload(**payload)
    except (jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = db.query(models.User).get(token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def get_current_active_user(current_user: models.User = Depends(get_current_user),) -> models.User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_current_active_superuser(current_user: models.User = Depends(get_current_active_user),) -> models.User:
    if not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="The user doesn't have enough privileges")
    return current_user
