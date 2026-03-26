"""Tests for map structure validation in generated scenarios."""

import pytest

from madaminu.services.map_validator import validate_map, _get_grid_cells, _are_adjacent
from madaminu.services.scenario_engine import _resolve_investigation_locations


# --- Fixtures ---

VALID_SCENARIO = {
    "setting": {"location": "洋館", "era": "現代", "situation": "主人が殺された"},
    "victim": {"name": "山田太郎", "description": "洋館の主人"},
    "map": {
        "locations": [
            {"id": "garden", "name": "庭園", "description": "広い庭園", "area_type": "outdoor", "x": 0, "y": 0, "w": 4, "h": 1, "features": ["噴水", "花壇"]},
            {"id": "entrance", "name": "玄関ホール", "description": "広い玄関", "area_type": "indoor", "x": 1, "y": 1, "w": 1, "h": 1, "features": ["シャンデリア", "コート掛け"]},
            {"id": "living_room", "name": "リビング", "description": "広いリビング", "area_type": "indoor", "x": 0, "y": 1, "w": 1, "h": 1, "features": ["暖炉", "ソファ", "本棚"]},
            {"id": "kitchen", "name": "キッチン", "description": "業務用キッチン", "area_type": "indoor", "x": 2, "y": 1, "w": 1, "h": 1, "features": ["包丁セット", "ワインセラー"]},
            {"id": "study", "name": "書斎", "description": "主人の書斎", "area_type": "indoor", "x": 3, "y": 1, "w": 1, "h": 1, "features": ["金庫", "デスク"]},
            {"id": "bedroom", "name": "寝室", "description": "主寝室", "area_type": "indoor", "x": 0, "y": 2, "w": 1, "h": 1, "features": ["ベッド", "クローゼット"]},
        ],
        "connections": [
            {"from": "entrance", "to": "living_room", "type": "door", "side": "west"},
            {"from": "entrance", "to": "kitchen", "type": "door", "side": "east"},
            {"from": "kitchen", "to": "study", "type": "door", "side": "east"},
            {"from": "living_room", "to": "garden", "type": "window", "side": "north"},
            {"from": "living_room", "to": "bedroom", "type": "stairs", "side": "south"},
            {"from": "entrance", "to": "garden", "type": "door", "side": "north"},
        ],
    },
    "relationships": [],
    "players": [],
    "phases": [
        {
            "phase_type": "investigation",
            "duration_sec": 300,
            "description": "調査",
            "investigation_locations": ["living_room", "kitchen", "study", "garden"],
        },
        {"phase_type": "discussion", "duration_sec": 300, "description": "議論"},
        {"phase_type": "voting", "duration_sec": 180, "description": "投票"},
    ],
    "gm_strategy": "test",
}


def _make_scenario(**overrides):
    """Helper to create a scenario with overrides."""
    s = {**VALID_SCENARIO}
    for k, v in overrides.items():
        s[k] = v
    return s


def _make_map(**overrides):
    """Helper to create a scenario with map overrides."""
    m = {**VALID_SCENARIO["map"]}
    for k, v in overrides.items():
        m[k] = v
    return _make_scenario(map=m)


# --- Basic validation tests ---

def test_valid_scenario_passes_validation():
    errors = validate_map(VALID_SCENARIO)
    assert errors == []


def test_missing_map():
    scenario = {k: v for k, v in VALID_SCENARIO.items() if k != "map"}
    errors = validate_map(scenario)
    assert any("Missing 'map'" in e for e in errors)


def test_too_few_locations():
    scenario = _make_map(locations=[
        {"id": "a", "name": "A", "description": "a", "features": ["x"], "x": 0, "y": 0, "w": 1, "h": 1},
        {"id": "b", "name": "B", "description": "b", "features": ["x"], "x": 1, "y": 0, "w": 1, "h": 1},
    ], connections=[{"from": "a", "to": "b", "type": "door"}])
    errors = validate_map(scenario)
    assert any("Too few" in e for e in errors)


def test_connection_references_unknown_location():
    scenario = _make_map(connections=[
        *VALID_SCENARIO["map"]["connections"],
        {"from": "living_room", "to": "nonexistent_room", "type": "door"},
    ])
    errors = validate_map(scenario)
    assert any("nonexistent_room" in e for e in errors)


