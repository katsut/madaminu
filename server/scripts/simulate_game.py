"""4-player game simulation via HTTP API + WebSocket.

Run against a local server:
  1. Start server: cd server && uv run uvicorn madaminu.main:app --reload
  2. Run simulation: cd server && uv run python scripts/simulate_game.py

Each player has an LLM "brain" that decides actions based on visible state.
"""

import asyncio
import json
import sys
import time

import httpx
import websockets

BASE_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000"

PLAYERS = [
    {"name": "Alice", "char_name": "桐生 真琴", "gender": "女", "age": "28", "occupation": "新聞記者",
     "personality": "直感的で行動力がある。正義感が強い", "background": "社会部の記者。不正を追う"},
    {"name": "Bob", "char_name": "高畑 龍介", "gender": "男", "age": "45", "occupation": "実業家",
     "personality": "冷静沈着で計算高い。表情を読まれない", "background": "投資会社の社長。自力で成り上がった"},
    {"name": "Charlie", "char_name": "水沢 結衣", "gender": "女", "age": "33", "occupation": "医師",
     "personality": "理知的で慎重。データで判断する", "background": "大学病院の内科医。研究にも従事"},
    {"name": "Dave", "char_name": "黒木 渉", "gender": "男", "age": "55", "occupation": "退職刑事",
     "personality": "経験豊富で観察力が鋭い。寡黙だが核心をつく", "background": "元警視庁捜査一課。昨年退職"},
]


class SimPlayer:
    def __init__(self, name: str, char_info: dict):
        self.name = name
        self.char_info = char_info
        self.token: str = ""
        self.player_id: str = ""
        self.ws: websockets.WebSocketClientProtocol | None = None
        self.state: dict = {}
        self.phase_type: str = ""
        self.discoveries: list[dict] = []
        self.evidences: list[dict] = []
        self.speech_history: list[str] = []
        self.secret_info: str = ""
        self.objective: str = ""
        self.role: str = ""
        self.locations: list[dict] = []
        self.messages: list[dict] = []

    def log(self, msg: str):
        print(f"  [{self.name}/{self.char_info['char_name']}] {msg}")


async def create_room(client: httpx.AsyncClient) -> str:
    resp = await client.post(f"{BASE_URL}/api/v1/rooms", json={"display_name": PLAYERS[0]["name"], "room_name": "シミュレーション"})
    resp.raise_for_status()
    data = resp.json()
    return data["room_code"], data["session_token"], data["player_id"]


async def join_room(client: httpx.AsyncClient, room_code: str, name: str) -> tuple[str, str]:
    resp = await client.post(f"{BASE_URL}/api/v1/rooms/{room_code}/join", json={"display_name": name})
    resp.raise_for_status()
    return resp.json()["session_token"], resp.json()["player_id"]


async def create_character(client: httpx.AsyncClient, room_code: str, token: str, info: dict):
    resp = await client.post(
        f"{BASE_URL}/api/v1/rooms/{room_code}/characters",
        json={
            "character_name": info["char_name"],
            "character_personality": info["personality"],
            "character_background": info["background"],
            "character_gender": info["gender"],
            "character_age": info["age"],
            "character_occupation": info["occupation"],
        },
        headers={"x-session-token": token},
    )
    resp.raise_for_status()


async def set_ready(client: httpx.AsyncClient, room_code: str, token: str):
    resp = await client.post(f"{BASE_URL}/api/v1/rooms/{room_code}/ready", headers={"x-session-token": token})
    resp.raise_for_status()


async def start_game(client: httpx.AsyncClient, room_code: str, host_token: str):
    resp = await client.post(f"{BASE_URL}/api/v1/rooms/{room_code}/start", headers={"x-session-token": host_token}, timeout=120)
    resp.raise_for_status()
    return resp.json()


async def get_state(client: httpx.AsyncClient, room_code: str, token: str) -> dict:
    resp = await client.get(f"{BASE_URL}/api/v1/rooms/{room_code}/state", headers={"x-session-token": token})
    resp.raise_for_status()
    return resp.json()


async def connect_ws(player: SimPlayer, room_code: str):
    uri = f"{WS_URL}/ws/{room_code}?token={player.token}"
    player.ws = await websockets.connect(uri)
    player.log("WS connected")


