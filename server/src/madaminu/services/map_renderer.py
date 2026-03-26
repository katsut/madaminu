"""Generate SVG map from grid-based location data."""

from xml.etree.ElementTree import Element, SubElement, tostring

CELL_SIZE = 80
PADDING = 20
FONT_SIZE = 13
WALL_WIDTH = 3
DOOR_GAP = 20
WINDOW_DASH = "4,4"

COLORS = {
    "indoor": {"fill": "#2a2a3a", "stroke": "#8888aa"},
    "outdoor": {"fill": "#1a2a1a", "stroke": "#558855"},
    "semi_outdoor": {"fill": "#222a2a", "stroke": "#667766"},
    "door": "#cc9944",
    "window": "#6699cc",
    "stairs": "#aa77cc",
    "text": "#cccccc",
    "text_feature": "#888899",
    "background": "#111118",
}


def render_map_svg(map_data: dict) -> str:
    """Render map data to SVG string."""
    locations = map_data.get("locations", [])
    connections = map_data.get("connections", [])

    if not locations:
        return _empty_svg()

    # Calculate grid bounds
    min_x = min(loc.get("x", 0) for loc in locations)
    min_y = min(loc.get("y", 0) for loc in locations)
    max_x = max(loc.get("x", 0) + loc.get("w", 1) for loc in locations)
    max_y = max(loc.get("y", 0) + loc.get("h", 1) for loc in locations)

    width = (max_x - min_x) * CELL_SIZE + PADDING * 2
    height = (max_y - min_y) * CELL_SIZE + PADDING * 2

    svg = Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "viewBox": f"0 0 {width} {height}",
        "width": str(width),
        "height": str(height),
    })

    # Background
    SubElement(svg, "rect", {
        "width": str(width),
        "height": str(height),
        "fill": COLORS["background"],
    })

    # Offset for coordinate normalization
    ox = -min_x * CELL_SIZE + PADDING
    oy = -min_y * CELL_SIZE + PADDING

    loc_by_id = {loc["id"]: loc for loc in locations}

    # Draw locations
    for loc in locations:
        _draw_location(svg, loc, ox, oy)

    # Draw connections
    for conn in connections:
        loc_from = loc_by_id.get(conn["from"])
        loc_to = loc_by_id.get(conn["to"])
        if loc_from and loc_to:
            _draw_connection(svg, conn, loc_from, loc_to, ox, oy)

    return tostring(svg, encoding="unicode")


def _empty_svg() -> str:
    svg = Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "viewBox": "0 0 200 100",
        "width": "200",
        "height": "100",
    })
    SubElement(svg, "rect", {"width": "200", "height": "100", "fill": COLORS["background"]})
    text = SubElement(svg, "text", {
        "x": "100", "y": "55", "text-anchor": "middle",
        "fill": COLORS["text"], "font-size": "14",
    })
    text.text = "マップなし"
    return tostring(svg, encoding="unicode")


