"""Validate map structure consistency for generated scenarios."""


VALID_CONNECTION_TYPES = {"door", "corridor", "stairs", "window", "hidden_passage"}
VALID_AREA_TYPES = {"indoor", "outdoor", "semi_outdoor"}


def validate_map(scenario: dict) -> list[str]:
    """Validate map structure consistency. Returns list of error messages."""
    errors = []
    map_data = scenario.get("map")
    if map_data is None:
        errors.append("Missing 'map' in scenario")
        return errors

    # Support both hierarchical and flat format
    if "areas" in map_data:
        errors.extend(_validate_hierarchical(map_data, scenario))
    elif "locations" in map_data:
        errors.extend(_validate_flat(map_data, scenario))
    else:
        errors.append("Map has neither 'areas' nor 'locations'")

    return errors


def _validate_hierarchical(map_data: dict, scenario: dict) -> list[str]:
    errors = []
    areas = map_data.get("areas", [])
    connections = map_data.get("connections", [])

    all_room_ids = set()
    room_to_area = {}

    for area in areas:
        area_type = area.get("area_type", "indoor")
        if area_type not in VALID_AREA_TYPES:
            errors.append(f"Area '{area.get('id')}' has invalid area_type: {area_type}")

        rooms = area.get("rooms", [])
        if not rooms:
            errors.append(f"Area '{area.get('id')}' has no rooms")

        for room in rooms:
            rid = room.get("id")
            if not rid:
                errors.append(f"Room missing 'id' in area '{area.get('id')}'")
                continue
            if rid in all_room_ids:
                errors.append(f"Duplicate room id: {rid}")
            all_room_ids.add(rid)
            room_to_area[rid] = area.get("id")

            if not room.get("name"):
                errors.append(f"Room '{rid}' missing 'name'")
            if not room.get("features"):
                errors.append(f"Room '{rid}' has no features")

    if len(all_room_ids) < 4:
        errors.append(f"Too few rooms: {len(all_room_ids)} (minimum 10)")

    connected_ids = set()
    for conn in connections:
        from_id = conn.get("from", "")
        to_id = conn.get("to", "")
        if from_id not in all_room_ids:
            errors.append(f"Connection 'from' references unknown room: {from_id}")
        if to_id not in all_room_ids:
            errors.append(f"Connection 'to' references unknown room: {to_id}")
        conn_type = conn.get("type", "")
        if conn_type and conn_type not in VALID_CONNECTION_TYPES:
            errors.append(f"Unknown connection type: {conn_type}")
        connected_ids.add(from_id)
        connected_ids.add(to_id)

    isolated = all_room_ids - connected_ids
    for rid in isolated:
        errors.append(f"Isolated room (no connections): {rid}")

    for phase in scenario.get("phases", []):
        for loc_ref in phase.get("investigation_locations", []):
            ref_id = loc_ref if isinstance(loc_ref, str) else loc_ref.get("id")
            if ref_id not in all_room_ids:
                errors.append(f"Phase references unknown room: {ref_id}")

    return errors


def _validate_flat(map_data: dict, scenario: dict) -> list[str]:
    """Validate old flat format."""
    errors = []
    locations = map_data.get("locations", [])
    connections = map_data.get("connections", [])
    location_ids = {loc["id"] for loc in locations}

    if len(location_ids) < 4:
        errors.append(f"Too few locations: {len(location_ids)} (minimum 4)")

    for loc in locations:
        if not loc.get("id"):
            errors.append(f"Location missing 'id': {loc}")
        if not loc.get("name"):
            errors.append(f"Location missing 'name': {loc}")
        if not loc.get("features"):
            errors.append(f"Location '{loc.get('id')}' has no features")

    for conn in connections:
        if conn["from"] not in location_ids:
            errors.append(f"Connection 'from' references unknown location: {conn['from']}")
        if conn["to"] not in location_ids:
            errors.append(f"Connection 'to' references unknown location: {conn['to']}")
        if conn.get("type") and conn["type"] not in VALID_CONNECTION_TYPES:
            errors.append(f"Unknown connection type: {conn['type']}")

    connected_ids = set()
    for conn in connections:
        connected_ids.add(conn["from"])
        connected_ids.add(conn["to"])
    for loc_id in location_ids - connected_ids:
        errors.append(f"Isolated location (no connections): {loc_id}")

    for phase in scenario.get("phases", []):
        for loc_ref in phase.get("investigation_locations", []):
            ref_id = loc_ref if isinstance(loc_ref, str) else loc_ref.get("id")
            if ref_id not in location_ids:
                errors.append(f"Phase references unknown location: {ref_id}")

    return errors
