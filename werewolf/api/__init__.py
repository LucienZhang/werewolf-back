from fastapi import APIRouter

from . import auth, user, game

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(user.router, prefix="/user", tags=["user"])
api_router.include_router(game.router, prefix="/game", tags=["game"])
# api_router.include_router(skill.router, prefix="/skill", tags=["skill"])
# api_router.include_router(utils.router, prefix="/utils", tags=["utils"])
# api_router.include_router(items.router, prefix="/items", tags=["items"])
