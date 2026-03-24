async def test_create_room(client):
    response = await client.post("/api/v1/rooms", json={"display_name": "Alice"})
    assert response.status_code == 200
    data = response.json()
    assert "room_code" in data
    assert len(data["room_code"]) == 6
    assert "player_id" in data
    assert "session_token" in data


async def test_join_room(client):
    create_resp = await client.post("/api/v1/rooms", json={"display_name": "Alice"})
    room_code = create_resp.json()["room_code"]

    join_resp = await client.post(f"/api/v1/rooms/{room_code}/join", json={"display_name": "Bob"})
    assert join_resp.status_code == 200
    data = join_resp.json()
    assert "player_id" in data
    assert "session_token" in data


async def test_join_nonexistent_room(client):
    resp = await client.post("/api/v1/rooms/XXXXXX/join", json={"display_name": "Bob"})
    assert resp.status_code == 400


async def test_get_room(client):
    create_resp = await client.post("/api/v1/rooms", json={"display_name": "Alice"})
    room_code = create_resp.json()["room_code"]

    await client.post(f"/api/v1/rooms/{room_code}/join", json={"display_name": "Bob"})

    get_resp = await client.get(f"/api/v1/rooms/{room_code}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["room_code"] == room_code
    assert data["status"] == "waiting"
    assert len(data["players"]) == 2
    assert data["players"][0]["is_host"] is True


async def test_get_nonexistent_room(client):
    resp = await client.get("/api/v1/rooms/XXXXXX")
    assert resp.status_code == 404


async def test_room_max_players(client):
    create_resp = await client.post("/api/v1/rooms", json={"display_name": "Player1"})
    room_code = create_resp.json()["room_code"]

    for i in range(2, 8):
        resp = await client.post(f"/api/v1/rooms/{room_code}/join", json={"display_name": f"Player{i}"})
        assert resp.status_code == 200

    resp = await client.post(f"/api/v1/rooms/{room_code}/join", json={"display_name": "Player8"})
    assert resp.status_code == 400
    assert "full" in resp.json()["detail"].lower()


async def test_create_room_empty_name(client):
    resp = await client.post("/api/v1/rooms", json={"display_name": ""})
    assert resp.status_code == 422
