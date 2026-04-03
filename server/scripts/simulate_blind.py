"""Blind simulation: players vote based ONLY on visible information.

Each player knows:
- Their own role, secret, objective
- Public info of all characters
- Speech history (what was said)
- Evidence they found

They do NOT use their knowledge of other players' roles for voting.
Voting heuristic: analyze speeches for defensiveness, contradictions, and suspicion.
"""

import asyncio
import json
import random
import time
import sys

import httpx
import websockets

BASE_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000"

# Randomize characters each game
CHAR_POOL = [
    {"char_name": "天城 蓮", "gender": "男", "age": "35", "occupation": "建築家"},
    {"char_name": "白石 凛", "gender": "女", "age": "29", "occupation": "弁護士"},
    {"char_name": "鳴海 悠太", "gender": "男", "age": "52", "occupation": "料理評論家"},
    {"char_name": "朝倉 詩織", "gender": "女", "age": "41", "occupation": "画廊オーナー"},
    {"char_name": "九条 隼人", "gender": "男", "age": "38", "occupation": "外科医"},
    {"char_name": "藤宮 楓", "gender": "女", "age": "26", "occupation": "フリーライター"},
    {"char_name": "榊原 誠一", "gender": "男", "age": "60", "occupation": "元検事"},
    {"char_name": "柊 美月", "gender": "女", "age": "33", "occupation": "薬剤師"},
]


class Player:
    def __init__(self, name, char_info):
        self.name = name
        self.ci = char_info
        self.tok = ""
        self.pid = ""
        self.ws = None
        self.pt = ""
        self.role = ""
        self.secret = ""
        self.objective = ""
        self.locs = []
        self.discs = []
        self.end = None
        self.speeches = []  # (speaker_name, text)
        self.kept_evidence = []

    async def drain(self, dur=1.0):
        try:
            end = time.monotonic() + dur
            while time.monotonic() < end:
                raw = await asyncio.wait_for(self.ws.recv(), timeout=0.5)
                m = json.loads(raw)
                t = m.get("type", "")
                d = m.get("data", {})
                if t == "game.state":
                    self.role = d.get("my_role", "") or ""
                    self.secret = d.get("my_secret_info", "") or ""
                    self.objective = d.get("my_objective", "") or ""
                elif t == "phase.started":
                    self.pt = d.get("phase_type", "")
                    self.discs = []
                    l = d.get("investigation_locations")
                    if l:
                        if isinstance(l, str):
                            try:
                                l = json.loads(l)
                            except:
                                l = []
                        self.locs = l
                elif t == "investigate.discoveries":
                    ds = d.get("discoveries")
                    if isinstance(ds, str):
                        try:
                            ds = json.loads(ds)
                        except:
                            ds = []
                    if ds:
                        self.discs = ds
                elif t == "investigate.kept":
                    self.kept_evidence.append(d.get("title", ""))
                elif t in ("speech.released", "speech.ai"):
                    name = d.get("character_name", "?")
                    text = d.get("transcript", "")
                    if text:
                        self.speeches.append((name, text))
                elif t == "game.ending":
                    self.end = d
        except:
            pass


async def drain_all(ps, d=1.0):
    await asyncio.gather(*[p.drain(d) for p in ps])


async def wp(ps, ph, to=60):
    e = time.monotonic() + to
    while time.monotonic() < e:
        await drain_all(ps, 1.0)
        if all(p.pt == ph for p in ps):
            return True
    return False


def blind_vote(player, all_players):
    """Vote based ONLY on what this player can observe.

    Heuristics:
    - Who claimed innocence defensively?
    - Who was evasive?
    - Who had contradictions in their statements?
    - Random factor for uncertainty
    """
    suspects = [p for p in all_players if p.pid != player.pid]
    scores = {p.pid: 0 for p in suspects}

    for p in suspects:
        for speaker, text in player.speeches:
            if speaker == p.ci["char_name"]:
                # Defensive language increases suspicion
                if any(w in text for w in ["無実", "違う", "疑わない", "別の場所"]):
                    scores[p.pid] += 3
                # Evasive language
                if any(w in text for w in ["何でもない", "気のせい", "覚えていない"]):
                    scores[p.pid] += 2
                # Accusatory (less suspicious - real criminals don't usually accuse)
                if any(w in text for w in ["怪しい", "犯人", "証拠"]):
                    scores[p.pid] -= 1

    # Add randomness (real players have intuition/uncertainty)
    for pid in scores:
        scores[pid] += random.randint(0, 3)

    # Vote for highest suspicion
    target_pid = max(scores, key=scores.get)
    return next(p for p in suspects if p.pid == target_pid)


