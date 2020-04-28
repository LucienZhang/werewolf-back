from fastapi import FastAPI

from werewolf.api import api_router
from werewolf.core.config import settings

app = FastAPI()

app.include_router(api_router, prefix=settings.API_PREFIX)

# from werewolf.api.deps import get_current_active_user
# from fastapi import Depends
# from werewolf.models import User
# @app.get("/users/me")
# async def read_items(current_user: User = Depends(get_current_active_user)):
#     return {"gid": current_user.gid}
