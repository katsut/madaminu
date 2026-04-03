"""Tests for map_builder: graph construction from room list."""

from madaminu.services.map_builder import build_map_structure, generate_route_text, generate_travel_narrative


def _make_area(area_id, name, rooms, area_type="indoor", floor_order=0):
    return {
        "id": area_id,
        "name": name,
        "area_type": area_type,
        "floor_order": floor_order,
        "rooms": rooms,
    }


def _make_room(room_id, name, size=1, is_crime_scene=False):
    return {
        "id": room_id,
        "name": name,
        "size": size,
        "features": [f"f{i}" for i in range(size * 3)],
        "is_crime_scene": is_crime_scene,
    }


class TestBuildMapStructure:
    def test_indoor_adds_entrance_corridor_stairs(self):
        llm_map = {
            "areas": [
                _make_area("f1", "1階", [_make_room("r1", "書斎"), _make_room("r2", "リビング")]),
                _make_area("f2", "2階", [_make_room("r3", "寝室"), _make_room("r4", "客室")], floor_order=1),
            ]
        }
        result = build_map_structure(llm_map)
        areas = result["areas"]

        for area in areas:
            types = {r.get("room_type") for r in area["rooms"]}
            assert "entrance" in types
            assert "corridor" in types
            assert "stairs" in types

    def test_single_area_no_stairs(self):
        llm_map = {"areas": [_make_area("f1", "1階", [_make_room("r1", "書斎"), _make_room("r2", "リビング")])]}
        result = build_map_structure(llm_map)
        types = {r.get("room_type") for r in result["areas"][0]["rooms"]}
        assert "stairs" not in types
        assert "entrance" in types
        assert "corridor" in types

    def test_max_2_rooms_per_corridor(self):
        rooms = [_make_room(f"r{i}", f"部屋{i}") for i in range(6)]
        llm_map = {"areas": [_make_area("f1", "1階", rooms)]}
        result = build_map_structure(llm_map)

        conns = result["connections"]
        corridor_room_counts: dict[str, int] = {}
        for c in conns:
            if c["type"] == "door":
                corridor_room_counts[c["from"]] = corridor_room_counts.get(c["from"], 0) + 1

        for count in corridor_room_counts.values():
            assert count <= 2, f"Corridor has {count} rooms attached"

    def test_corridor_count_matches_rooms(self):
        import math

        rooms = [_make_room(f"r{i}", f"部屋{i}") for i in range(5)]
        llm_map = {"areas": [_make_area("f1", "1階", rooms)]}
        result = build_map_structure(llm_map)

        corridors = [r for r in result["areas"][0]["rooms"] if r.get("room_type") == "corridor"]
        assert len(corridors) >= math.ceil(len(rooms) / 2)

    def test_outdoor_no_corridor(self):
        rooms = [_make_room("g1", "噴水"), _make_room("g2", "温室")]
        llm_map = {"areas": [_make_area("garden", "中庭", rooms, area_type="outdoor")]}
        result = build_map_structure(llm_map)

        types = {r.get("room_type") for r in result["areas"][0]["rooms"]}
        assert "corridor" not in types
        assert "entrance" not in types

    def test_floor_connections(self):
        llm_map = {
            "areas": [
                _make_area("f1", "1階", [_make_room("r1", "書斎"), _make_room("r2", "リビング")], floor_order=0),
                _make_area("f2", "2階", [_make_room("r3", "寝室"), _make_room("r4", "客室")], floor_order=1),
            ]
        }
        result = build_map_structure(llm_map)
        stair_conns = [c for c in result["connections"] if c["type"] == "stairs"]
        assert len(stair_conns) == 1

    def test_crime_scene_from_victim(self):
        rooms = [_make_room("r1", "書斎"), _make_room("r2", "リビング")]
        llm_map = {"areas": [_make_area("f1", "1階", rooms)]}
        victim = {"name": "被害者", "crime_scene_room_id": "r2"}
        result = build_map_structure(llm_map, victim=victim)

        r2 = next(r for r in result["areas"][0]["rooms"] if r["id"] == "r2")
        assert r2.get("is_crime_scene") is True

    def test_crime_scene_fallback(self):
        rooms = [_make_room("r1", "書斎", size=1), _make_room("r2", "リビング", size=2)]
        llm_map = {"areas": [_make_area("f1", "1階", rooms)]}
        result = build_map_structure(llm_map)

        has_crime = any(r.get("is_crime_scene") for a in result["areas"] for r in a["rooms"])
        assert has_crime

    def test_indoor_outdoor_connection(self):
        llm_map = {
            "areas": [
                _make_area("f1", "1階", [_make_room("r1", "書斎"), _make_room("r2", "リビング")]),
                _make_area(
                    "garden",
                    "中庭",
                    [_make_room("g1", "噴水"), _make_room("g2", "温室")],
                    area_type="outdoor",
                    floor_order=1,
                ),
            ]
        }
        result = build_map_structure(llm_map)
        door_conns = [c for c in result["connections"] if c["type"] == "door"]
        cross_area = [
            c
            for c in door_conns
            if ("entrance" in c["from"] and c["to"] == "g1") or ("entrance" in c["to"] and c["from"] == "g1")
        ]
        assert len(cross_area) > 0


class TestGenerateRouteText:
    def test_basic_output(self):
        llm_map = {
            "areas": [
                _make_area("f1", "1階", [_make_room("r1", "書斎", is_crime_scene=True), _make_room("r2", "リビング")]),
            ]
        }
        result = build_map_structure(llm_map)
        text = generate_route_text(result)

        assert "1階" in text
        assert "書斎" in text
        assert "リビング" in text
        assert "犯行現場" in text
        assert "動線" in text

    def test_player_positions(self):
        llm_map = {"areas": [_make_area("f1", "1階", [_make_room("r1", "書斎"), _make_room("r2", "リビング")])]}
        result = build_map_structure(llm_map)
        players = [
            {"character_name": "探偵", "alibi_room_id": "r1", "personal_room_id": None},
            {"character_name": "医者", "alibi_room_id": "r2", "personal_room_id": "r2"},
        ]
        text = generate_route_text(result, players=players)
        assert "探偵" in text
        assert "医者" in text
        assert "書斎" in text


class TestTravelNarrative:
    def test_generates_narrative(self):
        llm_map = {
            "areas": [
                _make_area("f1", "1階", [_make_room("r1", "書斎"), _make_room("r2", "リビング")]),
            ]
        }
        result = build_map_structure(llm_map)
        selections = {"p1": "r1", "p2": "r2"}
        id_to_name = {"p1": "探偵", "p2": "医者"}
        narratives = generate_travel_narrative(result, selections, id_to_name)

        assert "p1" in narratives
        assert "p2" in narratives
        assert "書斎" in narratives["p1"]

    def test_companions_mentioned(self):
        llm_map = {"areas": [_make_area("f1", "1階", [_make_room("r1", "書斎"), _make_room("r2", "リビング")])]}
        result = build_map_structure(llm_map)
        selections = {"p1": "r1", "p2": "r1"}
        id_to_name = {"p1": "探偵", "p2": "医者"}
        narratives = generate_travel_narrative(result, selections, id_to_name)

        assert "医者" in narratives["p1"]
