"""Generate SVG floor-plan from graph-based map data.

Map structure (sugoroku style):
- Passage nodes (corridor, entrance, stairs) form the backbone
- Room nodes branch off passage nodes (dead ends)
- Stairs nodes connect floors
"""

from xml.etree.ElementTree import Element, SubElement, tostring

CELL = 44
PASSAGE_W = 44
PASSAGE_H = 18
PASSAGE_GAP = 36
BRANCH_GAP = 6
AREA_PAD = 8
AREA_HEADER = 20
INTER_GAP = 16
PADDING = 10
FONT_SIZE = 10
LEGEND_FONT_SIZE = 10

COLORS = {
    "indoor": {"stroke": "#6666bb", "header": "#3a3a5a", "bg": "#1a1a28"},
    "outdoor": {"stroke": "#55aa55", "header": "#2a4a2a", "bg": "#171f17"},
    "semi_outdoor": {"stroke": "#55aa88", "header": "#2a3a3a", "bg": "#181f1f"},
    "room": "#2d2d44",
    "room_stroke": "#7777bb",
    "room_outdoor": "#263626",
    "room_outdoor_stroke": "#55aa55",
    "passage": "#222238",
    "passage_stroke": "#444466",
    "entrance": "#2a2a3a",
    "entrance_stroke": "#cc9944",
    "stairs_fill": "#2a2240",
    "stairs_stroke": "#9977bb",
    "stairs_step": "#7755aa",
    "crime_scene": "#3a1515",
    "crime_scene_stroke": "#cc3333",
    "meeting": "#1a2a1a",
    "meeting_stroke": "#44aa66",
    "edge": "#444466",
    "branch_edge": "#555577",
    "text": "#e0e0e8",
    "text_dim": "#9999aa",
    "text_passage": "#8888aa",
    "background": "#111118",
    "highlight_fill": "#3d2d15",
    "highlight_stroke": "#ddaa44",
    "highlight_glow": "#ddaa4433",
    "floor_conn": "#9977bb",
}

AREA_ICONS = {"indoor": "🏠", "outdoor": "🌳", "semi_outdoor": "⛺"}


def render_map_svg(map_data: dict, highlight_room: str | None = None) -> str:
    areas = map_data.get("areas")
    if areas is None:
        return _render_flat_map(map_data, highlight_room)
    return _render_map(map_data, highlight_room)


def _node_size(node: dict) -> tuple[int, int]:
    """Return (width, height) in pixels based on node size and type."""
    ntype = node.get("type", "room")
    if ntype in ("passage", "entrance", "stairs"):
        return PASSAGE_W, PASSAGE_H
    size = node.get("size", 1)
    if size >= 4:
        return CELL * 2, CELL * 2
    if size >= 2:
        return CELL * 2, CELL
    return CELL, CELL


