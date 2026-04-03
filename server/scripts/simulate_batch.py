"""Run simulate_game.py N times and collect stats."""

import asyncio
import json
import time

import httpx
import websockets

BASE_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000"

PLAYERS = [
    {"name": "Alice", "char_name": "桐生 真琴", "gender": "女", "age": "28", "occupation": "新聞記者",
     "personality": "直感的で行動力がある。正義感が強い", "background": "社会部の記者。不正を追う"},
    {"name": "Bob", "char_name": "高畑 龍介", "gender": "男", "age": "45", "occupation": "実業家",
     "personality": "冷静沈着で計算高い。表情を読まれない", "background": "投資会社の社長"},
    {"name": "Charlie", "char_name": "水沢 結衣", "gender": "女", "age": "33", "occupation": "医師",
     "personality": "理知的で慎重。データで判断する", "background": "大学病院の内科医"},
    {"name": "Dave", "char_name": "黒木 渉", "gender": "男", "age": "55", "occupation": "退職刑事",
     "personality": "経験豊富で観察力が鋭い", "background": "元警視庁捜査一課"},
]


class Player:
    def __init__(self, name, char_info):
        self.name = name
        self.char_info = char_info
        self.token = ""
        self.player_id = ""
        self.ws = None
        self.phase_type = ""
        self.role = ""
        self.secret_info = ""
        self.objective = ""
        self.locations = []
        self.discoveries = []
        self.ending_data = None
        self.messages = []

    async def drain(self, duration=1.0):
        try:
            end = time.monotonic() + duration
            while time.monotonic() < end:
                raw = await asyncio.wait_for(self.ws.recv(), timeout=0.5)
                msg = json.loads(raw)
                self.messages.append(msg)
                t = msg.get("type", "")
                d = msg.get("data", {})
                if t == "game.state":
                    self.role = d.get("my_role", "") or ""
                    self.secret_info = d.get("my_secret_info", "") or ""
                    self.objective = d.get("my_objective", "") or ""
                elif t == "phase.started":
                    self.phase_type = d.get("phase_type", "")
                    self.discoveries = []
                    locs = d.get("investigation_locations")
                    if locs:
                        if isinstance(locs, str):
                            try: locs = json.loads(locs)
                            except: locs = []
                        self.locations = locs
                elif t == "investigate.discoveries":
                    discs = d.get("discoveries")
                    if isinstance(discs, str):
                        try: discs = json.loads(discs)
                        except: discs = []
                    if discs:
                        self.discoveries = discs
                elif t == "game.ending":
                    self.ending_data = d
        except (asyncio.TimeoutError, websockets.ConnectionClosed):
            pass


async def drain_all(players, duration=1.0):
    await asyncio.gather(*[p.drain(duration) for p in players])


async def wait_phase(players, phase, timeout=60):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        await drain_all(players, 1.0)
        if all(p.phase_type == phase for p in players):
            return True
    return False


