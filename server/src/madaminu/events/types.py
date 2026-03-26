from dataclasses import dataclass


@dataclass
class GameStarted:
    game_id: str
    room_code: str


@dataclass
class ScenarioReady:
    game_id: str
    room_code: str


@dataclass
class ImagesReady:
    game_id: str
    room_code: str


@dataclass
class PhaseAdvanced:
    game_id: str
    room_code: str
    ended_phase_id: str


@dataclass
class GameEnded:
    game_id: str
    room_code: str