def _render_map(map_data: dict, highlight_room: str | None = None) -> str:
    areas = map_data.get("areas", [])
    connections = map_data.get("connections", [])
    floor_conns = map_data.get("floor_connections", [])
    if not floor_conns:
        floor_conns = [
            [c.get("from", ""), c.get("to", "")]
            for c in connections
            if c.get("type") == "stairs"
        ]

    if not areas:
        return _empty_svg()

    # Normalize: support both "nodes"/"edges" and "rooms"/"connections" formats
    for area in areas:
        if "nodes" not in area and "rooms" in area:
            area["nodes"] = area["rooms"]
        if "edges" not in area and "connections" not in area:
            area["edges"] = []

    # Build node lookup
    _type_map = {"corridor": "passage"}
    all_nodes: dict[str, dict] = {}
    for area in areas:
        for node in area.get("nodes", []):
            if "type" not in node:
                raw_type = node.get("room_type", "room")
                node["type"] = _type_map.get(raw_type, raw_type)
            all_nodes[node["id"]] = node

    # Layout each area
    area_blocks: list[dict] = []
    node_positions: dict[str, dict] = {}

    max_block_w = 0

    for area in areas:
        nodes = area.get("nodes", [])
        area_conns = area.get("connections", [])
        edges = area.get("edges", [])
        if not edges and area_conns:
            edges = [[c.get("from", ""), c.get("to", "")] for c in area_conns]
        if not edges and connections:
            node_ids = {n["id"] for n in nodes}
            edges = [[c.get("from", ""), c.get("to", "")] for c in connections if c.get("from") in node_ids and c.get("to") in node_ids]
        area_type = area.get("area_type", "indoor")

        # Find backbone: chain of passage/entrance/stairs nodes
        passage_ids = {n["id"] for n in nodes if n.get("type") in ("passage", "entrance", "stairs")}
        room_ids = {n["id"] for n in nodes if n.get("type") in ("room", "crime_scene", "meeting")}
        node_map = {n["id"]: n for n in nodes}

        # Build adjacency
        adj: dict[str, list[str]] = {n["id"]: [] for n in nodes}
        for e in edges:
            a, b = e[0], e[1]
            if a in adj and b in adj:
                adj[a].append(b)
                adj[b].append(a)

        # Find backbone order (BFS from entrance or first passage)
        backbone = _find_backbone(nodes, edges, passage_ids)
        if not backbone:
            backbone = [n["id"] for n in nodes]

        # Find which rooms branch from which backbone node
        backbone_set = set(backbone)
        branches: dict[str, list[str]] = {pid: [] for pid in backbone}
        assigned = set(backbone)
        for rid in room_ids:
            for nb in adj.get(rid, []):
                if nb in backbone_set:
                    branches.setdefault(nb, []).append(rid)
                    assigned.add(rid)
                    break

        # Assign unassigned rooms to their nearest backbone neighbor (BFS)
        for rid in room_ids - assigned:
            visited = {rid}
            queue = list(adj.get(rid, []))
            found = False
            while queue and not found:
                nid = queue.pop(0)
                if nid in visited:
                    continue
                visited.add(nid)
                if nid in backbone_set:
                    branches.setdefault(nid, []).append(rid)
                    assigned.add(rid)
                    found = True
                else:
                    queue.extend(adj.get(nid, []))

        # If still unassigned (disconnected), add to last backbone node
        for rid in room_ids - assigned:
            if backbone:
                branches.setdefault(backbone[-1], []).append(rid)

        # Calculate room placement: above and below backbone, stacked
        room_placement: dict[str, dict] = {}  # rid -> {"side": "above"|"below", "stack_index": int}
        max_above_stacks = 0
        max_below_stacks = 0
        for pid in backbone:
            rooms = branches.get(pid, [])
            above_idx = 0
            below_idx = 0
            for j, rid in enumerate(rooms):
                if j % 2 == 0:
                    room_placement[rid] = {"side": "above", "stack": above_idx}
                    above_idx += 1
                else:
                    room_placement[rid] = {"side": "below", "stack": below_idx}
                    below_idx += 1
            max_above_stacks = max(max_above_stacks, above_idx)
            max_below_stacks = max(max_below_stacks, below_idx)

        n_backbone = len(backbone)
        backbone_w = n_backbone * (PASSAGE_W + PASSAGE_GAP) - PASSAGE_GAP

        # Calculate max width considering branch rooms
        max_room_w = 0
        for pid in backbone:
            for rid in branches.get(pid, []):
                rw, _ = _node_size(node_map[rid])
                max_room_w = max(max_room_w, rw)
        content_w = max(backbone_w, n_backbone * max(PASSAGE_W + PASSAGE_GAP, max_room_w + BRANCH_GAP) - BRANCH_GAP) if max_room_w > 0 else backbone_w

        above_h = max_above_stacks * (CELL + BRANCH_GAP) if max_above_stacks else 0
        below_h = max_below_stacks * (CELL + BRANCH_GAP) if max_below_stacks else 0
        content_h = above_h + PASSAGE_H + below_h

        block_w = content_w + AREA_PAD * 2
        block_h = AREA_HEADER + content_h + AREA_PAD * 2
        if block_w > max_block_w:
            max_block_w = block_w

        area_blocks.append({
            "area": area, "backbone": backbone, "branches": branches,
            "node_map": node_map, "edges": edges, "room_placement": room_placement,
            "w": block_w, "h": block_h,
            "content_w": content_w,
            "above_h": above_h, "below_h": below_h,
            "area_type": area_type,
        })

    # Position blocks vertically
    y_cursor = PADDING
    for block in area_blocks:
        block["x"] = PADDING + (max_block_w - block["w"]) // 2
        block["y"] = y_cursor

        ox = block["x"] + AREA_PAD
        oy = block["y"] + AREA_HEADER + AREA_PAD
        above_h = block["above_h"]

        # Position backbone nodes (PASSAGE_W x PASSAGE_H, thin)
        for i, nid in enumerate(block["backbone"]):
            px = ox + i * (PASSAGE_W + PASSAGE_GAP)
            py = oy + above_h
            node_positions[nid] = {
                "x": px, "y": py, "w": PASSAGE_W, "h": PASSAGE_H,
                "cx": px + PASSAGE_W // 2, "cy": py + PASSAGE_H // 2,
                "is_backbone": True,
            }

        # Position room branches using room_placement
        rp = block["room_placement"]
        area_left = block["x"] + AREA_PAD
        area_right = block["x"] + block["w"] - AREA_PAD
        for pid in block["backbone"]:
            rooms = block["branches"].get(pid, [])
            pp = node_positions[pid]
            for rid in rooms:
                node = block["node_map"][rid]
                rw, rh = _node_size(node)
                rx = pp["cx"] - rw // 2
                rx = max(area_left, min(rx, area_right - rw))
                placement = rp.get(rid, {"side": "above", "stack": 0})
                stack = placement["stack"]
                if placement["side"] == "above":
                    ry = oy + above_h - (stack + 1) * (CELL + BRANCH_GAP)
                else:
                    ry = oy + above_h + PASSAGE_H + BRANCH_GAP + stack * (CELL + BRANCH_GAP)
                node_positions[rid] = {
                    "x": rx, "y": ry, "w": rw, "h": rh,
                    "cx": rx + rw // 2, "cy": ry + rh // 2,
                    "is_backbone": False,
                }

        y_cursor += block["h"] + INTER_GAP

    total_w = max_block_w + PADDING * 2
    legend_h = 36
    # Add space for floor connections
    floor_conn_h = len(floor_conns) * 8 if floor_conns else 0
    total_h = y_cursor + floor_conn_h + legend_h

    svg = Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "viewBox": f"0 0 {total_w} {total_h}",
        "width": str(total_w), "height": str(total_h),
        "role": "img", "aria-label": "マップ",
    })
    SubElement(svg, "title").text = "ゲームマップ"
    defs = SubElement(svg, "defs")
    _add_glow_filter(defs)
    SubElement(svg, "rect", {"width": str(total_w), "height": str(total_h), "fill": COLORS["background"]})

    # Draw floor connections first (behind everything)
    for fc in floor_conns:
        p1 = node_positions.get(fc[0])
        p2 = node_positions.get(fc[1])
        if p1 and p2:
            _draw_floor_connection(svg, p1, p2)

    # Draw area blocks
    for block in area_blocks:
        _draw_area(svg, block, node_positions, highlight_room)

    _draw_legend(svg, PADDING, total_h - legend_h + 4, total_w)
    return tostring(svg, encoding="unicode")