def test_isolated_location_detected():
    scenario = _make_map(locations=[
        *VALID_SCENARIO["map"]["locations"],
        {"id": "attic", "name": "屋根裏", "description": "暗い", "features": ["古い箱"], "x": 0, "y": 3, "w": 1, "h": 1},
    ])
    errors = validate_map(scenario)
    assert any("attic" in e for e in errors)


def test_phase_references_unknown_location():
    scenario = _make_scenario(phases=[{
        "phase_type": "investigation",
        "duration_sec": 300,
        "description": "調査",
        "investigation_locations": ["living_room", "unknown_place"],
    }])
    errors = validate_map(scenario)
    assert any("unknown_place" in e for e in errors)


def test_location_without_features():
    locs = [dict(loc) for loc in VALID_SCENARIO["map"]["locations"]]
    locs[1] = {**locs[1], "features": []}
    scenario = _make_map(locations=locs)
    errors = validate_map(scenario)
    assert any("no features" in e for e in errors)


def test_invalid_connection_type():
    scenario = _make_map(connections=[
        *VALID_SCENARIO["map"]["connections"],
        {"from": "living_room", "to": "entrance", "type": "teleporter"},
    ])
    errors = validate_map(scenario)
    assert any("teleporter" in e for e in errors)


def test_invalid_area_type():
    locs = [dict(loc) for loc in VALID_SCENARIO["map"]["locations"]]
    locs[0] = {**locs[0], "area_type": "underwater"}
    scenario = _make_map(locations=locs)
    errors = validate_map(scenario)
    assert any("underwater" in e for e in errors)


def test_invalid_connection_side():
    scenario = _make_map(connections=[
        {"from": "entrance", "to": "living_room", "type": "door", "side": "diagonal"},
    ])
    errors = validate_map(scenario)
    assert any("diagonal" in e for e in errors)


# --- Grid overlap tests ---

def test_no_overlap_in_valid_scenario():
    errors = validate_map(VALID_SCENARIO)
    assert not any("overlap" in e.lower() for e in errors)


def test_grid_overlap_detected():
    locs = [
        {"id": "room_a", "name": "A", "description": "a", "features": ["x"], "x": 0, "y": 0, "w": 2, "h": 1},
        {"id": "room_b", "name": "B", "description": "b", "features": ["x"], "x": 1, "y": 0, "w": 2, "h": 1},
        {"id": "room_c", "name": "C", "description": "c", "features": ["x"], "x": 3, "y": 0, "w": 1, "h": 1},
        {"id": "room_d", "name": "D", "description": "d", "features": ["x"], "x": 0, "y": 1, "w": 1, "h": 1},
    ]
    scenario = _make_map(
        locations=locs,
        connections=[
            {"from": "room_a", "to": "room_b", "type": "door"},
            {"from": "room_b", "to": "room_c", "type": "door"},
            {"from": "room_a", "to": "room_d", "type": "door"},
        ],
    )
    errors = validate_map(scenario)
    assert any("overlap" in e.lower() for e in errors)


def test_large_room_no_overlap():
    locs = [
        {"id": "hall", "name": "ホール", "description": "大広間", "features": ["柱", "絵画"], "x": 0, "y": 0, "w": 2, "h": 2},
        {"id": "room_a", "name": "A", "description": "a", "features": ["x"], "x": 2, "y": 0, "w": 1, "h": 1},
        {"id": "room_b", "name": "B", "description": "b", "features": ["x"], "x": 2, "y": 1, "w": 1, "h": 1},
        {"id": "room_c", "name": "C", "description": "c", "features": ["x"], "x": 0, "y": 2, "w": 1, "h": 1},
    ]
    scenario = _make_map(
        locations=locs,
        connections=[
            {"from": "hall", "to": "room_a", "type": "door"},
            {"from": "hall", "to": "room_b", "type": "door"},
            {"from": "hall", "to": "room_c", "type": "door"},
        ],
    )
    errors = validate_map(scenario)
    assert not any("overlap" in e.lower() for e in errors)


# --- Adjacency tests ---

