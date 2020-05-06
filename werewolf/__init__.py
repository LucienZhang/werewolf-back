from fastapi import FastAPI

from werewolf.api import api_router
# from werewolf.api.websocket import broadcaster, init_websocket
from werewolf.core.config import settings


app = FastAPI()
app.include_router(api_router, prefix=settings.API_PREFIX)

# init_websocket(app)


# @app.on_event("startup")
# async def startup_event():
#     await broadcaster.connect()


# @app.on_event("shutdown")
# async def shutdown_event():
#     await broadcaster.disconnect()


# ###
# # test
# ###

# from starlette.templating import Jinja2Templates
# templates = Jinja2Templates("templates")


# @app.get("/test")
# async def test(request: Request):
#     template = "index.html"
#     context = {"request": request}
#     return templates.TemplateResponse(template, context)


# @app.get("/send/{msg}")
# async def send(msg: str):
#     import json
#     message = json.dumps({"action": 'message', "user": "god", "message": msg})
#     await broadcaster.publish(channel="chatroom", message=message)

# from werewolf.api.deps import get_current_active_user
# from fastapi import Depends
# from werewolf.models import User
# @app.get("/users/me")
# async def read_items(current_user: User = Depends(get_current_active_user)):
#     return {"gid": current_user.gid}
