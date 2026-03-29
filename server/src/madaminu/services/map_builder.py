"""Build map graph structure from LLM-generated room list.

LLM generates: areas with rooms (name, size, features, special attributes)
This module generates: corridors, entrances, stairs, connections
"""

import math


def build_map_structure(llm_map: dict, victim: dict | None = None) -> dict:
    """Transform LLM room list into complete map with backbone and connections."""
    areas = llm_map.get("areas", [])
    if not areas:
        return llm_map

    all_connections: list[dict] = []
    indoor_areas_with_stairs: list[dict] = []

    # Set crime scene from victim data
    crime_room_id = (victim or {}).get("crime_scene_room_id")
    all_rooms_flat = [r for a in areas for r in a.get("rooms", [])]
    if crime_room_id:
        for r in all_rooms_flat:
            r["is_crime_scene"] = r["id"] == crime_room_id
    # Fallback: if no crime scene set, pick first size>=2 room
    if not any(r.get("is_crime_scene") for r in all_rooms_flat):
        candidate = next((r for r in all_rooms_flat if r.get("size", 1) >= 2), None)
        if candidate is None and all_rooms_flat:
            candidate = all_rooms_flat[0]
        if candidate:
            candidate["is_crime_scene"] = True

    # Determine which areas need stairs (multiple indoor/semi_outdoor areas)
    indoor_areas = [a for a in areas if a.get("area_type", "indoor") != "outdoor"]
    needs_stairs = len(indoor_areas) > 1

    for area in areas:
        area_type = area.get("area_type", "indoor")
        rooms = [r for r in area.get("rooms", []) if r.get("room_type") not in ("corridor", "entrance", "stairs")]

        if area_type == "outdoor":
            conns = _build_outdoor(area, rooms)
        else:
            conns = _build_indoor(area, rooms, needs_stairs)
            if needs_stairs:
                indoor_areas_with_stairs.append(area)

        all_connections.extend(conns)

    # Connect stairs between floors
    stair_conns = _connect_floors(indoor_areas_with_stairs)
    all_connections.extend(stair_conns)

    # Connect indoor entrance to outdoor areas
    entrance_conns = _connect_indoor_outdoor(areas)
    all_connections.extend(entrance_conns)

    return {
        "areas": areas,
        "connections": all_connections,
    }


