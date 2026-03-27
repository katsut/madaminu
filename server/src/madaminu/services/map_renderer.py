"""Generate SVG map from hierarchical area/room map data."""

from xml.etree.ElementTree import Element, SubElement, tostring

ROOM_W = 120
ROOM_H = 50
ROOM_GAP = 12
AREA_PAD = 16
AREA_GAP = 24
AREA_HEADER = 28
PADDING = 20
FONT_SIZE = 12
FEATURE_FONT = 9

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


def render_map_svg(map_data: dict, highlight_room: str | None = None) -> str:
    """Render map data to SVG string. Supports both flat and hierarchical format."""
    areas = map_data.get("areas")
    if areas is None:
        return _render_flat_map(map_data, highlight_room)
    return _render_hierarchical_map(map_data, highlight_room)


def _render_hierarchical_map(map_data: dict, highlight_room: str | None = None) -> str:
    areas = map_data.get("areas", [])
    connections = map_data.get("connections", [])

    if not areas:
        return _empty_svg()

    # Layout: areas side by side, rooms stacked vertically in each area
    area_layouts = []
    room_positions = {}
    x_cursor = PADDING

    for area in areas:
        rooms = area.get("rooms", [])
        area_type = area.get("area_type", "indoor")
        max_rooms = len(rooms)

        area_content_h = max_rooms * (ROOM_H + ROOM_GAP) - ROOM_GAP if max_rooms > 0 else ROOM_H
        area_w = ROOM_W + AREA_PAD * 2
        area_h = AREA_HEADER + area_content_h + AREA_PAD * 2

        area_x = x_cursor
        area_y = PADDING

        area_layouts.append({
            "area": area,
            "x": area_x,
            "y": area_y,
            "w": area_w,
            "h": area_h,
            "area_type": area_type,
        })

        for i, room in enumerate(rooms):
            rx = area_x + AREA_PAD
            ry = area_y + AREA_HEADER + AREA_PAD + i * (ROOM_H + ROOM_GAP)
            room_positions[room["id"]] = {
                "x": rx, "y": ry,
                "cx": rx + ROOM_W // 2,
                "cy": ry + ROOM_H // 2,
                "area_type": area_type,
            }

        x_cursor += area_w + AREA_GAP

    total_w = x_cursor - AREA_GAP + PADDING
    total_h = max((a["y"] + a["h"] for a in area_layouts), default=200) + PADDING

    svg = Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "viewBox": f"0 0 {total_w} {total_h}",
        "width": str(total_w),
        "height": str(total_h),
    })

    SubElement(svg, "rect", {"width": str(total_w), "height": str(total_h), "fill": COLORS["background"]})

    # Draw areas
    for al in area_layouts:
        _draw_area(svg, al)

    # Draw rooms
    for area in areas:
        area_type = area.get("area_type", "indoor")
        for room in area.get("rooms", []):
            pos = room_positions[room["id"]]
            _draw_room(svg, room, pos["x"], pos["y"], area_type, highlighted=room["id"] == highlight_room)

    # Draw connections
    for conn in connections:
        from_pos = room_positions.get(conn["from"])
        to_pos = room_positions.get(conn["to"])
        if from_pos and to_pos:
            _draw_connection(svg, conn, from_pos, to_pos)

    return tostring(svg, encoding="unicode")