def _draw_location(svg: Element, loc: dict, ox: int, oy: int):
    area_type = loc.get("area_type", "indoor")
    colors = COLORS.get(area_type, COLORS["indoor"])

    x = loc.get("x", 0) * CELL_SIZE + ox
    y = loc.get("y", 0) * CELL_SIZE + oy
    w = loc.get("w", 1) * CELL_SIZE
    h = loc.get("h", 1) * CELL_SIZE

    attrs = {
        "x": str(x + 1),
        "y": str(y + 1),
        "width": str(w - 2),
        "height": str(h - 2),
        "fill": colors["fill"],
        "stroke": colors["stroke"],
        "stroke-width": str(WALL_WIDTH),
        "rx": "4",
    }
    if area_type == "outdoor":
        attrs["stroke-dasharray"] = "6,3"

    SubElement(svg, "rect", attrs)

    # Room name
    text = SubElement(svg, "text", {
        "x": str(x + w // 2),
        "y": str(y + h // 2 - 2),
        "text-anchor": "middle",
        "dominant-baseline": "central",
        "fill": COLORS["text"],
        "font-size": str(FONT_SIZE),
        "font-weight": "bold",
        "font-family": "sans-serif",
    })
    text.text = loc.get("name", loc["id"])

    # Features (small text below name)
    features = loc.get("features", [])
    if features:
        feature_text = "・".join(features[:3])
        ft = SubElement(svg, "text", {
            "x": str(x + w // 2),
            "y": str(y + h // 2 + FONT_SIZE),
            "text-anchor": "middle",
            "dominant-baseline": "central",
            "fill": COLORS["text_feature"],
            "font-size": str(FONT_SIZE - 3),
            "font-family": "sans-serif",
        })
        ft.text = feature_text


def _draw_connection(svg: Element, conn: dict, loc_from: dict, loc_to: dict, ox: int, oy: int):
    conn_type = conn.get("type", "door")

    # Calculate center points
    fx = loc_from.get("x", 0) * CELL_SIZE + loc_from.get("w", 1) * CELL_SIZE // 2 + ox
    fy = loc_from.get("y", 0) * CELL_SIZE + loc_from.get("h", 1) * CELL_SIZE // 2 + oy
    tx = loc_to.get("x", 0) * CELL_SIZE + loc_to.get("w", 1) * CELL_SIZE // 2 + ox
    ty = loc_to.get("y", 0) * CELL_SIZE + loc_to.get("h", 1) * CELL_SIZE // 2 + oy

    # Find midpoint (where the wall is)
    mx = (fx + tx) // 2
    my = (fy + ty) // 2

    color = COLORS.get(conn_type, COLORS["door"])

    if conn_type == "door":
        _draw_door_marker(svg, mx, my, fx, fy, tx, ty, color)
    elif conn_type == "window":
        _draw_window_marker(svg, mx, my, fx, fy, tx, ty, color)
    elif conn_type == "stairs":
        _draw_stairs_marker(svg, fx, fy, tx, ty, color)
    elif conn_type == "hidden_passage":
        _draw_hidden_marker(svg, mx, my, fx, fy, tx, ty)
    else:
        _draw_door_marker(svg, mx, my, fx, fy, tx, ty, color)


def _draw_door_marker(svg: Element, mx: int, my: int, fx: int, fy: int, tx: int, ty: int, color: str):
    is_horizontal = abs(fx - tx) > abs(fy - ty)
    half = DOOR_GAP // 2

    if is_horizontal:
        SubElement(svg, "line", {
            "x1": str(mx), "y1": str(my - half),
            "x2": str(mx), "y2": str(my + half),
            "stroke": color, "stroke-width": "3", "stroke-linecap": "round",
        })
    else:
        SubElement(svg, "line", {
            "x1": str(mx - half), "y1": str(my),
            "x2": str(mx + half), "y2": str(my),
            "stroke": color, "stroke-width": "3", "stroke-linecap": "round",
        })


def _draw_window_marker(svg: Element, mx: int, my: int, fx: int, fy: int, tx: int, ty: int, color: str):
    is_horizontal = abs(fx - tx) > abs(fy - ty)
    half = DOOR_GAP // 2

    if is_horizontal:
        SubElement(svg, "line", {
            "x1": str(mx), "y1": str(my - half),
            "x2": str(mx), "y2": str(my + half),
            "stroke": color, "stroke-width": "2",
            "stroke-dasharray": WINDOW_DASH, "stroke-linecap": "round",
        })
        SubElement(svg, "line", {
            "x1": str(mx - 2), "y1": str(my - half),
            "x2": str(mx - 2), "y2": str(my + half),
            "stroke": color, "stroke-width": "1",
            "stroke-dasharray": WINDOW_DASH, "stroke-linecap": "round",
        })
    else:
        SubElement(svg, "line", {
            "x1": str(mx - half), "y1": str(my),
            "x2": str(mx + half), "y2": str(my),
            "stroke": color, "stroke-width": "2",
            "stroke-dasharray": WINDOW_DASH, "stroke-linecap": "round",
        })
        SubElement(svg, "line", {
            "x1": str(mx - half), "y1": str(my - 2),
            "x2": str(mx + half), "y2": str(my - 2),
            "stroke": color, "stroke-width": "1",
            "stroke-dasharray": WINDOW_DASH, "stroke-linecap": "round",
        })


def _draw_stairs_marker(svg: Element, fx: int, fy: int, tx: int, ty: int, color: str):
    # Dashed line connecting the two rooms
    SubElement(svg, "line", {
        "x1": str(fx), "y1": str(fy),
        "x2": str(tx), "y2": str(ty),
        "stroke": color, "stroke-width": "2",
        "stroke-dasharray": "8,4", "stroke-linecap": "round",
    })
    # Stairs icon at midpoint
    mx = (fx + tx) // 2
    my = (fy + ty) // 2
    text = SubElement(svg, "text", {
        "x": str(mx), "y": str(my),
        "text-anchor": "middle", "dominant-baseline": "central",
        "fill": color, "font-size": "16",
    })
    text.text = "⇅"


def _draw_hidden_marker(svg: Element, mx: int, my: int, fx: int, fy: int, tx: int, ty: int):
    SubElement(svg, "line", {
        "x1": str(fx), "y1": str(fy),
        "x2": str(tx), "y2": str(ty),
        "stroke": "#666666", "stroke-width": "1",
        "stroke-dasharray": "2,6", "stroke-linecap": "round",
    })
    text = SubElement(svg, "text", {
        "x": str(mx), "y": str(my),
        "text-anchor": "middle", "dominant-baseline": "central",
        "fill": "#666666", "font-size": "12",
    })
    text.text = "?"
