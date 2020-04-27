from fastapi import FastAPI

from werewolf.api import api_router
from werewolf.core.config import settings

app = FastAPI()

app.include_router(api_router, prefix=settings.API_PREFIX)
