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


class PhaseStartedData(BaseModel):
    phase_id: str
    phase_type: str
    phase_order: int
    total_phases: int
    duration_sec: int
    turn_number: int = 1
    total_turns: int = 3
    investigation_locations: list[dict] | None = None


class PhaseTimerData(BaseModel):
    phase_id: str
    remaining_sec: int


class PhaseEndedData(BaseModel):
    phase_id: str
    phase_type: str
    next_phase_type: str | None = None


class SpeechActiveData(BaseModel):
    player_id: str


class SpeechReleasedData(BaseModel):
    player_id: str