async def run_one_game(game_num):
    print(f"\n{'='*50}")
    print(f"GAME {game_num}")
    print(f"{'='*50}")

    async with httpx.AsyncClient() as client:
        # Setup
        resp = await client.post(f"{BASE_URL}/api/v1/rooms", json={"display_name": PLAYERS[0]["name"]})
        resp.raise_for_status()
        room_code = resp.json()["room_code"]
        players = []
        p0 = Player(PLAYERS[0]["name"], PLAYERS[0])
        p0.token = resp.json()["session_token"]
        p0.player_id = resp.json()["player_id"]
        players.append(p0)

        for info in PLAYERS[1:]:
            r = await client.post(f"{BASE_URL}/api/v1/rooms/{room_code}/join", json={"display_name": info["name"]})
            r.raise_for_status()
            p = Player(info["name"], info)
            p.token = r.json()["session_token"]
            p.player_id = r.json()["player_id"]
            players.append(p)

        # Characters
        char_map = {p.name: p.char_info["char_name"] for p in players}
        for p in players:
            await client.post(
                f"{BASE_URL}/api/v1/rooms/{room_code}/characters",
                json={"character_name": p.char_info["char_name"], "character_personality": p.char_info["personality"], "character_background": p.char_info["background"],
                      "character_gender": p.char_info["gender"], "character_age": p.char_info["age"], "character_occupation": p.char_info["occupation"]},
                headers={"x-session-token": p.token},
            )

        # Ready
        for p in players[1:]:
            await client.post(f"{BASE_URL}/api/v1/rooms/{room_code}/ready", headers={"x-session-token": p.token})

        # WS connect
        for p in players:
            p.ws = await websockets.connect(f"{WS_URL}/ws/{room_code}?token={p.token}")

        # Start
        await client.post(f"{BASE_URL}/api/v1/rooms/{room_code}/start", headers={"x-session-token": players[0].token}, timeout=120)

        # Wait for game ready
        for _ in range(40):
            await drain_all(players, 2.0)
            try:
                state = await client.get(f"{BASE_URL}/api/v1/rooms/{room_code}/state", headers={"x-session-token": players[0].token})
                if state.json().get("status") == "playing":
                    break
            except:
                pass

        # Get state (retry until roles are populated)
        for _ in range(5):
            for p in players:
                s = await client.get(f"{BASE_URL}/api/v1/rooms/{room_code}/state", headers={"x-session-token": p.token})
                d = s.json()
                p.role = d.get("my_role", "") or ""
                p.secret_info = d.get("my_secret_info", "") or ""
                p.objective = d.get("my_objective", "") or ""
            if all(p.role for p in players):
                break
            await asyncio.sleep(2)

        criminal = next((p for p in players if p.role == "criminal"), None)
        print(f"  Criminal: {criminal.char_info['char_name'] if criminal else '?'}", flush=True)

        # Wait for opening
        await wait_phase(players, "opening", 30)

        # Opening: intro
        for p in players:
            await p.ws.send(json.dumps({"type": "speech.request"}))
            await asyncio.sleep(0.2)
            await p.ws.send(json.dumps({"type": "speech.release", "data": {"transcript": f"私は{p.char_info['char_name']}です。{p.char_info['occupation']}をしています。"}}))
            await asyncio.sleep(0.3)

        # 3 turns
        for turn in range(3):
            # Planning
            await players[0].ws.send(json.dumps({"type": "phase.advance"}))
            await wait_phase(players, "planning", 30)
            await drain_all(players, 2.0)

            for p in players:
                if p.locations:
                    loc = p.locations[0]
                    if p.role == "criminal":
                        for l in p.locations:
                            if "資料" not in l.get("name", "") and "study" not in l.get("id", ""):
                                loc = l
                                break
                    await p.ws.send(json.dumps({"type": "investigate.select", "data": {"location_id": loc["id"]}}))

            # Investigation
            await players[0].ws.send(json.dumps({"type": "phase.advance"}))
            await wait_phase(players, "investigation", 60)
            await drain_all(players, 8.0)

            for p in players:
                if p.discoveries:
                    d = p.discoveries[0]
                    if isinstance(d, dict) and "id" in d:
                        await p.ws.send(json.dumps({"type": "investigate.keep", "data": {"discovery_id": d["id"]}}))
                        await p.drain(1.0)

            # Discussion
            await players[0].ws.send(json.dumps({"type": "phase.advance"}))
            await wait_phase(players, "discussion", 30)

            for p in players:
                await p.ws.send(json.dumps({"type": "speech.request"}))
                await asyncio.sleep(0.2)
                if p.role == "criminal":
                    text = "私は無実です。事件当時は別の場所にいました。"
                elif p.role == "witness":
                    text = "何か不審な物音を聞いた気がしますが..."
                else:
                    text = "証拠を整理して、犯人を特定しましょう。"
                await p.ws.send(json.dumps({"type": "speech.release", "data": {"transcript": text}}))
                await asyncio.sleep(0.3)

        # Voting
        await players[0].ws.send(json.dumps({"type": "phase.advance"}))
        await wait_phase(players, "voting", 30)
        await asyncio.sleep(1)

        for p in players:
            suspects = [s for s in players if s.player_id != p.player_id]
            if p.role == "criminal":
                target = next((s for s in suspects if s.role == "innocent"), suspects[0])
            else:
                target = next((s for s in suspects if s.role == "criminal"), suspects[-1])
            await p.ws.send(json.dumps({"type": "vote.submit", "data": {"suspect_player_id": target.player_id}}))
            await asyncio.sleep(0.5)

        # Wait for ending (retry until at least one player has it)
        for _ in range(30):
            await drain_all(players, 2.0)
            if any(p.ending_data for p in players):
                break

        # Collect results
        ending = next((p.ending_data for p in players if p.ending_data), {}) or {}
        arrested = ending.get("arrested_name")
        true_criminal_name = criminal.char_info["char_name"] if criminal else None
        caught = bool(arrested and true_criminal_name and arrested == true_criminal_name)

        objectives = ending.get("objective_results", {}) or {}
        obj_achieved = sum(1 for v in objectives.values() if isinstance(v, dict) and v.get("achieved"))
        obj_total = len(objectives)

        print(f"  Arrested: {arrested}", flush=True)
        print(f"  Criminal caught: {'YES' if caught else 'NO'}", flush=True)
        print(f"  Objectives achieved: {obj_achieved}/{obj_total}", flush=True)

        for p in players:
            pid = p.player_id
            obj = objectives.get(pid, {})
            achieved = obj.get("achieved", False) if isinstance(obj, dict) else False
            desc = obj.get("description", "") if isinstance(obj, dict) else ""
            print(f"    {p.char_info['char_name']} ({p.role}): {'達成' if achieved else '未達成'} - {desc[:50]}", flush=True)

        # Cleanup
        for p in players:
            if p.ws:
                await p.ws.close()

        return {
            "caught": caught,
            "arrested": arrested,
            "criminal": true_criminal_name,
            "objectives_achieved": obj_achieved,
            "objectives_total": obj_total,
            "objective_details": {
                p.char_info["char_name"]: {
                    "role": p.role,
                    "achieved": objectives.get(p.player_id, {}).get("achieved", False) if isinstance(objectives.get(p.player_id), dict) else False,
                }
                for p in players
            },
        }


