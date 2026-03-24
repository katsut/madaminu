from pydantic import BaseModel


class WSMessage(BaseModel):
    type: str
    data: dict = {}


class PlayerConnectedData(BaseModel):
    player_id: str
    display_name: str


class PlayerDisconnectedData(BaseModel):
    player_id: str
    display_name: str