def _build_indoor(area: dict, rooms: list[dict], add_stairs: bool) -> list[dict]:
    """Build backbone + branch structure for indoor area."""
    area_id = area["id"]
    connections: list[dict] = []

    corridor_count = max(1, math.ceil(len(rooms) / 2))

    # Generate infrastructure nodes
    entrance = {
        "id": f"{area_id}_entrance",
        "name": "玄関",
        "room_type": "entrance",
    }

    corridors = []
    for i in range(corridor_count):
        corridors.append(
            {
                "id": f"{area_id}_corridor_{i}",
                "name": "廊下",
                "room_type": "corridor",
            }
        )

    stairs = None
    if add_stairs:
        stairs = {
            "id": f"{area_id}_stairs",
            "name": "階段",
            "room_type": "stairs",
        }

    # Build backbone: entrance → corridors → stairs
    backbone = [entrance] + corridors
    if stairs:
        backbone.append(stairs)

    for i in range(len(backbone) - 1):
        connections.append(
            {
                "from": backbone[i]["id"],
                "to": backbone[i + 1]["id"],
                "type": "corridor",
            }
        )

    # Connect rooms to corridors (max 2 per corridor)
    for i, room in enumerate(rooms):
        corridor_idx = min(i // 2, corridor_count - 1)
        connections.append(
            {
                "from": corridors[corridor_idx]["id"],
                "to": room["id"],
                "type": "door",
            }
        )

    # Crime scene: ensure 2+ connections
    for room in rooms:
        if room.get("is_crime_scene"):
            room_conns = [c for c in connections if c["to"] == room["id"] or c["from"] == room["id"]]
            if len(room_conns) < 2:
                # Connect to an adjacent corridor
                room_idx = rooms.index(room)
                corridor_idx = min(room_idx // 2, corridor_count - 1)
                alt_idx = corridor_idx + 1 if corridor_idx + 1 < corridor_count else corridor_idx - 1
                if 0 <= alt_idx < corridor_count:
                    connections.append(
                        {
                            "from": corridors[alt_idx]["id"],
                            "to": room["id"],
                            "type": "door",
                        }
                    )

    # Prepend infrastructure nodes to area rooms
    infra = [entrance] + corridors
    if stairs:
        infra.append(stairs)
    area["rooms"] = infra + rooms

    return connections


def _build_outdoor(area: dict, rooms: list[dict]) -> list[dict]:
    """Build linear path for outdoor area. First room acts as entrance point."""
    connections: list[dict] = []

    if len(rooms) <= 1:
        area["rooms"] = rooms
        return connections

    # Linear chain: room0 → room1 → room2 → ...
    for i in range(len(rooms) - 1):
        connections.append(
            {
                "from": rooms[i]["id"],
                "to": rooms[i + 1]["id"],
                "type": "corridor",
            }
        )

    area["rooms"] = rooms
    return connections


def _connect_floors(indoor_areas: list[dict]) -> list[dict]:
    """Connect stairs between adjacent indoor floors."""
    connections: list[dict] = []

    # Sort by floor_order
    sorted_areas = sorted(indoor_areas, key=lambda a: a.get("floor_order", 0))

    for i in range(len(sorted_areas) - 1):
        stairs_a = _find_stairs(sorted_areas[i])
        stairs_b = _find_stairs(sorted_areas[i + 1])
        if stairs_a and stairs_b:
            connections.append(
                {
                    "from": stairs_a["id"],
                    "to": stairs_b["id"],
                    "type": "stairs",
                }
            )

    return connections


def _connect_indoor_outdoor(areas: list[dict]) -> list[dict]:
    """Connect indoor entrance to the first outdoor area's first room."""
    connections: list[dict] = []

    indoor_entrance = None
    for area in areas:
        if area.get("area_type", "indoor") != "outdoor":
            entrance = _find_entrance(area)
            if entrance:
                indoor_entrance = entrance
                break

    outdoor_first_room = None
    for area in areas:
        if area.get("area_type") == "outdoor":
            rooms = [r for r in area.get("rooms", []) if r.get("room_type") not in ("corridor", "entrance", "stairs")]
            if rooms:
                outdoor_first_room = rooms[0]
                break

    if indoor_entrance and outdoor_first_room:
        connections.append(
            {
                "from": indoor_entrance["id"],
                "to": outdoor_first_room["id"],
                "type": "door",
            }
        )

    return connections


def _find_stairs(area: dict) -> dict | None:
    for room in area.get("rooms", []):
        if room.get("room_type") == "stairs":
            return room
    return None


def _find_entrance(area: dict) -> dict | None:
    for room in area.get("rooms", []):
        if room.get("room_type") == "entrance":
            return room
    return None


def generate_route_text(map_data: dict, players: list[dict] | None = None) -> str:
    """Convert map structure to natural language route description for LLM context."""
    areas = map_data.get("areas", [])
    connections = map_data.get("connections", [])
    lines: list[str] = []

    # Build adjacency from connections
    adj: dict[str, list[str]] = {}
    for c in connections:
        a, b = c["from"], c["to"]
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)

    # Node lookup
    all_nodes: dict[str, dict] = {}
    for area in areas:
        for room in area.get("rooms", []):
            all_nodes[room["id"]] = room

    for area in areas:
        lines.append(f"■ {area.get('name', area['id'])}")

        rooms = area.get("rooms", [])
        room_map = {r["id"]: r for r in rooms}

        # Find backbone
        backbone_types = {"corridor", "entrance", "stairs"}
        backbone_ids = [r["id"] for r in rooms if r.get("room_type") in backbone_types]
        room_ids = [r["id"] for r in rooms if r.get("room_type") not in backbone_types]

        if backbone_ids:
            backbone_names = [room_map[bid].get("name", bid) for bid in backbone_ids]
            lines.append(f"  動線: {' → '.join(backbone_names)}")

            for bid in backbone_ids:
                connected_rooms = []
                for nb in adj.get(bid, []):
                    if nb in room_map and room_map[nb].get("room_type") not in backbone_types:
                        node = room_map[nb]
                        name = node.get("name", nb)
                        size = node.get("size", 1)
                        extras = []
                        if node.get("is_crime_scene"):
                            extras.append("犯行現場")
                        extra = f"({', '.join(extras)})" if extras else ""
                        connected_rooms.append(f"{name}(size:{size}){extra}")
                if connected_rooms:
                    corridor_name = room_map[bid].get("name", bid)
                    lines.append(f"  - {corridor_name}: {', '.join(connected_rooms)}")
        else:
            # Outdoor: list rooms linearly
            room_names = [room_map[rid].get("name", rid) for rid in room_ids]
            lines.append(f"  場所: {' — '.join(room_names)}")

        lines.append("")

    # Floor connections
    stair_conns = [c for c in connections if c["type"] == "stairs"]
    for c in stair_conns:
        a_name = all_nodes.get(c["from"], {}).get("name", c["from"])
        b_name = all_nodes.get(c["to"], {}).get("name", c["to"])
        # Find area names
        a_area = _find_area_for_node(areas, c["from"])
        b_area = _find_area_for_node(areas, c["to"])
        lines.append(f"● 階段接続: {a_area}・{a_name} ↔ {b_area}・{b_name}")

    # Indoor-outdoor connections
    door_conns = [c for c in connections if c["type"] == "door"]
    for c in door_conns:
        a_area_type = _find_area_type_for_node(areas, c["from"])
        b_area_type = _find_area_type_for_node(areas, c["to"])
        if a_area_type != b_area_type:
            a_name = all_nodes.get(c["from"], {}).get("name", c["from"])
            b_name = all_nodes.get(c["to"], {}).get("name", c["to"])
            lines.append(f"● 出入口: {a_name} → {b_name}")

    # Crime scene
    for area in areas:
        for room in area.get("rooms", []):
            if room.get("is_crime_scene"):
                lines.append(f"● 犯行現場: {room.get('name', room['id'])}（{area.get('name', area['id'])}）")

    # Character locations at time of incident
    if players:
        lines.append("")
        lines.append("■ 事件発生時のキャラクター位置")
        for p in players:
            name = p.get("character_name", "?")
            alibi_room = p.get("alibi_room_id")
            personal_room = p.get("personal_room_id")
            alibi_name = all_nodes.get(alibi_room, {}).get("name", alibi_room) if alibi_room else "不明"
            parts = [f"  - {name}: 居場所={alibi_name}"]
            if personal_room:
                personal_name = all_nodes.get(personal_room, {}).get("name", personal_room)
                parts.append(f"(個室={personal_name})")
            lines.append(" ".join(parts))

    return "\n".join(lines)


def generate_travel_narrative(
    map_data: dict,
    selections: dict[str, str],
    id_to_name: dict[str, str],
) -> dict[str, str]:
    """Generate travel narrative for each player from a common start point.

    Args:
        map_data: Complete map with areas and connections.
        selections: {player_id: location_id} - where each player is going.
        id_to_name: {player_id: character_name}.

    Returns:
        {player_id: narrative_text} for each player.
    """
    connections = map_data.get("connections", [])
    all_nodes: dict[str, dict] = {}
    for area in map_data.get("areas", []):
        for room in area.get("rooms", []):
            all_nodes[room["id"]] = room

    # Build adjacency
    adj: dict[str, list[str]] = {}
    for c in connections:
        a, b = c["from"], c["to"]
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)

    # Find common start: first entrance
    start = None
    for area in map_data.get("areas", []):
        for room in area.get("rooms", []):
            if room.get("room_type") == "entrance":
                start = room["id"]
                break
        if start:
            break

    if not start:
        return {pid: "" for pid in selections}

    # BFS shortest path for each destination
    def find_path(from_id: str, to_id: str) -> list[str]:
        if from_id == to_id:
            return [from_id]
        visited = {from_id}
        queue = [(from_id, [from_id])]
        while queue:
            current, path = queue.pop(0)
            for nb in adj.get(current, []):
                if nb in visited:
                    continue
                visited.add(nb)
                new_path = path + [nb]
                if nb == to_id:
                    return new_path
                queue.append((nb, new_path))
        return []

    # Group players by destination
    dest_groups: dict[str, list[str]] = {}
    for pid, loc_id in selections.items():
        dest_groups.setdefault(loc_id, []).append(pid)

    narratives: dict[str, str] = {}
    for pid, loc_id in selections.items():
        path = find_path(start, loc_id)
        if not path:
            narratives[pid] = ""
            continue

        room_names = [all_nodes.get(nid, {}).get("name", nid) for nid in path]
        dest_name = all_nodes.get(loc_id, {}).get("name", loc_id)

        # Who else is going to the same place?
        companions = [id_to_name.get(other, "?") for other in dest_groups.get(loc_id, []) if other != pid]

        parts = []
        if len(room_names) > 2:
            route = " → ".join(room_names[1:-1])
            parts.append(f"{route}を通って")
        parts.append(f"{dest_name}に向かった。")

        if companions:
            parts.append(f"{', '.join(companions)}も同じ場所に向かっている。")

        narratives[pid] = "".join(parts)

    return narratives


def _find_area_for_node(areas: list[dict], node_id: str) -> str:
    for area in areas:
        for room in area.get("rooms", []):
            if room["id"] == node_id:
                return area.get("name", area["id"])
    return "?"


def _find_area_type_for_node(areas: list[dict], node_id: str) -> str:
    for area in areas:
        for room in area.get("rooms", []):
            if room["id"] == node_id:
                return area.get("area_type", "indoor")
    return "indoor"