async def main():
    results = []
    for i in range(1, 6):
        try:
            r = await run_one_game(i)
            results.append(r)
        except Exception as e:
            print(f"GAME {i} FAILED: {e}")
            results.append({"caught": False, "objectives_achieved": 0, "objectives_total": 4, "error": str(e)})

    print("\n" + "=" * 60)
    print("BATCH RESULTS (5 GAMES)")
    print("=" * 60)

    caught_count = sum(1 for r in results if r.get("caught"))
    total_obj = sum(r.get("objectives_total", 0) for r in results)
    achieved_obj = sum(r.get("objectives_achieved", 0) for r in results)

    print(f"\n犯人的中率: {caught_count}/5 ({caught_count*100//5}%)")
    print(f"目的達成率: {achieved_obj}/{total_obj} ({achieved_obj*100//total_obj if total_obj else 0}%)")

    print("\n詳細:")
    for i, r in enumerate(results, 1):
        status = "犯人的中" if r.get("caught") else "冤罪"
        print(f"  Game {i}: {status} | 逮捕: {r.get('arrested', '?')} | 真犯人: {r.get('criminal', '?')} | 目的: {r.get('objectives_achieved', 0)}/{r.get('objectives_total', 0)}")
        if "objective_details" in r:
            for name, info in r["objective_details"].items():
                print(f"    {name} ({info['role']}): {'達成' if info['achieved'] else '未達成'}")


if __name__ == "__main__":
    asyncio.run(main())
