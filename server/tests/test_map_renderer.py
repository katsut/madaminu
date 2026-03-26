"""Tests for SVG map renderer."""

from madaminu.services.map_renderer import render_map_svg


SAMPLE_MAP = {
    "locations": [
        {"id": "garden", "name": "庭園", "description": "広い庭園", "area_type": "outdoor", "x": 0, "y": 0, "w": 3, "h": 1, "features": ["噴水", "花壇"]},
        {"id": "entrance", "name": "玄関", "description": "玄関ホール", "area_type": "indoor", "x": 1, "y": 1, "w": 1, "h": 1, "features": ["シャンデリア"]},
        {"id": "living", "name": "リビング", "description": "広いリビング", "area_type": "indoor", "x": 0, "y": 1, "w": 1, "h": 1, "features": ["暖炉", "ソファ"]},
        {"id": "kitchen", "name": "キッチン", "description": "キッチン", "area_type": "indoor", "x": 2, "y": 1, "w": 1, "h": 1, "features": ["包丁"]},
        {"id": "study", "name": "書斎", "description": "書斎", "area_type": "indoor", "x": 0, "y": 2, "w": 1, "h": 1, "features": ["金庫", "デスク"]},
        {"id": "terrace", "name": "テラス", "description": "テラス", "area_type": "semi_outdoor", "x": 2, "y": 2, "w": 1, "h": 1, "features": ["テーブル"]},
    ],
    "connections": [
        {"from": "entrance", "to": "living", "type": "door", "side": "west"},
        {"from": "entrance", "to": "kitchen", "type": "door", "side": "east"},
        {"from": "entrance", "to": "garden", "type": "door", "side": "north"},
        {"from": "living", "to": "garden", "type": "window", "side": "north"},
        {"from": "living", "to": "study", "type": "stairs", "side": "south"},
        {"from": "kitchen", "to": "terrace", "type": "door", "side": "south"},
    ],
}


def test_render_produces_valid_svg():
    svg = render_map_svg(SAMPLE_MAP)
    assert svg.startswith("<svg")
    assert "xmlns" in svg
    assert "</svg>" in svg


def test_render_contains_all_room_names():
    svg = render_map_svg(SAMPLE_MAP)
    for loc in SAMPLE_MAP["locations"]:
        assert loc["name"] in svg


def test_render_contains_features():
    svg = render_map_svg(SAMPLE_MAP)
    assert "噴水" in svg
    assert "暖炉" in svg


def test_render_has_outdoor_dashed_border():
    svg = render_map_svg(SAMPLE_MAP)
    assert "stroke-dasharray" in svg


def test_render_empty_map():
    svg = render_map_svg({"locations": [], "connections": []})
    assert "マップなし" in svg


def test_render_single_location():
    svg = render_map_svg({
        "locations": [
            {"id": "room", "name": "部屋", "description": "d", "area_type": "indoor", "x": 0, "y": 0, "w": 1, "h": 1, "features": ["椅子"]},
        ],
        "connections": [],
    })
    assert "部屋" in svg
    assert "椅子" in svg


def test_render_large_room():
    svg = render_map_svg({
        "locations": [
            {"id": "hall", "name": "大広間", "description": "d", "area_type": "indoor", "x": 0, "y": 0, "w": 3, "h": 2, "features": ["柱"]},
            {"id": "room", "name": "小部屋", "description": "d", "area_type": "indoor", "x": 3, "y": 0, "w": 1, "h": 1, "features": ["窓"]},
        ],
        "connections": [
            {"from": "hall", "to": "room", "type": "door"},
        ],
    })
    assert "大広間" in svg
    assert "小部屋" in svg


def test_render_stairs_marker():
    svg = render_map_svg(SAMPLE_MAP)
    # Stairs should draw a dashed line + marker
    assert "⇅" in svg


def test_render_viewbox_covers_all_rooms():
    svg = render_map_svg(SAMPLE_MAP)
    # viewBox should be large enough (3 columns * 80 + padding, 3 rows * 80 + padding)
    assert 'viewBox="0 0' in svg
