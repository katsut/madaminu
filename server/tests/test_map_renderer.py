"""Tests for SVG map renderer."""

from madaminu.services.map_renderer import render_map_svg


HIERARCHICAL_MAP = {
    "areas": [
        {
            "id": "main_1f", "name": "本館1階", "area_type": "indoor",
            "rooms": [
                {"id": "entrance", "name": "玄関", "features": ["鏡", "傘立て"]},
                {"id": "living", "name": "リビング", "features": ["暖炉", "ソファ"]},
                {"id": "kitchen", "name": "台所", "features": ["包丁"]},
            ],
        },
        {
            "id": "main_2f", "name": "本館2階", "area_type": "indoor",
            "rooms": [
                {"id": "hallway_2f", "name": "2階廊下", "features": ["窓"]},
                {"id": "bedroom", "name": "寝室", "features": ["ベッド"]},
            ],
        },
        {
            "id": "outside", "name": "屋外", "area_type": "outdoor",
            "rooms": [
                {"id": "garden", "name": "庭園", "features": ["噴水"]},
            ],
        },
    ],
    "connections": [
        {"from": "entrance", "to": "living", "type": "door"},
        {"from": "living", "to": "kitchen", "type": "door"},
        {"from": "entrance", "to": "hallway_2f", "type": "stairs"},
        {"from": "hallway_2f", "to": "bedroom", "type": "door"},
        {"from": "entrance", "to": "garden", "type": "door"},
    ],
}

FLAT_MAP = {
    "locations": [
        {"id": "room_a", "name": "部屋A", "features": ["椅子"]},
        {"id": "room_b", "name": "部屋B", "features": ["机"]},
    ],
    "connections": [
        {"from": "room_a", "to": "room_b", "type": "door"},
    ],
}


def test_render_hierarchical_produces_svg():
    svg = render_map_svg(HIERARCHICAL_MAP)
    assert svg.startswith("<svg")
    assert "</svg>" in svg


def test_render_contains_area_names():
    svg = render_map_svg(HIERARCHICAL_MAP)
    assert "本館1階" in svg
    assert "本館2階" in svg
    assert "屋外" in svg


def test_render_contains_room_names():
    svg = render_map_svg(HIERARCHICAL_MAP)
    assert "玄関" in svg
    assert "リビング" in svg
    assert "寝室" in svg
    assert "庭園" in svg


def test_render_room_names_only_no_features():
    svg = render_map_svg(HIERARCHICAL_MAP)
    assert "リビング" in svg
    assert "暖炉" not in svg  # features not shown on map


def test_render_contains_connection_markers():
    svg = render_map_svg(HIERARCHICAL_MAP)
    assert "⇅" in svg  # stairs marker


def test_render_flat_map_fallback():
    svg = render_map_svg(FLAT_MAP)
    assert "部屋A" in svg
    assert "部屋B" in svg


def test_render_empty_map():
    svg = render_map_svg({"areas": []})
    assert "マップなし" in svg


def test_render_empty_connections():
    svg = render_map_svg({
        "areas": [{"id": "a", "name": "A", "area_type": "indoor", "rooms": [{"id": "r1", "name": "R1", "features": ["x"]}]}],
        "connections": [],
    })
    assert "R1" in svg


def test_outdoor_area_has_dashed_border():
    svg = render_map_svg(HIERARCHICAL_MAP)
    assert "stroke-dasharray" in svg
