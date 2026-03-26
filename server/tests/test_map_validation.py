"""Tests for map structure validation in generated scenarios."""

import pytest

from madaminu.services.scenario_engine import _resolve_investigation_locations


def _validate_map(scenario: dict) -> list[str]:
    """Validate map structure consistency. Returns list of error messages."""
    errors = []
    map_data = scenario.get("map")
    if map_data is None:
        errors.append("Missing 'map' in scenario")
        return errors

    locations = map_data.get("locations", [])
    connections = map_data.get("connections", [])

    location_ids = {loc["id"] for loc in locations}

    if len(location_ids) < 4:
        errors.append(f"Too few locations: {len(location_ids)} (minimum 4)")

    for loc in locations:
        if not loc.get("id"):
            errors.append(f"Location missing 'id': {loc}")
        if not loc.get("name"):
            errors.append(f"Location missing 'name': {loc}")
        if not loc.get("features"):
            errors.append(f"Location '{loc.get('id')}' has no features")

    valid_types = {"door", "corridor", "stairs", "window", "hidden_passage"}
    for conn in connections:
        if conn["from"] not in location_ids:
            errors.append(f"Connection 'from' references unknown location: {conn['from']}")
        if conn["to"] not in location_ids:
            errors.append(f"Connection 'to' references unknown location: {conn['to']}")
        if conn.get("type") and conn["type"] not in valid_types:
            errors.append(f"Unknown connection type: {conn['type']}")

    connected_ids = set()
    for conn in connections:
        connected_ids.add(conn["from"])
        connected_ids.add(conn["to"])
    isolated = location_ids - connected_ids
    for loc_id in isolated:
        errors.append(f"Isolated location (no connections): {loc_id}")

    for phase in scenario.get("phases", []):
        for loc_ref in phase.get("investigation_locations", []):
            ref_id = loc_ref if isinstance(loc_ref, str) else loc_ref.get("id")
            if ref_id not in location_ids:
                errors.append(f"Phase references unknown location: {ref_id}")

    return errors


VALID_SCENARIO = {
    "setting": {"location": "洋館", "era": "現代", "situation": "主人が殺された"},
    "victim": {"name": "山田太郎", "description": "洋館の主人"},
    "map": {
        "locations": [
            {"id": "entrance", "name": "玄関ホール", "description": "広い玄関", "features": ["シャンデリア", "コート掛け"]},
            {"id": "living_room", "name": "リビング", "description": "広いリビング", "features": ["暖炉", "ソファ", "本棚"]},
            {"id": "kitchen", "name": "キッチン", "description": "業務用キッチン", "features": ["包丁セット", "ワインセラー"]},
            {"id": "study", "name": "書斎", "description": "主人の書斎", "features": ["金庫", "デスク", "窓"]},
            {"id": "garden", "name": "庭園", "description": "広い庭園", "features": ["噴水", "花壇"]},
            {"id": "bedroom", "name": "寝室", "description": "主寝室", "features": ["ベッド", "クローゼット"]},
        ],
        "connections": [
            {"from": "entrance", "to": "living_room", "type": "door"},
            {"from": "living_room", "to": "kitchen", "type": "door"},
            {"from": "living_room", "to": "study", "type": "door"},
            {"from": "living_room", "to": "garden", "type": "window"},
            {"from": "entrance", "to": "bedroom", "type": "stairs"},
            {"from": "study", "to": "garden", "type": "window"},
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


def test_valid_scenario_passes_validation():
    errors = _validate_map(VALID_SCENARIO)
    assert errors == []


def test_missing_map():
    scenario = {**VALID_SCENARIO}
    del scenario["map"]
    errors = _validate_map(scenario)
    assert any("Missing 'map'" in e for e in errors)


def test_connection_references_unknown_location():
    scenario = {**VALID_SCENARIO, "map": {
        "locations": VALID_SCENARIO["map"]["locations"],
        "connections": [
            *VALID_SCENARIO["map"]["connections"],
            {"from": "living_room", "to": "nonexistent_room", "type": "door"},
        ],
    }}
    errors = _validate_map(scenario)
    assert any("nonexistent_room" in e for e in errors)


def test_isolated_location_detected():
    scenario = {**VALID_SCENARIO, "map": {
        "locations": [
            *VALID_SCENARIO["map"]["locations"],
            {"id": "attic", "name": "屋根裏", "description": "暗い屋根裏部屋", "features": ["古い箱"]},
        ],
        "connections": VALID_SCENARIO["map"]["connections"],
    }}
    errors = _validate_map(scenario)
    assert any("attic" in e for e in errors)


def test_phase_references_unknown_location():
    scenario = {**VALID_SCENARIO, "phases": [
        {
            "phase_type": "investigation",
            "duration_sec": 300,
            "description": "調査",
            "investigation_locations": ["living_room", "unknown_place"],
        },
    ]}
    errors = _validate_map(scenario)
    assert any("unknown_place" in e for e in errors)


def test_location_without_features():
    scenario = {**VALID_SCENARIO, "map": {
        "locations": [
            {"id": "entrance", "name": "玄関ホール", "description": "広い玄関", "features": ["シャンデリア"]},
            {"id": "living_room", "name": "リビング", "description": "広いリビング", "features": []},
            {"id": "kitchen", "name": "キッチン", "description": "業務用キッチン", "features": ["包丁"]},
            {"id": "study", "name": "書斎", "description": "主人の書斎", "features": ["金庫"]},
        ],
        "connections": [
            {"from": "entrance", "to": "living_room", "type": "door"},
            {"from": "living_room", "to": "kitchen", "type": "door"},
            {"from": "living_room", "to": "study", "type": "door"},
        ],
    }}
    errors = _validate_map(scenario)
    assert any("no features" in e for e in errors)


def test_resolve_investigation_locations_from_ids():
    map_locations = {
        "living_room": {"id": "living_room", "name": "リビング", "description": "広い", "features": ["暖炉"]},
        "kitchen": {"id": "kitchen", "name": "キッチン", "description": "広い", "features": ["包丁"]},
    }
    result = _resolve_investigation_locations(["living_room", "kitchen"], map_locations)
    assert len(result) == 2
    assert result[0]["id"] == "living_room"
    assert result[0]["name"] == "リビング"
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


def test_invalid_connection_type():
    scenario = {**VALID_SCENARIO, "map": {
        "locations": VALID_SCENARIO["map"]["locations"],
        "connections": [
            *VALID_SCENARIO["map"]["connections"],
            {"from": "living_room", "to": "kitchen", "type": "teleporter"},
        ],
    }}
    errors = _validate_map(scenario)
    assert any("teleporter" in e for e in errors)
