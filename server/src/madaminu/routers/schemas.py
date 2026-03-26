from pydantic import BaseModel, Field


class CreateRoomRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=50)
    password: str | None = None


class CreateRoomResponse(BaseModel):
    room_code: str
    player_id: str
    session_token: str


class JoinRoomRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=50)
    password: str | None = None


class JoinRoomResponse(BaseModel):
    player_id: str
    session_token: str


class PlayerInfo(BaseModel):
    id: str
    display_name: str
    character_name: str | None = None
    is_host: bool
    connection_status: str


class CreateCharacterRequest(BaseModel):
    character_name: str = Field(..., min_length=1, max_length=50)
    character_gender: str = Field(default="不明", max_length=10)
    character_age: str = Field(default="不明", max_length=10)
    character_occupation: str = Field(default="", max_length=100)
    character_appearance: str = Field(default="", max_length=500)
    character_personality: str = Field(..., min_length=1, max_length=500)
    character_background: str = Field(..., min_length=1, max_length=1000)


class CharacterResponse(BaseModel):
    player_id: str
    character_name: str
    character_gender: str | None = None
    character_age: str | None = None
    character_occupation: str | None = None
    character_appearance: str | None = None
    character_personality: str
    character_background: str


class RoomInfoResponse(BaseModel):
    room_code: str
    status: str
    players: list[PlayerInfo]
    host_player_id: str | None
    has_password: bool = False


class RoomListItem(BaseModel):
    room_code: str
    status: str
    player_count: int
    host_name: str | None = None
    has_password: bool = False
