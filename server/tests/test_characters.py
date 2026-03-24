async def test_create_character(client):
    room_resp = await client.post("/api/v1/rooms", json={"display_name": "Alice"})
    room_code = room_resp.json()["room_code"]
    token = room_resp.json()["session_token"]

    resp = await client.post(
        f"/api/v1/rooms/{room_code}/characters",
        json={
            "character_name": "Detective Smith",
            "character_personality": "Calm and analytical",
            "character_background": "A retired detective who was called back for one last case.",
        },
        headers={"x-session-token": token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["character_name"] == "Detective Smith"
    assert data["character_personality"] == "Calm and analytical"


async def test_create_character_visible_in_room(client):
    room_resp = await client.post("/api/v1/rooms", json={"display_name": "Alice"})
    room_code = room_resp.json()["room_code"]
    token = room_resp.json()["session_token"]

    await client.post(
        f"/api/v1/rooms/{room_code}/characters",
        json={
            "character_name": "Detective Smith",
            "character_personality": "Calm",
            "character_background": "Retired detective",
        },
        headers={"x-session-token": token},
    )

    room_info = await client.get(f"/api/v1/rooms/{room_code}")
    players = room_info.json()["players"]
    assert players[0]["character_name"] == "Detective Smith"


async def test_create_character_invalid_token(client):
    room_resp = await client.post("/api/v1/rooms", json={"display_name": "Alice"})
    room_code = room_resp.json()["room_code"]

    resp = await client.post(
        f"/api/v1/rooms/{room_code}/characters",
        json={
            "character_name": "X",
            "character_personality": "Y",
            "character_background": "Z",
        },
        headers={"x-session-token": "bad-token"},
    )
    assert resp.status_code == 401


async def test_create_character_nonexistent_room(client):
    resp = await client.post(
        "/api/v1/rooms/XXXXXX/characters",
        json={
            "character_name": "X",
            "character_personality": "Y",
            "character_background": "Z",
        },
        headers={"x-session-token": "some-token"},
    )
    assert resp.status_code == 404


async def test_create_character_empty_name(client):
    room_resp = await client.post("/api/v1/rooms", json={"display_name": "Alice"})
    room_code = room_resp.json()["room_code"]
    token = room_resp.json()["session_token"]

    resp = await client.post(
        f"/api/v1/rooms/{room_code}/characters",
        json={
            "character_name": "",
            "character_personality": "Calm",
            "character_background": "Detective",
        },
        headers={"x-session-token": token},
    )
    assert resp.status_code == 422