async def listen_ws(player: SimPlayer):
    """Listen for WS messages and update player state."""
    try:
        while True:
            raw = await asyncio.wait_for(player.ws.recv(), timeout=1.0)
            msg = json.loads(raw)
            msg_type = msg.get("type", "")
            data = msg.get("data", {})

            if msg_type == "game.state":
                player.state = data
                player.role = data.get("my_role", "")
                player.secret_info = data.get("my_secret_info", "")
                player.objective = data.get("my_objective", "")

            elif msg_type == "phase.started":
                player.phase_type = data.get("phase_type", "")
                player.discoveries = []
                locs = data.get("investigation_locations")
                if locs:
                    if isinstance(locs, str):
                        try:
                            locs = json.loads(locs)
                        except json.JSONDecodeError:
                            locs = []
                    player.locations = locs
                player.log(f"Phase: {player.phase_type} (turn {data.get('turn_number')}/{data.get('total_turns')})")

            elif msg_type == "phase.ended":
                pass

            elif msg_type == "investigate.discoveries":
                discs = data.get("discoveries")
                if isinstance(discs, str):
                    try:
                        discs = json.loads(discs)
                    except json.JSONDecodeError:
                        discs = []
                if discs:
                    player.discoveries = discs
                    player.log(f"Got {len(discs)} discoveries")

            elif msg_type == "investigate.kept":
                player.log(f"Kept: {data.get('title')}")

            elif msg_type == "speech.released":
                name = data.get("character_name", "?")
                text = data.get("transcript", "")
                if text:
                    player.speech_history.append(f"{name}: {text}")

            elif msg_type == "speech.ai":
                name = data.get("character_name", "?")
                text = data.get("transcript", "")
                if text:
                    player.speech_history.append(f"[AI]{name}: {text}")
                    player.log(f"AI speech: {name}: {text[:50]}...")

            elif msg_type == "vote.results":
                player.log(f"Vote results: {data.get('votes', {})}")

            elif msg_type == "game.ending":
                player.log(f"ENDING: {str(data.get('ending_text', ''))[:100]}...")
                player.log(f"True criminal: {data.get('true_criminal_id')}")

            elif msg_type == "error":
                player.log(f"ERROR: {data.get('message')}")

            player.messages.append(msg)

    except asyncio.TimeoutError:
        pass
    except websockets.ConnectionClosed:
        player.log("WS disconnected")


async def drain_ws(player: SimPlayer, duration: float = 2.0):
    """Listen for messages for a given duration."""
    end = time.monotonic() + duration
    while time.monotonic() < end:
        await listen_ws(player)


async def drain_all(players: list[SimPlayer], duration: float = 3.0):
    await asyncio.gather(*[drain_ws(p, duration) for p in players])