def _find_backbone(nodes, edges, passage_ids):
    """Find the backbone chain of passage nodes.

    Start from entrance (or non-stairs endpoint) so stairs end up last.
    """
    if not passage_ids:
        return [n["id"] for n in nodes]

    node_type_map = {n["id"]: n.get("type") for n in nodes}

    # Build passage-only adjacency
    adj: dict[str, list[str]] = {pid: [] for pid in passage_ids}
    for e in edges:
        a, b = e[0], e[1]
        if a in passage_ids and b in passage_ids:
            adj[a].append(b)
            adj[b].append(a)

    # Pick start node: prefer entrance, then non-stairs endpoint
    start = None
    for n in nodes:
        if n.get("type") == "entrance" and n["id"] in passage_ids:
            start = n["id"]
            break

    if not start:
        # Pick a degree-1 node that is NOT stairs
        for pid in passage_ids:
            if len(adj[pid]) <= 1 and node_type_map.get(pid) != "stairs":
                start = pid
                break
        # If all degree-1 nodes are stairs, just pick any non-stairs
        if not start:
            for pid in passage_ids:
                if node_type_map.get(pid) != "stairs":
                    start = pid
                    break
        if not start:
            start = next(iter(passage_ids))

    # BFS to build chain
    visited = set()
    chain = []
    queue = [start]
    while queue:
        nid = queue.pop(0)
        if nid in visited:
            continue
        visited.add(nid)
        chain.append(nid)
        for nb in adj[nid]:
            if nb not in visited:
                queue.append(nb)

    # Add any disconnected passage nodes not yet visited
    for pid in passage_ids:
        if pid not in visited:
            chain.append(pid)

    return chain


