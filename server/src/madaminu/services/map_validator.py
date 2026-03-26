"""Validate map structure consistency for generated scenarios."""


VALID_CONNECTION_TYPES = {"door", "corridor", "stairs", "window", "hidden_passage"}
VALID_AREA_TYPES = {"indoor", "outdoor", "semi_outdoor"}
VALID_SIDES = {"north", "south", "east", "west"}


def validate_map(scenario: dict) -> list[str]:
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

    # Validate each location
    for loc in locations:
        if not loc.get("id"):
            errors.append(f"Location missing 'id': {loc}")
        if not loc.get("name"):
            errors.append(f"Location missing 'name': {loc}")
        if not loc.get("features"):
            errors.append(f"Location '{loc.get('id')}' has no features")
        area_type = loc.get("area_type", "indoor")
        if area_type not in VALID_AREA_TYPES:
            errors.append(f"Location '{loc.get('id')}' has invalid area_type: {area_type}")

    # Validate connections
    for conn in connections:
        if conn["from"] not in location_ids:
            errors.append(f"Connection 'from' references unknown location: {conn['from']}")
        if conn["to"] not in location_ids:
            errors.append(f"Connection 'to' references unknown location: {conn['to']}")
        if conn.get("type") and conn["type"] not in VALID_CONNECTION_TYPES:
            errors.append(f"Unknown connection type: {conn['type']}")
        if conn.get("side") and conn["side"] not in VALID_SIDES:
            errors.append(f"Invalid connection side: {conn['side']}")

    # Check isolated locations
    connected_ids = set()
    for conn in connections:
        connected_ids.add(conn["from"])
        connected_ids.add(conn["to"])
    isolated = location_ids - connected_ids
    for loc_id in isolated:
        errors.append(f"Isolated location (no connections): {loc_id}")

    # Check grid overlaps
    errors.extend(_check_grid_overlaps(locations))

    # Check connection adjacency on grid
    errors.extend(_check_connection_adjacency(locations, connections))

    # Check phase references
    for phase in scenario.get("phases", []):
        for loc_ref in phase.get("investigation_locations", []):
            ref_id = loc_ref if isinstance(loc_ref, str) else loc_ref.get("id")
            if ref_id not in location_ids:
                errors.append(f"Phase references unknown location: {ref_id}")

    return errors


def _get_grid_cells(loc: dict) -> set[tuple[int, int]]:
    """Return all grid cells occupied by a location."""
    x = loc.get("x", 0)
    y = loc.get("y", 0)
    w = loc.get("w", 1)
    h = loc.get("h", 1)
    cells = set()
    for dx in range(w):
        for dy in range(h):
            cells.add((x + dx, y + dy))
    return cells


def _check_grid_overlaps(locations: list[dict]) -> list[str]:
    """Check that no two locations overlap on the grid."""
    errors = []
    has_grid = any("x" in loc for loc in locations)
    if not has_grid:
        return errors

    occupied: dict[tuple[int, int], str] = {}
    for loc in locations:
        if "x" not in loc:
            continue
        cells = _get_grid_cells(loc)
        for cell in cells:
            if cell in occupied:
                errors.append(
                    f"Grid overlap at ({cell[0]},{cell[1]}): "
                    f"'{loc['id']}' and '{occupied[cell]}'"
                )
            else:
                occupied[cell] = loc["id"]
    return errors


def _are_adjacent(loc_a: dict, loc_b: dict) -> bool:
    """Check if two locations are adjacent on the grid (share an edge)."""
    cells_a = _get_grid_cells(loc_a)
    cells_b = _get_grid_cells(loc_b)
    for ax, ay in cells_a:
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            if (ax + dx, ay + dy) in cells_b:
                return True
    return False


def _check_connection_adjacency(locations: list[dict], connections: list[dict]) -> list[str]:
    """Check that connected locations are adjacent on the grid (except stairs)."""
    errors = []
    has_grid = any("x" in loc for loc in locations)
    if not has_grid:
        return errors

    loc_by_id = {loc["id"]: loc for loc in locations if "x" in loc}

    for conn in connections:
        # stairs can connect non-adjacent locations (different floors)
        if conn.get("type") == "stairs":
            continue
        loc_a = loc_by_id.get(conn["from"])
        loc_b = loc_by_id.get(conn["to"])
        if loc_a is None or loc_b is None:
            continue
        if not _are_adjacent(loc_a, loc_b):
            errors.append(
                f"Connection '{conn['from']}' -> '{conn['to']}' ({conn.get('type', '?')}) "
                f"but locations are not adjacent on grid"
            )
    return errors