def _draw_area(svg: Element, layout: dict):
    area = layout["area"]
    area_type = layout["area_type"]
    colors = COLORS.get(area_type, COLORS["indoor"])

    attrs = {
        "x": str(layout["x"]),
        "y": str(layout["y"]),
        "width": str(layout["w"]),
        "height": str(layout["h"]),
        "fill": "none",
        "stroke": colors["stroke"],
        "stroke-width": "2",
        "rx": "8",
    }
    if area_type == "outdoor":
        attrs["stroke-dasharray"] = "6,3"

    SubElement(svg, "rect", attrs)

    # Area header background
    SubElement(svg, "rect", {
        "x": str(layout["x"]),
        "y": str(layout["y"]),
        "width": str(layout["w"]),
        "height": str(AREA_HEADER),
        "fill": colors["header"],
        "rx": "8",
    })
    # Bottom corners of header should be square
    SubElement(svg, "rect", {
        "x": str(layout["x"]),
        "y": str(layout["y"] + AREA_HEADER - 8),
        "width": str(layout["w"]),
        "height": "8",
        "fill": colors["header"],
    })

    # Area name
    text = SubElement(svg, "text", {
        "x": str(layout["x"] + layout["w"] // 2),
        "y": str(layout["y"] + AREA_HEADER // 2 + 1),
        "text-anchor": "middle",
        "dominant-baseline": "central",
        "fill": COLORS["text"],
        "font-size": str(FONT_SIZE),
        "font-weight": "bold",
        "font-family": "sans-serif",
    })
    text.text = area.get("name", area["id"])


def _draw_room(svg: Element, room: dict, x: int, y: int, area_type: str, highlighted: bool = False):
    if highlighted:
        fill = "#3a2a1a"
        stroke = "#cc9944"
        stroke_width = "2.5"
    elif area_type == "outdoor":
        fill = COLORS["room_outdoor"]["fill"]
        stroke = COLORS["room_outdoor"]["stroke"]
        stroke_width = "1.5"
    else:
        fill = COLORS["room"]["fill"]
        stroke = COLORS["room"]["stroke"]
        stroke_width = "1.5"

    SubElement(svg, "rect", {
        "x": str(x), "y": str(y),
        "width": str(ROOM_W), "height": str(ROOM_H),
        "fill": fill,
        "stroke": stroke,
        "stroke-width": stroke_width,
        "rx": "4",
    })

    # Room name
    name_text = SubElement(svg, "text", {
        "x": str(x + ROOM_W // 2),
        "y": str(y + 18),
        "text-anchor": "middle",
        "fill": COLORS["text"],
        "font-size": str(FONT_SIZE),
        "font-weight": "bold",
        "font-family": "sans-serif",
    })
    name_text.text = room.get("name", room["id"])

    # Features
    features = room.get("features", [])
    if features:
        ft = SubElement(svg, "text", {
            "x": str(x + ROOM_W // 2),
            "y": str(y + 34),
            "text-anchor": "middle",
            "fill": COLORS["text_dim"],
            "font-size": str(FEATURE_FONT),
            "font-family": "sans-serif",
        })
        ft.text = "・".join(features[:3])


def _draw_connection(svg: Element, conn: dict, from_pos: dict, to_pos: dict):
    conn_type = conn.get("type", "door")
    color = CONNECTION_COLORS.get(conn_type, COLORS["door"])

    fx, fy = from_pos["cx"], from_pos["cy"]
    tx, ty = to_pos["cx"], to_pos["cy"]

    # Adjust start/end to room edges
    if abs(fx - tx) > abs(fy - ty):
        # Horizontal connection
        if fx < tx:
            fx = from_pos["x"] + ROOM_W
            tx = to_pos["x"]
        else:
            fx = from_pos["x"]
            tx = to_pos["x"] + ROOM_W
        fy = from_pos["cy"]
        ty = to_pos["cy"]
    else:
        # Vertical connection
        if fy < ty:
            fy = from_pos["y"] + ROOM_H
            ty = to_pos["y"]
        else:
            fy = from_pos["y"]
            ty = to_pos["y"] + ROOM_H
        fx = from_pos["cx"]
        tx = to_pos["cx"]

    attrs = {
        "x1": str(fx), "y1": str(fy),
        "x2": str(tx), "y2": str(ty),
        "stroke": color,
        "stroke-width": "2",
        "stroke-linecap": "round",
    }

    if conn_type in ("stairs", "hidden_passage"):
        attrs["stroke-dasharray"] = "6,4"
    if conn_type == "window":
        attrs["stroke-dasharray"] = "3,3"

    SubElement(svg, "line", attrs)

    # Label at midpoint
    mx = (fx + tx) // 2
    my = (fy + ty) // 2

    label = {"door": "🚪", "stairs": "⇅", "window": "◇", "hidden_passage": "?", "corridor": "─"}.get(conn_type, "")
    if label:
        # Background for label
        SubElement(svg, "rect", {
            "x": str(mx - 8), "y": str(my - 8),
            "width": "16", "height": "16",
            "fill": COLORS["background"], "rx": "3",
        })
        lt = SubElement(svg, "text", {
            "x": str(mx), "y": str(my + 1),
            "text-anchor": "middle",
            "dominant-baseline": "central",
            "fill": color,
            "font-size": "11",
        })
        lt.text = label


def _render_flat_map(map_data: dict, highlight_room: str | None = None) -> str:
    """Fallback renderer for old flat location format."""
    locations = map_data.get("locations", [])
    if not locations:
        return _empty_svg()

    # Convert to hierarchical format
    hierarchical = {
        "areas": [{"id": "main", "name": "マップ", "area_type": "indoor", "rooms": locations}],
        "connections": map_data.get("connections", []),
    }
    return _render_hierarchical_map(hierarchical, highlight_room)


def _empty_svg() -> str:
    svg = Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "viewBox": "0 0 200 100",
        "width": "200", "height": "100",
    })
    SubElement(svg, "rect", {"width": "200", "height": "100", "fill": COLORS["background"]})
    t = SubElement(svg, "text", {
        "x": "100", "y": "55", "text-anchor": "middle",
        "fill": COLORS["text"], "font-size": "14",
    })
    t.text = "マップなし"
    return tostring(svg, encoding="unicode")
