"""Generate SVG map from hierarchical area/room map data."""

from xml.etree.ElementTree import Element, SubElement, tostring

ROOM_W = 110
ROOM_H = 34
ROOM_GAP = 8
AREA_PAD = 14
AREA_GAP = 40
AREA_HEADER = 26
PADDING = 20
CONN_MARGIN = 18  # space on left/right of areas for routing lines
FONT_SIZE = 11

COLORS = {
    "indoor": {"fill": "#1e1e2e", "stroke": "#5555aa", "header": "#3a3a5a"},
    "outdoor": {"fill": "#1a2a1a", "stroke": "#448844", "header": "#2a4a2a"},
    "semi_outdoor": {"fill": "#1e2a2a", "stroke": "#558866", "header": "#2a3a3a"},
    "room": {"fill": "#2a2a3e", "stroke": "#6666aa"},
    "room_outdoor": {"fill": "#223322", "stroke": "#669966"},
    "text": "#cccccc",
    "text_dim": "#888899",
    "background": "#111118",
    "door": "#cc9944",
    "window": "#6699cc",
    "stairs": "#aa77cc",
    "corridor": "#999999",
    "hidden_passage": "#666666",
}

CONNECTION_COLORS = {
    "door": COLORS["door"],
    "window": COLORS["window"],
    "stairs": COLORS["stairs"],
    "corridor": COLORS["corridor"],
    "hidden_passage": COLORS["hidden_passage"],
}

CONN_ICONS = {"door": "D", "stairs": "S", "window": "W", "hidden_passage": "?", "corridor": "="}


def render_map_svg(map_data: dict, highlight_room: str | None = None) -> str:
    areas = map_data.get("areas")
    if areas is None:
        return _render_flat_map(map_data, highlight_room)
    return _render_hierarchical_map(map_data, highlight_room)


def _render_hierarchical_map(map_data: dict, highlight_room: str | None = None) -> str:
    areas = map_data.get("areas", [])
    connections = map_data.get("connections", [])

    if not areas:
        return _empty_svg()

    # Build room-to-area index
    room_area = {}
    for area in areas:
        for room in area.get("rooms", []):
            room_area[room["id"]] = area["id"]

    # Sort rooms within each area: connected rooms should be adjacent
    for area in areas:
        area["rooms"] = _sort_rooms_by_connections(area["rooms"], connections)

    # Classify connections
    intra_conns = []  # same area
    inter_conns = []  # cross area
    for conn in connections:
        fa = room_area.get(conn["from"])
        ta = room_area.get(conn["to"])
        if fa and ta and fa == ta:
            intra_conns.append(conn)
        elif fa and ta:
            inter_conns.append(conn)

    # Layout areas
    area_layouts = []
    room_positions = {}
    x_cursor = PADDING + CONN_MARGIN

    for area in areas:
        rooms = area.get("rooms", [])
        area_type = area.get("area_type", "indoor")
        n = len(rooms)

        content_h = n * (ROOM_H + ROOM_GAP) - ROOM_GAP if n > 0 else ROOM_H
        area_w = ROOM_W + AREA_PAD * 2
        area_h = AREA_HEADER + content_h + AREA_PAD * 2

        area_x = x_cursor
        area_y = PADDING

        area_layouts.append({
            "area": area, "x": area_x, "y": area_y,
            "w": area_w, "h": area_h, "area_type": area_type,
        })

        for i, room in enumerate(rooms):
            rx = area_x + AREA_PAD
            ry = area_y + AREA_HEADER + AREA_PAD + i * (ROOM_H + ROOM_GAP)
            room_positions[room["id"]] = {
                "x": rx, "y": ry,
                "cx": rx + ROOM_W // 2, "cy": ry + ROOM_H // 2,
                "area_id": area["id"], "index": i,
            }

        x_cursor += area_w + AREA_GAP

    total_w = x_cursor - AREA_GAP + CONN_MARGIN + PADDING
    max_area_bottom = max((a["y"] + a["h"] for a in area_layouts), default=200)
    inter_routing_y = max_area_bottom + 20
    total_h = inter_routing_y + len(inter_conns) * 14 + PADDING

    svg = Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "viewBox": f"0 0 {total_w} {total_h}",
        "width": str(total_w), "height": str(total_h),
    })
    SubElement(svg, "rect", {"width": str(total_w), "height": str(total_h), "fill": COLORS["background"]})

    # Draw areas
    for al in area_layouts:
        _draw_area(svg, al)

    # Draw rooms
    for area in areas:
        at = area.get("area_type", "indoor")
        for room in area.get("rooms", []):
            pos = room_positions[room["id"]]
            _draw_room(svg, room, pos["x"], pos["y"], at, highlighted=room["id"] == highlight_room)

    # Draw intra-area connections (left side brackets)
    for conn in intra_conns:
        fp = room_positions.get(conn["from"])
        tp = room_positions.get(conn["to"])
        if fp and tp:
            _draw_intra_connection(svg, conn, fp, tp)

    # Draw inter-area connections (routed below)
    for i, conn in enumerate(inter_conns):
        fp = room_positions.get(conn["from"])
        tp = room_positions.get(conn["to"])
        if fp and tp:
            route_y = inter_routing_y + i * 14
            _draw_inter_connection(svg, conn, fp, tp, route_y)

    return tostring(svg, encoding="unicode")