async def run_simulation():
    print("=" * 60)
    print("4-PLAYER GAME SIMULATION")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # === Setup ===
        print("\n--- 1. Room Setup ---")
        room_code, host_token, host_id = await create_room(client)
        print(f"Room: {room_code}")

        sim_players: list[SimPlayer] = []
        p0 = SimPlayer(PLAYERS[0]["name"], PLAYERS[0])
        p0.token = host_token
        p0.player_id = host_id
        sim_players.append(p0)

        for info in PLAYERS[1:]:
            token, pid = await join_room(client, room_code, info["name"])
            p = SimPlayer(info["name"], info)
            p.token = token
            p.player_id = pid
            sim_players.append(p)

        print(f"Players: {[p.name for p in sim_players]}")

        # === Characters ===
        print("\n--- 2. Character Creation ---")
        for p in sim_players:
            await create_character(client, room_code, p.token, p.char_info)
            p.log(f"Created: {p.char_info['char_name']}")

        # === Ready ===
        for p in sim_players[1:]:
            await set_ready(client, room_code, p.token)

        # === Connect WS ===
        print("\n--- 3. WebSocket Connect ---")
        for p in sim_players:
            await connect_ws(p, room_code)

        # === Start Game ===
        print("\n--- 4. Game Start ---")
        result = await start_game(client, room_code, host_token)
        print(f"Status: {result.get('status')}")

        # Wait for scenario generation
        print("Waiting for scenario generation...")
        await drain_all(sim_players, 10.0)

        # === Get State ===
        print("\n--- 5. Game State ---")
        for p in sim_players:
            state = await get_state(client, room_code, p.token)
            p.state = state
            p.role = state.get("my_role", "")
            p.secret_info = state.get("my_secret_info", "")
            p.objective = state.get("my_objective", "")
            p.log(f"Role: {p.role} | Secret: {p.secret_info[:30]}... | Objective: {p.objective[:30]}...")

        # === Game Loop ===
        print("\n--- 6. Game Loop ---")

        # Wait for phases to progress
        game_over = False
        max_wait = 300  # 5 minutes max
        start_time = time.monotonic()

        while not game_over and (time.monotonic() - start_time) < max_wait:
            await drain_all(sim_players, 2.0)

            # Check current phase for first player
            current_phase = sim_players[0].phase_type

            if current_phase == "planning":
                # Select a location
                for p in sim_players:
                    if p.locations:
                        # Pick based on role: criminal avoids crime scene, others investigate it
                        loc = p.locations[0]
                        for l in p.locations:
                            name = l.get("name", "")
                            if p.role == "criminal" and "書斎" not in name:
                                loc = l
                                break
                            elif p.role != "criminal" and ("書斎" in name or "study" in l.get("id", "")):
                                loc = l
                                break
                        await p.ws.send(json.dumps({"type": "investigate.select", "data": {"location_id": loc["id"]}}))
                        p.log(f"Selected: {loc.get('name', loc['id'])}")

                # Host advances after selection
                await asyncio.sleep(1)
                await sim_players[0].ws.send(json.dumps({"type": "phase.advance"}))
                p0.log("Advanced phase")
                await drain_all(sim_players, 5.0)

            elif current_phase == "investigation":
                await drain_all(sim_players, 3.0)
                # Keep first discovery if available
                for p in sim_players:
                    if p.discoveries:
                        disc = p.discoveries[0]
                        await p.ws.send(json.dumps({"type": "investigate.keep", "data": {"discovery_id": disc["id"]}}))
                        p.log(f"Keeping: {disc.get('title', '?')}")
                        await drain_ws(p, 1.0)

                await asyncio.sleep(1)
                await sim_players[0].ws.send(json.dumps({"type": "phase.advance"}))
                await drain_all(sim_players, 5.0)

            elif current_phase == "discussion":
                # Each player makes a speech based on what they know
                for p in sim_players:
                    await p.ws.send(json.dumps({"type": "speech.request"}))
                    await drain_ws(p, 0.5)

                    # Decide what to say based on role
                    if p.role == "criminal":
                        transcript = f"私は無実です。事件当時は別の場所にいました。"
                    elif p.role == "witness":
                        transcript = f"私が見たものは... いえ、何でもありません。"
                    else:
                        transcript = f"証拠を確認しましょう。何か気になる点があります。"

                    await p.ws.send(json.dumps({"type": "speech.release", "data": {"transcript": transcript}}))
                    p.log(f"Said: {transcript[:40]}...")
                    await drain_ws(p, 0.5)

                await asyncio.sleep(1)
                await sim_players[0].ws.send(json.dumps({"type": "phase.advance"}))
                await drain_all(sim_players, 5.0)

            elif current_phase == "voting":
                print("\n--- 7. Voting ---")
                # Each player votes based on suspicion
                for p in sim_players:
                    # Simple heuristic: vote for someone suspicious
                    # Criminal votes for random innocent
                    # Others try to find criminal based on speech patterns
                    suspects = [sp for sp in sim_players if sp.player_id != p.player_id]
                    if p.role == "criminal":
                        # Frame someone else
                        target = suspects[0]
                    else:
                        # Vote for the person who claimed innocence most defensively
                        target = suspects[-1]  # Simple heuristic

                    await p.ws.send(json.dumps({"type": "vote.submit", "data": {"suspect_player_id": target.player_id}}))
                    target_name = target.char_info["char_name"]
                    p.log(f"Voted for: {target_name}")
                    await drain_ws(p, 1.0)

                # Wait for ending
                await drain_all(sim_players, 15.0)
                game_over = True

            elif current_phase == "opening":
                # Self-introduction
                for p in sim_players:
                    await p.ws.send(json.dumps({"type": "speech.request"}))
                    await drain_ws(p, 0.5)
                    transcript = f"初めまして、{p.char_info['char_name']}と申します。{p.char_info['occupation']}をしています。"
                    await p.ws.send(json.dumps({"type": "speech.release", "data": {"transcript": transcript}}))
                    p.log(f"Intro: {transcript[:50]}...")
                    await drain_ws(p, 0.5)

                await asyncio.sleep(1)
                await sim_players[0].ws.send(json.dumps({"type": "phase.advance"}))
                await drain_all(sim_players, 3.0)

            else:
                # Unknown phase or waiting
                await drain_all(sim_players, 2.0)

        # === Summary ===
        print("\n" + "=" * 60)
        print("SIMULATION RESULTS")
        print("=" * 60)

        criminal = next((p for p in sim_players if p.role == "criminal"), None)
        if criminal:
            print(f"\nTrue criminal: {criminal.char_info['char_name']} ({criminal.name})")

        print("\nPlayer summary:")
        for p in sim_players:
            print(f"  {p.char_info['char_name']} ({p.name})")
            print(f"    Role: {p.role}")
            print(f"    Secret: {p.secret_info[:60]}...")
            print(f"    Objective: {p.objective[:60]}...")
            print(f"    Messages received: {len(p.messages)}")
            ending_msgs = [m for m in p.messages if m.get("type") == "game.ending"]
            if ending_msgs:
                ending = ending_msgs[0].get("data", {})
                print(f"    Ending received: Yes")
                print(f"    Arrested: {ending.get('arrested_name', '?')}")

        # Cleanup
        for p in sim_players:
            if p.ws:
                await p.ws.close()


if __name__ == "__main__":
    asyncio.run(run_simulation())
