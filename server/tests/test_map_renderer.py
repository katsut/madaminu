"""Tests for SVG map renderer."""

from madaminu.services.map_renderer import render_map_svg


GRAPH_MAP = {
    "areas": [
        {
            "id": "main_1f", "name": "本館1階", "area_type": "indoor",
            "nodes": [
                {"id": "entrance", "name": "玄関", "type": "entrance"},
                {"id": "corridor_1", "name": "廊下", "type": "passage"},
                {"id": "stairs_1f", "name": "階段", "type": "stairs"},
                {"id": "living", "name": "リビング", "type": "room", "features": ["暖炉", "ソファ"]},
                {"id": "kitchen", "name": "台所", "type": "room", "features": ["包丁"]},
            ],
            "edges": [
                ["entrance", "corridor_1"],
                ["corridor_1", "stairs_1f"],
                ["corridor_1", "living"],
                ["corridor_1", "kitchen"],
            ],
        },
        {
            "id": "main_2f", "name": "本館2階", "area_type": "indoor",
            "nodes": [
                {"id": "stairs_2f", "name": "階段", "type": "stairs"},
                {"id": "corridor_2", "name": "廊下", "type": "passage"},
                {"id": "bedroom", "name": "寝室", "type": "room", "features": ["ベッド"]},
            ],
            "edges": [
                ["stairs_2f", "corridor_2"],
                ["corridor_2", "bedroom"],
            ],
        },
        {
            "id": "outside", "name": "屋外", "area_type": "outdoor",
            "nodes": [
                {"id": "garden", "name": "庭園", "type": "room", "features": ["噴水"]},
            ],
            "edges": [],
        },
    ],
    "floor_connections": [
        ["stairs_1f", "stairs_2f"],
        ["entrance", "garden"],
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


def test_render_produces_svg():
    svg = render_map_svg(GRAPH_MAP)
    assert svg.startswith("<svg")
    assert "</svg>" in svg


def test_render_contains_area_names():
    svg = render_map_svg(GRAPH_MAP)
    assert "本館1階" in svg
    assert "本館2階" in svg
    assert "屋外" in svg


def test_render_contains_room_names():
    svg = render_map_svg(GRAPH_MAP)
    assert "玄関" in svg
    assert "リビング" in svg
    assert "寝室" in svg
    assert "庭園" in svg


def test_render_no_features_on_map():
    svg = render_map_svg(GRAPH_MAP)
    assert "暖炉" not in svg


def test_render_contains_stairs():
    svg = render_map_svg(GRAPH_MAP)
    assert "階段" in svg


def test_render_contains_legend():
    svg = render_map_svg(GRAPH_MAP)
    assert "部屋" in svg
    assert "廊下" in svg
    assert "階段" in svg


def test_render_has_aria_label():
    svg = render_map_svg(GRAPH_MAP)
    assert 'aria-label="マップ"' in svg


def test_render_highlight_has_glow():
    svg = render_map_svg(GRAPH_MAP, highlight_room="entrance")
    assert "url(#glow)" in svg


def test_render_area_icons():
    svg = render_map_svg(GRAPH_MAP)
    assert "🏠" in svg
    assert "🌳" in svg


def test_render_svg_title():
    svg = render_map_svg(GRAPH_MAP)
    assert "ゲームマップ" in svg


def test_render_area_aria_group():
    svg = render_map_svg(GRAPH_MAP)
    assert 'aria-label="本館1階"' in svg


def test_render_flat_map_fallback():
    svg = render_map_svg(FLAT_MAP)
    assert "部屋A" in svg
    assert "部屋B" in svg


def test_render_empty_map():
    svg = render_map_svg({"areas": []})
    assert "マップなし" in svg


def test_render_outdoor_area_has_dashed_border():
    svg = render_map_svg(GRAPH_MAP)
    assert "stroke-dasharray" in svg
