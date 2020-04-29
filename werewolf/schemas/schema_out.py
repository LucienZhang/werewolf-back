from pydantic import BaseModel


class ResponseBase(BaseModel):
    code: int
    msg: str


class GameCreateOut(ResponseBase):
    gid: int