def _sort_rooms_by_connections(rooms: list[dict], connections: list[dict]) -> list[dict]:
    """Sort rooms so connected rooms are adjacent."""
    if len(rooms) <= 2:
        return rooms

    room_ids = [r["id"] for r in rooms]
    room_map = {r["id"]: r for r in rooms}
    adj: dict[str, list[str]] = {rid: [] for rid in room_ids}
    for conn in connections:
        if conn["from"] in adj and conn["to"] in adj:
            adj[conn["from"]].append(conn["to"])
            adj[conn["to"]].append(conn["from"])

    # Simple greedy chain: start from a room with fewest connections
    visited = set()
    result = []
    start = min(room_ids, key=lambda r: len(adj[r]))
    queue = [start]
    while queue:
        rid = queue.pop(0)
        if rid in visited:
            continue
        visited.add(rid)
        result.append(room_map[rid])
        for neighbor in adj[rid]:
            if neighbor not in visited:
                queue.insert(0, neighbor)

    # Add any remaining rooms
    for rid in room_ids:
        if rid not in visited:
            result.append(room_map[rid])

    return result


def _draw_area(svg: Element, layout: dict):
    area = layout["area"]
    colors = COLORS.get(layout["area_type"], COLORS["indoor"])

    attrs = {
        "x": str(layout["x"]), "y": str(layout["y"]),
        "width": str(layout["w"]), "height": str(layout["h"]),
        "fill": "none", "stroke": colors["stroke"], "stroke-width": "2", "rx": "8",
    }
    if layout["area_type"] == "outdoor":
        attrs["stroke-dasharray"] = "6,3"
    SubElement(svg, "rect", attrs)

    SubElement(svg, "rect", {
        "x": str(layout["x"]), "y": str(layout["y"]),
        "width": str(layout["w"]), "height": str(AREA_HEADER),
        "fill": colors["header"], "rx": "8",
    })
    SubElement(svg, "rect", {
        "x": str(layout["x"]), "y": str(layout["y"] + AREA_HEADER - 8),
        "width": str(layout["w"]), "height": "8", "fill": colors["header"],
    })

    t = SubElement(svg, "text", {
        "x": str(layout["x"] + layout["w"] // 2),
        "y": str(layout["y"] + AREA_HEADER // 2 + 1),
        "text-anchor": "middle", "dominant-baseline": "central",
        "fill": COLORS["text"], "font-size": str(FONT_SIZE),
        "font-weight": "bold", "font-family": "sans-serif",
    })
    t.text = area.get("name", area["id"])


def _draw_room(svg: Element, room: dict, x: int, y: int, area_type: str, highlighted: bool = False):
    if highlighted:
        fill, stroke, sw = "#3a2a1a", "#cc9944", "2.5"
    elif area_type == "outdoor":
        fill, stroke, sw = COLORS["room_outdoor"]["fill"], COLORS["room_outdoor"]["stroke"], "1.5"
    else:
        fill, stroke, sw = COLORS["room"]["fill"], COLORS["room"]["stroke"], "1.5"

    SubElement(svg, "rect", {
        "x": str(x), "y": str(y), "width": str(ROOM_W), "height": str(ROOM_H),
        "fill": fill, "stroke": stroke, "stroke-width": sw, "rx": "4",
    })
    t = SubElement(svg, "text", {
        "x": str(x + ROOM_W // 2), "y": str(y + ROOM_H // 2 + 1),
        "text-anchor": "middle", "dominant-baseline": "central",
        "fill": COLORS["text"], "font-size": str(FONT_SIZE),
        "font-weight": "bold", "font-family": "sans-serif",
    })
    t.text = room.get("name", room["id"])


def _draw_intra_connection(svg: Element, conn: dict, fp: dict, tp: dict):
    """Draw connection between rooms in the same area, using left-side bracket."""
    conn_type = conn.get("type", "door")
    color = CONNECTION_COLORS.get(conn_type, COLORS["door"])

    # Route along the left side of the rooms
    x_line = fp["x"] - 8
    y1 = fp["cy"]
    y2 = tp["cy"]

    # Horizontal ticks from room edge to line
    SubElement(svg, "line", {
        "x1": str(fp["x"]), "y1": str(y1),
        "x2": str(x_line), "y2": str(y1),
        "stroke": color, "stroke-width": "1.5",
    })
    SubElement(svg, "line", {
        "x1": str(tp["x"]), "y1": str(y2),
        "x2": str(x_line), "y2": str(y2),
        "stroke": color, "stroke-width": "1.5",
    })
    # Vertical line
    dash = {}
    if conn_type == "window":
        dash = {"stroke-dasharray": "3,3"}
    elif conn_type == "hidden_passage":
        dash = {"stroke-dasharray": "2,4"}

    SubElement(svg, "line", {
        "x1": str(x_line), "y1": str(y1),
        "x2": str(x_line), "y2": str(y2),
        "stroke": color, "stroke-width": "1.5", **dash,
    })

    # Small icon at midpoint
    my = (y1 + y2) // 2
    icon = CONN_ICONS.get(conn_type, "")
    if icon:
        SubElement(svg, "rect", {
            "x": str(x_line - 7), "y": str(my - 6),
            "width": "14", "height": "12",
            "fill": COLORS["background"], "rx": "2",
        })
        it = SubElement(svg, "text", {
            "x": str(x_line), "y": str(my + 1),
            "text-anchor": "middle", "dominant-baseline": "central",
            "fill": color, "font-size": "8", "font-family": "sans-serif",
        })
        it.text = icon


def _draw_inter_connection(svg: Element, conn: dict, fp: dict, tp: dict, route_y: int):
    """Draw connection between rooms in different areas, routed below."""
    conn_type = conn.get("type", "door")
    color = CONNECTION_COLORS.get(conn_type, COLORS["door"])

    # Start from bottom of from-room, end at bottom of to-room
    fx = fp["cx"]
    fy = fp["y"] + ROOM_H
    tx = tp["cx"]
    ty = tp["y"] + ROOM_H

    dash = ""
    if conn_type in ("stairs", "hidden_passage"):
        dash = "6,4"
    elif conn_type == "window":
        dash = "3,3"

    # Path: down from room → horizontal at route_y → up to room
    path_d = f"M {fx} {fy} L {fx} {route_y} L {tx} {route_y} L {tx} {ty}"
    attrs = {
        "d": path_d, "fill": "none",
        "stroke": color, "stroke-width": "1.5", "stroke-linecap": "round",
    }
    if dash:
        attrs["stroke-dasharray"] = dash
    SubElement(svg, "path", attrs)

    # Icon at midpoint of horizontal segment
    mx = (fx + tx) // 2
    icon = CONN_ICONS.get(conn_type, "")
    if icon:
        SubElement(svg, "rect", {
            "x": str(mx - 8), "y": str(route_y - 7),
            "width": "16", "height": "14",
            "fill": COLORS["background"], "rx": "2",
        })
        it = SubElement(svg, "text", {
            "x": str(mx), "y": str(route_y + 1),
            "text-anchor": "middle", "dominant-baseline": "central",
            "fill": color, "font-size": "9", "font-family": "sans-serif",
        })
        it.text = icon


def _render_flat_map(map_data: dict, highlight_room: str | None = None) -> str:
    locations = map_data.get("locations", [])
    if not locations:
        return _empty_svg()
    hierarchical = {
        "areas": [{"id": "main", "name": "マップ", "area_type": "indoor", "rooms": locations}],
        "connections": map_data.get("connections", []),
    }
    return _render_hierarchical_map(hierarchical, highlight_room)


def _empty_svg() -> str:
    svg = Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "viewBox": "0 0 200 100", "width": "200", "height": "100",
    })
    SubElement(svg, "rect", {"width": "200", "height": "100", "fill": COLORS["background"]})
    t = SubElement(svg, "text", {
        "x": "100", "y": "55", "text-anchor": "middle",
        "fill": COLORS["text"], "font-size": "14",
    })
    t.text = "マップなし"
    return tostring(svg, encoding="unicode")