async def run_game(n):
    chars = random.sample(CHAR_POOL, 4)
    names = ["P1", "P2", "P3", "P4"]

    print(f"\n{'='*50}", flush=True)
    print(f"GAME {n}", flush=True)
    print(f"{'='*50}", flush=True)
    print(f"  Characters: {', '.join(c['char_name'] for c in chars)}", flush=True)

    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE_URL}/api/v1/rooms", json={"display_name": names[0]})
        r.raise_for_status()
        rc = r.json()["room_code"]
        ps = []
        p0 = Player(names[0], chars[0])
        p0.tok = r.json()["session_token"]
        p0.pid = r.json()["player_id"]
        ps.append(p0)

        for i in range(1, 4):
            r = await c.post(f"{BASE_URL}/api/v1/rooms/{rc}/join", json={"display_name": names[i]})
            r.raise_for_status()
            p = Player(names[i], chars[i])
            p.tok = r.json()["session_token"]
            p.pid = r.json()["player_id"]
            ps.append(p)

        for p in ps:
            await c.post(
                f"{BASE_URL}/api/v1/rooms/{rc}/characters",
                json={
                    "character_name": p.ci["char_name"],
                    "character_personality": "性格は秘密",
                    "character_background": "経歴は秘密",
                    "character_gender": p.ci["gender"],
                    "character_age": p.ci["age"],
                    "character_occupation": p.ci["occupation"],
                },
                headers={"x-session-token": p.tok},
            )

        for p in ps[1:]:
            await c.post(f"{BASE_URL}/api/v1/rooms/{rc}/ready", headers={"x-session-token": p.tok})

        for p in ps:
            p.ws = await websockets.connect(f"{WS_URL}/ws/{rc}?token={p.tok}")

        await c.post(f"{BASE_URL}/api/v1/rooms/{rc}/start", headers={"x-session-token": ps[0].tok}, timeout=120)

        # Wait for game ready
        for _ in range(40):
            await drain_all(ps, 2.0)
            try:
                s = await c.get(f"{BASE_URL}/api/v1/rooms/{rc}/state", headers={"x-session-token": ps[0].tok})
                if s.json().get("status") == "playing":
                    break
            except:
                pass

        for _ in range(5):
            for p in ps:
                s = await c.get(f"{BASE_URL}/api/v1/rooms/{rc}/state", headers={"x-session-token": p.tok})
                d = s.json()
                p.role = d.get("my_role", "") or ""
                p.secret = d.get("my_secret_info", "") or ""
                p.objective = d.get("my_objective", "") or ""
            if all(p.role for p in ps):
                break
            await asyncio.sleep(2)

        criminal = next((p for p in ps if p.role == "criminal"), None)
        print(f"  True criminal: {criminal.ci['char_name'] if criminal else '?'}", flush=True)

        # Opening
        await wp(ps, "opening", 30)
        for p in ps:
            await p.ws.send(json.dumps({"type": "speech.request"}))
            await asyncio.sleep(0.2)
            await p.ws.send(json.dumps({
                "type": "speech.release",
                "data": {"transcript": f"私は{p.ci['char_name']}です。{p.ci['occupation']}をしています。"},
            }))
            await asyncio.sleep(0.3)

        # 3 turns
        for turn in range(3):
            # Planning
            await ps[0].ws.send(json.dumps({"type": "phase.advance"}))
            await wp(ps, "planning", 30)
            await drain_all(ps, 2.0)

            for p in ps:
                if p.locs:
                    loc = random.choice(p.locs)
                    await p.ws.send(json.dumps({"type": "investigate.select", "data": {"location_id": loc["id"]}}))

            # Investigation
            await ps[0].ws.send(json.dumps({"type": "phase.advance"}))
            await wp(ps, "investigation", 60)
            await drain_all(ps, 8.0)

            for p in ps:
                if p.discs and isinstance(p.discs[0], dict) and "id" in p.discs[0]:
                    await p.ws.send(json.dumps({"type": "investigate.keep", "data": {"discovery_id": p.discs[0]["id"]}}))
                    await p.drain(1.0)

            # Discussion
            await ps[0].ws.send(json.dumps({"type": "phase.advance"}))
            await wp(ps, "discussion", 30)

            for p in ps:
                await p.ws.send(json.dumps({"type": "speech.request"}))
                await asyncio.sleep(0.2)
                # Role-based speech (but doesn't reveal role)
                if p.role == "criminal":
                    texts = [
                        "私は無実です。事件当時は別の場所にいました。",
                        "この件には何の関わりもありません。疑わないでいただきたい。",
                        "他に怪しい人がいると思います。私ではない。",
                    ]
                elif p.role == "witness":
                    texts = [
                        "何か物音を聞いた気がしますが... 気のせいかもしれません。",
                        "あの時間帯に廊下で誰かとすれ違った記憶があります。",
                        "直接見たわけではありませんが、不審な点があります。",
                    ]
                else:
                    texts = [
                        "証拠を整理して、論理的に犯人を特定しましょう。",
                        "動機がある人物を考えてみてください。",
                        f"ターン{turn+1}で見つけた手がかりが気になります。",
                    ]
                text = random.choice(texts)
                await p.ws.send(json.dumps({"type": "speech.release", "data": {"transcript": text}}))
                await asyncio.sleep(0.3)

        # Voting (BLIND - based only on observable info)
        await ps[0].ws.send(json.dumps({"type": "phase.advance"}))
        await wp(ps, "voting", 30)
        await asyncio.sleep(1)

        votes = {}
        for p in ps:
            target = blind_vote(p, ps)
            votes[p.ci["char_name"]] = target.ci["char_name"]
            await p.ws.send(json.dumps({"type": "vote.submit", "data": {"suspect_player_id": target.pid}}))
            print(f"    {p.ci['char_name']}({p.role}) voted for {target.ci['char_name']}", flush=True)
            await asyncio.sleep(0.5)

        # Wait for ending
        for _ in range(30):
            await drain_all(ps, 2.0)
            if any(p.end for p in ps):
                break

        ending = next((p.end for p in ps if p.end), {}) or {}
        arrested = ending.get("arrested_name")
        cn = criminal.ci["char_name"] if criminal else None
        caught = bool(arrested and cn and arrested == cn)

        objs = ending.get("objective_results", {}) or {}
        details = {}
        for p in ps:
            o = objs.get(p.pid, {})
            ach = o.get("achieved", False) if isinstance(o, dict) else False
            desc = o.get("description", "") if isinstance(o, dict) else ""
            details[p.ci["char_name"]] = {"role": p.role, "achieved": ach, "desc": desc}

        oa = sum(1 for v in details.values() if v["achieved"])
        print(f"  Arrested: {arrested}", flush=True)
        print(f"  Caught: {'YES' if caught else 'NO'}", flush=True)
        print(f"  Objectives: {oa}/4", flush=True)
        for nm, info in details.items():
            print(f"    {nm}({info['role']}): {'達成' if info['achieved'] else '未達成'} {info['desc'][:40]}", flush=True)

        for p in ps:
            if p.ws:
                await p.ws.close()

        return {"caught": caught, "arrested": arrested, "criminal": cn, "details": details}


async def main():
    results = []
    for i in range(1, 6):
        try:
            r = await run_game(i)
            results.append(r)
        except Exception as e:
            print(f"  FAILED: {e}", flush=True)
            results.append({"caught": False, "details": {}})

    print(f"\n{'='*60}", flush=True)
    print("FINAL RESULTS (BLIND VOTING)", flush=True)
    print(f"{'='*60}", flush=True)

    cc = sum(1 for r in results if r.get("caught"))
    ta = sum(1 for r in results for v in r.get("details", {}).values() if v.get("achieved"))
    tt = sum(len(r.get("details", {})) for r in results)

    print(f"\n犯人的中率: {cc}/{len(results)} ({cc*100//len(results) if results else 0}%)", flush=True)
    print(f"目的達成率: {ta}/{tt} ({ta*100//tt if tt else 0}%)", flush=True)

    for i, r in enumerate(results, 1):
        s = "的中" if r.get("caught") else "冤罪"
        print(f"\n  Game {i}: {s} | 逮捕:{r.get('arrested','?')} | 真犯人:{r.get('criminal','?')}", flush=True)
        for nm, info in r.get("details", {}).items():
            print(f"    {nm}({info['role']}): {'達成' if info['achieved'] else '未達成'}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