def _draw_area(svg, block, node_pos, highlight_room):
    area = block["area"]
    area_type = block["area_type"]
    colors = COLORS.get(area_type, COLORS["indoor"])

    g = SubElement(svg, "g", {"role": "group", "aria-label": area.get("name", area["id"])})

    # Background
    SubElement(g, "rect", {
        "x": str(block["x"]), "y": str(block["y"]),
        "width": str(block["w"]), "height": str(block["h"]),
        "fill": colors["bg"], "stroke": colors["stroke"],
        "stroke-width": "2", "rx": "8",
        **({"stroke-dasharray": "8,4"} if area_type == "outdoor" else {}),
    })

    # Header
    SubElement(g, "rect", {
        "x": str(block["x"]), "y": str(block["y"]),
        "width": str(block["w"]), "height": str(AREA_HEADER),
        "fill": colors["header"], "rx": "8",
    })
    SubElement(g, "rect", {
        "x": str(block["x"]), "y": str(block["y"] + AREA_HEADER - 8),
        "width": str(block["w"]), "height": "8", "fill": colors["header"],
    })
    icon = AREA_ICONS.get(area_type, "")
    lbl = f"{icon} {area.get('name', area['id'])}" if icon else area.get("name", area["id"])
    SubElement(g, "text", {
        "x": str(block["x"] + block["w"] // 2),
        "y": str(block["y"] + AREA_HEADER // 2 + 1),
        "text-anchor": "middle", "dominant-baseline": "central",
        "fill": COLORS["text"], "font-size": str(FONT_SIZE + 1),
        "font-weight": "bold", "font-family": "sans-serif",
    }).text = lbl

    node_map = block["node_map"]
    backbone = block["backbone"]
    branches = block["branches"]

    # Draw backbone nodes first (so edges draw on top)
    for nid in backbone:
        node = node_map[nid]
        pos = node_pos[nid]
        _draw_node(g, node, pos, highlight_room == nid, area_type)

    # Draw room nodes
    for pid in backbone:
        for rid in branches.get(pid, []):
            node = node_map[rid]
            pos = node_pos[rid]
            _draw_node(g, node, pos, highlight_room == rid, area_type)

    # Draw backbone edges (on top of nodes, between them)
    for i in range(len(backbone) - 1):
        p1 = node_pos[backbone[i]]
        p2 = node_pos[backbone[i + 1]]
        x1 = p1["x"] + p1["w"]
        x2 = p2["x"]
        cy = p1["cy"]
        if x2 > x1:
            SubElement(g, "line", {
                "x1": str(x1), "y1": str(cy),
                "x2": str(x2), "y2": str(p2["cy"]),
                "stroke": COLORS["edge"], "stroke-width": "3",
                "stroke-linecap": "round",
            })

    # Draw branch edges (passage → room, visible on top)
    for pid in backbone:
        pp = node_pos[pid]
        for rid in branches.get(pid, []):
            rp = node_pos[rid]
            if rp["y"] < pp["y"]:
                # Room is above
                y1 = pp["y"]
                y2 = rp["y"] + rp["h"]
            else:
                # Room is below
                y1 = pp["y"] + pp["h"]
                y2 = rp["y"]
            SubElement(g, "line", {
                "x1": str(pp["cx"]), "y1": str(y1),
                "x2": str(rp["cx"]), "y2": str(y2),
                "stroke": COLORS["branch_edge"], "stroke-width": "2",
                "stroke-linecap": "round",
            })


def _draw_node(svg, node, pos, highlighted, area_type):
    ntype = node.get("type", "room")
    name = node.get("name", node["id"])
    x, y, w, h = pos["x"], pos["y"], pos["w"], pos["h"]

    rg = SubElement(svg, "g", {"role": "img", "aria-label": name})

    if highlighted:
        SubElement(rg, "rect", {
            "x": str(x - 3), "y": str(y - 3),
            "width": str(w + 6), "height": str(h + 6),
            "fill": COLORS["highlight_glow"], "rx": "6",
            "filter": "url(#glow)",
        })

    if ntype == "passage":
        fill = COLORS["passage"]
        stroke = COLORS["passage_stroke"]
    elif ntype == "entrance":
        fill = COLORS["entrance"]
        stroke = COLORS["entrance_stroke"]
    elif ntype == "stairs":
        fill = COLORS["stairs_fill"]
        stroke = COLORS["stairs_stroke"]
    elif ntype == "crime_scene":
        fill = COLORS["crime_scene"]
        stroke = COLORS["crime_scene_stroke"]
    elif ntype == "meeting":
        fill = COLORS["meeting"]
        stroke = COLORS["meeting_stroke"]
    elif area_type == "outdoor":
        fill = COLORS["room_outdoor"]
        stroke = COLORS["room_outdoor_stroke"]
    else:
        fill = COLORS["room"]
        stroke = COLORS["room_stroke"]

    sw = "2"
    if ntype in ("crime_scene", "meeting"):
        sw = "3"

    if highlighted:
        fill = COLORS["highlight_fill"]
        stroke = COLORS["highlight_stroke"]

    SubElement(rg, "rect", {
        "x": str(x), "y": str(y),
        "width": str(w), "height": str(h),
        "fill": fill, "stroke": stroke,
        "stroke-width": sw, "rx": "4",
    })

    # Crime scene marker
    if ntype == "crime_scene" and not highlighted:
        SubElement(rg, "text", {
            "x": str(x + 6), "y": str(y + 10),
            "fill": COLORS["crime_scene_stroke"], "font-size": "10",
        }).text = "☠"

    # Meeting room marker
    if ntype == "meeting" and not highlighted:
        SubElement(rg, "text", {
            "x": str(x + 6), "y": str(y + 10),
            "fill": COLORS["meeting_stroke"], "font-size": "10",
        }).text = "👥"

    # Stairs decoration
    if ntype == "stairs" and not highlighted:
        for s in range(1, 4):
            sy = y + s * h // 4
            SubElement(rg, "line", {
                "x1": str(x + 6), "y1": str(sy),
                "x2": str(x + w - 6), "y2": str(sy),
                "stroke": COLORS["stairs_step"], "stroke-width": "1",
            })

    text_color = COLORS["text"] if ntype == "room" else COLORS["text_passage"]
    if highlighted:
        text_color = COLORS["text"]
    SubElement(rg, "text", {
        "x": str(x + w // 2), "y": str(y + h // 2 + 1),
        "text-anchor": "middle", "dominant-baseline": "central",
        "fill": text_color, "font-size": str(FONT_SIZE if ntype == "room" else FONT_SIZE - 1),
        "font-weight": "bold", "font-family": "sans-serif",
    }).text = name


def _draw_floor_connection(svg, p1, p2):
    """Draw a vertical dashed line connecting stairs between floors."""
    x1, y1 = p1["cx"], p1["y"] + p1["h"]
    x2, y2 = p2["cx"], p2["y"]
    if y1 > y2:
        x1, y1, x2, y2 = x2, p2["y"] + p2["h"], x1, p1["y"]

    mx = (x1 + x2) // 2
    SubElement(svg, "line", {
        "x1": str(x1), "y1": str(y1),
        "x2": str(x2), "y2": str(y2),
        "stroke": COLORS["floor_conn"], "stroke-width": "2",
        "stroke-dasharray": "6,4",
    })


def _add_glow_filter(defs):
    filt = SubElement(defs, "filter", {"id": "glow", "x": "-30%", "y": "-30%", "width": "160%", "height": "160%"})
    SubElement(filt, "feGaussianBlur", {"in": "SourceGraphic", "stdDeviation": "4", "result": "blur"})
    merge = SubElement(filt, "feMerge")
    SubElement(merge, "feMergeNode", {"in": "blur"})
    SubElement(merge, "feMergeNode", {"in": "SourceGraphic"})


def _draw_legend(svg, x, y, total_w):
    SubElement(svg, "line", {
        "x1": str(x), "y1": str(y - 4),
        "x2": str(total_w - x), "y2": str(y - 4),
        "stroke": "#333344", "stroke-width": "1",
    })
    cx = x + 8
    items = [
        (COLORS["room"], COLORS["room_stroke"], "部屋"),
        (COLORS["passage"], COLORS["passage_stroke"], "廊下"),
        (COLORS["entrance"], COLORS["entrance_stroke"], "玄関"),
        (COLORS["stairs_fill"], COLORS["stairs_stroke"], "階段"),
        (COLORS["crime_scene"], COLORS["crime_scene_stroke"], "☠現場"),
        (COLORS["meeting"], COLORS["meeting_stroke"], "👥集合"),
    ]
    for fill, stroke, label in items:
        SubElement(svg, "rect", {
            "x": str(cx), "y": str(y + 2), "width": "14", "height": "10",
            "fill": fill, "stroke": stroke, "stroke-width": "1", "rx": "2",
        })
        SubElement(svg, "text", {
            "x": str(cx + 20), "y": str(y + 8),
            "dominant-baseline": "central",
            "fill": COLORS["text_dim"], "font-size": str(LEGEND_FONT_SIZE), "font-family": "sans-serif",
        }).text = label
        cx += 56


def _render_flat_map(map_data: dict, highlight_room: str | None = None) -> str:
    locations = map_data.get("locations", [])
    if not locations:
        return _empty_svg()
    nodes = [{"id": loc["id"], "name": loc.get("name", loc["id"]), "type": "room", "features": loc.get("features", [])} for loc in locations]
    edges = [[c["from"], c["to"]] for c in map_data.get("connections", [])]
    return _render_map({
        "areas": [{"id": "main", "name": "マップ", "area_type": "indoor", "nodes": nodes, "edges": edges}],
    }, highlight_room)


def _empty_svg() -> str:
    svg = Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "viewBox": "0 0 200 100", "width": "200", "height": "100",
    })
    SubElement(svg, "rect", {"width": "200", "height": "100", "fill": COLORS["background"]})
    SubElement(svg, "text", {
        "x": "100", "y": "55", "text-anchor": "middle",
        "fill": COLORS["text"], "font-size": "14",
    }).text = "マップなし"
    return tostring(svg, encoding="unicode")