def test_non_adjacent_connection_detected():
    locs = [
        {"id": "room_a", "name": "A", "description": "a", "features": ["x"], "x": 0, "y": 0, "w": 1, "h": 1},
        {"id": "room_b", "name": "B", "description": "b", "features": ["x"], "x": 3, "y": 3, "w": 1, "h": 1},
        {"id": "room_c", "name": "C", "description": "c", "features": ["x"], "x": 1, "y": 0, "w": 1, "h": 1},
        {"id": "room_d", "name": "D", "description": "d", "features": ["x"], "x": 2, "y": 0, "w": 1, "h": 1},
    ]
    scenario = _make_map(
        locations=locs,
        connections=[
            {"from": "room_a", "to": "room_b", "type": "door"},
            {"from": "room_a", "to": "room_c", "type": "door"},
            {"from": "room_c", "to": "room_d", "type": "door"},
        ],
    )
    errors = validate_map(scenario)
    assert any("not adjacent" in e for e in errors)
    # room_a to room_c should be fine (adjacent)
    assert not any("room_a" in e and "room_c" in e for e in errors)


def test_stairs_skip_adjacency_check():
    locs = [
        {"id": "floor1", "name": "1F", "description": "1階", "features": ["x"], "x": 0, "y": 0, "w": 1, "h": 1},
        {"id": "floor2", "name": "2F", "description": "2階", "features": ["x"], "x": 0, "y": 5, "w": 1, "h": 1},
        {"id": "room_c", "name": "C", "description": "c", "features": ["x"], "x": 1, "y": 0, "w": 1, "h": 1},
        {"id": "room_d", "name": "D", "description": "d", "features": ["x"], "x": 1, "y": 5, "w": 1, "h": 1},
    ]
    scenario = _make_map(
        locations=locs,
        connections=[
            {"from": "floor1", "to": "floor2", "type": "stairs"},
            {"from": "floor1", "to": "room_c", "type": "door"},
            {"from": "floor2", "to": "room_d", "type": "door"},
        ],
    )
    errors = validate_map(scenario)
    assert not any("not adjacent" in e for e in errors)


# --- Helper function tests ---

def test_get_grid_cells():
    loc = {"x": 1, "y": 2, "w": 2, "h": 3}
    cells = _get_grid_cells(loc)
    assert cells == {(1, 2), (2, 2), (1, 3), (2, 3), (1, 4), (2, 4)}


def test_get_grid_cells_1x1():
    cells = _get_grid_cells({"x": 0, "y": 0, "w": 1, "h": 1})
    assert cells == {(0, 0)}


def test_are_adjacent_true():
    a = {"x": 0, "y": 0, "w": 1, "h": 1}
    b = {"x": 1, "y": 0, "w": 1, "h": 1}
    assert _are_adjacent(a, b) is True


def test_are_adjacent_false():
    a = {"x": 0, "y": 0, "w": 1, "h": 1}
    b = {"x": 3, "y": 3, "w": 1, "h": 1}
    assert _are_adjacent(a, b) is False


def test_are_adjacent_large_room():
    a = {"x": 0, "y": 0, "w": 3, "h": 1}
    b = {"x": 1, "y": 1, "w": 1, "h": 1}
    assert _are_adjacent(a, b) is True


def test_are_adjacent_diagonal_is_false():
    a = {"x": 0, "y": 0, "w": 1, "h": 1}
    b = {"x": 1, "y": 1, "w": 1, "h": 1}
    assert _are_adjacent(a, b) is False


# --- Resolve investigation locations tests ---

def test_resolve_investigation_locations_from_ids():
    map_locations = {
        "living_room": {"id": "living_room", "name": "リビング", "description": "広い", "features": ["暖炉"]},
        "kitchen": {"id": "kitchen", "name": "キッチン", "description": "広い", "features": ["包丁"]},
    }
    result = _resolve_investigation_locations(["living_room", "kitchen"], map_locations)
    assert len(result) == 2
    assert result[0]["id"] == "living_room"
    assert result[0]["features"] == ["暖炉"]


def test_resolve_investigation_locations_from_dicts():
    result = _resolve_investigation_locations(
        [{"id": "room1", "name": "部屋1", "description": "desc"}],
        {},
    )
    assert len(result) == 1
    assert result[0]["id"] == "room1"


def test_resolve_investigation_locations_skips_unknown_ids():
    result = _resolve_investigation_locations(["nonexistent"], {})
    assert result == []
