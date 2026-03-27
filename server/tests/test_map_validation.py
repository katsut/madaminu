"""Tests for map structure validation."""

from madaminu.services.map_validator import validate_map
from madaminu.services.scenario_engine import _resolve_investigation_locations


VALID_SCENARIO = {
    "map": {
        "areas": [
            {
                "id": "main_1f", "name": "本館1階", "area_type": "indoor",
                "rooms": [
                    {"id": "entrance", "name": "玄関", "features": ["鏡"]},
                    {"id": "living", "name": "リビング", "features": ["暖炉"]},
                    {"id": "kitchen", "name": "台所", "features": ["包丁"]},
                ],
            },
            {
                "id": "main_2f", "name": "本館2階", "area_type": "indoor",
                "rooms": [
                    {"id": "hallway", "name": "廊下", "features": ["窓"]},
                    {"id": "bedroom", "name": "寝室", "features": ["ベッド"]},
                ],
            },
        ],
        "connections": [
            {"from": "entrance", "to": "living", "type": "door"},
            {"from": "living", "to": "kitchen", "type": "door"},
            {"from": "entrance", "to": "hallway", "type": "stairs"},
            {"from": "hallway", "to": "bedroom", "type": "door"},
        ],
    },
    "phases": [
        {"phase_type": "investigation", "investigation_locations": ["living", "kitchen", "bedroom"]},
        {"phase_type": "discussion"},
        {"phase_type": "voting"},
    ],
}


def test_valid_scenario():
    assert validate_map(VALID_SCENARIO) == []


def test_missing_map():
    assert any("Missing" in e for e in validate_map({}))


def test_unknown_connection_from():
    s = {**VALID_SCENARIO, "map": {
        **VALID_SCENARIO["map"],
        "connections": [*VALID_SCENARIO["map"]["connections"], {"from": "xxx", "to": "living", "type": "door"}],
    }}
    assert any("xxx" in e for e in validate_map(s))


def test_unknown_connection_to():
    s = {**VALID_SCENARIO, "map": {
        **VALID_SCENARIO["map"],
        "connections": [*VALID_SCENARIO["map"]["connections"], {"from": "living", "to": "yyy", "type": "door"}],
    }}
    assert any("yyy" in e for e in validate_map(s))


def test_invalid_connection_type():
    s = {**VALID_SCENARIO, "map": {
        **VALID_SCENARIO["map"],
        "connections": [{"from": "entrance", "to": "living", "type": "teleport"}],
    }}
    assert any("teleport" in e for e in validate_map(s))


def test_isolated_room():
    areas = [
        *VALID_SCENARIO["map"]["areas"],
        {"id": "shed", "name": "物置", "area_type": "indoor", "rooms": [{"id": "attic", "name": "屋根裏", "features": ["箱"]}]},
    ]
    s = {**VALID_SCENARIO, "map": {"areas": areas, "connections": VALID_SCENARIO["map"]["connections"]}}
    assert any("attic" in e for e in validate_map(s))


def test_duplicate_room_id():
    areas = [
        {"id": "a1", "name": "A", "area_type": "indoor", "rooms": [
            {"id": "room1", "name": "R1", "features": ["x"]},
            {"id": "room2", "name": "R2", "features": ["x"]},
        ]},
        {"id": "a2", "name": "B", "area_type": "indoor", "rooms": [
            {"id": "room1", "name": "R1 dup", "features": ["x"]},
            {"id": "room3", "name": "R3", "features": ["x"]},
        ]},
    ]
    s = {"map": {"areas": areas, "connections": [
        {"from": "room1", "to": "room2", "type": "door"},
        {"from": "room1", "to": "room3", "type": "door"},
    ]}, "phases": []}
    assert any("Duplicate" in e for e in validate_map(s))


def test_room_without_features():
    areas = [{"id": "a", "name": "A", "area_type": "indoor", "rooms": [
        {"id": "r1", "name": "R1", "features": []},
        {"id": "r2", "name": "R2", "features": ["x"]},
        {"id": "r3", "name": "R3", "features": ["x"]},
        {"id": "r4", "name": "R4", "features": ["x"]},
    ]}]
    s = {"map": {"areas": areas, "connections": [
        {"from": "r1", "to": "r2", "type": "door"},
        {"from": "r2", "to": "r3", "type": "door"},
        {"from": "r3", "to": "r4", "type": "door"},
    ]}, "phases": []}
    assert any("no features" in e for e in validate_map(s))


def test_invalid_area_type():
    areas = [{"id": "a", "name": "A", "area_type": "underwater", "rooms": [
        {"id": "r1", "name": "R1", "features": ["x"]},
        {"id": "r2", "name": "R2", "features": ["x"]},
        {"id": "r3", "name": "R3", "features": ["x"]},
        {"id": "r4", "name": "R4", "features": ["x"]},
    ]}]
    s = {"map": {"areas": areas, "connections": [
        {"from": "r1", "to": "r2", "type": "door"},
        {"from": "r2", "to": "r3", "type": "door"},
        {"from": "r3", "to": "r4", "type": "door"},
    ]}, "phases": []}
    assert any("underwater" in e for e in validate_map(s))


def test_phase_references_unknown_room():
    s = {**VALID_SCENARIO, "phases": [
        {"phase_type": "investigation", "investigation_locations": ["living", "nonexistent"]},
    ]}
    assert any("nonexistent" in e for e in validate_map(s))


def test_too_few_rooms():
    areas = [{"id": "a", "name": "A", "area_type": "indoor", "rooms": [
        {"id": "r1", "name": "R1", "features": ["x"]},
    ]}]
    s = {"map": {"areas": areas, "connections": []}, "phases": []}
    errors = validate_map(s)
    assert any("Too few" in e for e in errors)


def test_empty_area():
    areas = [
        {"id": "a", "name": "A", "area_type": "indoor", "rooms": []},
        *VALID_SCENARIO["map"]["areas"],
    ]
    s = {**VALID_SCENARIO, "map": {"areas": areas, "connections": VALID_SCENARIO["map"]["connections"]}}
    assert any("no rooms" in e for e in validate_map(s))


# --- Resolve investigation locations ---

def test_resolve_from_hierarchical():
    rooms = {
        "living": {"id": "living", "name": "リビング", "features": ["暖炉"]},
        "kitchen": {"id": "kitchen", "name": "台所", "features": ["包丁"]},
    }
    result = _resolve_investigation_locations(["living", "kitchen"], rooms)
    assert len(result) == 2
    assert result[0]["name"] == "リビング"
    assert result[0]["features"] == ["暖炉"]


def test_resolve_skips_unknown():
    assert _resolve_investigation_locations(["nonexistent"], {}) == []


def test_resolve_from_dict():
    result = _resolve_investigation_locations([{"id": "r1", "name": "部屋", "description": "d"}], {})
    assert len(result) == 1
    assert result[0]["id"] == "r1"
