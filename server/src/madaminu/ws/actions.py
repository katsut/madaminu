"""WS action handlers. Each function handles one message type.

All actions:
1. Call the appropriate service
2. Send response/notification via WS manager
"""

import asyncio
import logging
from datetime import datetime, timedelta

from madaminu.models import Phase, PhaseType
from madaminu.services.discovery_service import DiscoveryService
from madaminu.services.game_service import GameService
from madaminu.services.speech_service import SpeechService
from madaminu.ws.manager_v3 import WSManager

logger = logging.getLogger(__name__)

# Server-side phase timers: game_id -> asyncio.Task
_phase_timers: dict[str, asyncio.Task] = {}


def schedule_phase_timer(
    game_id: str,
    room_code: str,
    duration_sec: int,
    game_service: GameService,
    discovery_service: DiscoveryService,
    ws: WSManager,
):
    """Schedule auto-advance after duration_sec. Cancels any existing timer for this game."""
    cancel_phase_timer(game_id)
    if duration_sec <= 0:
        logger.info("schedule_phase_timer: duration_sec=%d, manual advance only", duration_sec)
        return

    logger.info("schedule_phase_timer: %s %ds", room_code, duration_sec)

    async def _timer():
        await asyncio.sleep(duration_sec)
        _phase_timers.pop(game_id, None)
        logger.info("Phase timer expired for %s, auto-advancing", room_code)
        await handle_advance(game_id, room_code, "__server__", {"force": True}, game_service, discovery_service, ws)

    _phase_timers[game_id] = asyncio.create_task(_timer())


def cancel_phase_timer(game_id: str):
    """Cancel timer if it exists. Called on manual advance."""
    task = _phase_timers.pop(game_id, None)
    if task and not task.done():
        task.cancel()


async def handle_advance(
    game_id: str,
    room_code: str,
    player_id: str,
    data: dict,
    game_service: GameService,
    discovery_service: DiscoveryService,
    ws: WSManager,
):
    force_raw = data.get("force", False)
    force = force_raw is True or force_raw == "true"
    result = await game_service.advance_phase(game_id, force=force)

    if result.status == "not_expired":
        if player_id != "__server__":
            await ws.send_to(room_code, player_id, {
                "type": "error",
                "data": {"code": "not_expired", "remaining_sec": result.remaining_sec},
            })
        return

    if result.status == "already_advanced":
        return

    cancel_phase_timer(game_id)

    if result.status == "game_ended":
        await ws.broadcast_game_state(room_code, game_id, game_service)
        asyncio.create_task(_generate_ending_background(game_id, room_code, game_service, ws))
        return

    # 1st broadcast: phase preparing (discoveries_status = "preparing" or "generating")
    phase = result.phase
    await ws.broadcast_game_state(room_code, game_id, game_service)

    # Background: wait minimum 3s transition, then mark ready and send 2nd broadcast
    asyncio.create_task(
        _finalize_phase_start(game_id, room_code, phase, discovery_service, game_service, ws)
    )


async def handle_select_location(
    game_id: str,
    room_code: str,
    player_id: str,
    data: dict,
    game_service: GameService,
    ws: WSManager,
):
    location_id = data.get("location_id", "")
    if not location_id:
        await ws.send_to(room_code, player_id, {
            "type": "error",
            "data": {"code": "invalid", "message": "location_id is required"},
        })
        return
    await game_service.select_location(game_id, player_id, location_id)


async def handle_keep_evidence(
    game_id: str,
    room_code: str,
    player_id: str,
    data: dict,
    game_service: GameService,
    ws: WSManager,
):
    discovery_id = data.get("discovery_id", "")
    if not discovery_id:
        await ws.send_to(room_code, player_id, {
            "type": "error",
            "data": {"code": "invalid", "message": "discovery_id is required"},
        })
        return

    evidence = await game_service.keep_evidence(game_id, player_id, discovery_id)
    if evidence is None:
        await ws.send_to(room_code, player_id, {
            "type": "error",
            "data": {"code": "already_kept", "message": "Already kept evidence this phase"},
        })
        return

    # Update the player's state
    await ws.send_to(room_code, player_id, {
        "type": "game.state",
        "data": await game_service.get_state(game_id, player_id),
    })


async def handle_speech_request(
    game_id: str,
    room_code: str,
    player_id: str,
    speech_service: SpeechService,
    ws: WSManager,
):
    granted, prev_speaker = await speech_service.request_speech(game_id, player_id)
    if granted:
        await ws.send_to(room_code, player_id, {
            "type": "speech.granted",
            "data": {"player_id": player_id},
        })
        await ws.broadcast(room_code, {
            "type": "speech.active",
            "data": {"player_id": player_id},
        })
        if prev_speaker:
            # Notify previous speaker they were preempted
            await ws.broadcast(room_code, {
                "type": "speech",
                "data": {"player_id": prev_speaker, "character_name": "", "transcript": ""},
            })


async def handle_speech_release(
    game_id: str,
    room_code: str,
    player_id: str,
    data: dict,
    speech_service: SpeechService,
    ws: WSManager,
    players: dict[str, str],  # player_id -> character_name
):
    transcript = data.get("transcript", "")
    released = await speech_service.release_speech(game_id, player_id, transcript)
    if released:
        char_name = players.get(player_id, "")
        await ws.broadcast(room_code, {
            "type": "speech",
            "data": {"player_id": player_id, "character_name": char_name, "transcript": transcript},
        })


async def handle_reveal_evidence(
    game_id: str,
    room_code: str,
    player_id: str,
    data: dict,
    game_service: GameService,
    ws: WSManager,
    players: dict[str, str],
):
    evidence_id = data.get("evidence_id", "")
    if not evidence_id:
        return

    from sqlalchemy import select

    from madaminu.models import Evidence

    async with game_service._sf() as db:
        result = await db.execute(select(Evidence).where(Evidence.id == evidence_id, Evidence.player_id == player_id))
        evidence = result.scalar_one_or_none()
        if evidence is None:
            return

        char_name = players.get(player_id, "")
        await ws.broadcast(room_code, {
            "type": "evidence_revealed",
            "data": {
                "player_id": player_id,
                "player_name": char_name,
                "title": evidence.title,
                "content": evidence.content,
            },
        })


async def handle_vote(
    game_id: str,
    room_code: str,
    player_id: str,
    data: dict,
    game_service: GameService,
    discovery_service: DiscoveryService,
    ws: WSManager,
):
    suspect_id = data.get("suspect_player_id", "")
    if not suspect_id:
        await ws.send_to(room_code, player_id, {
            "type": "error",
            "data": {"code": "invalid", "message": "suspect_player_id is required"},
        })
        return

    result = await game_service.vote(game_id, player_id, suspect_id)
    if "error" in result:
        await ws.send_to(room_code, player_id, {
            "type": "error",
            "data": {"code": result["error"]},
        })
        return

    await ws.broadcast(room_code, {
        "type": "vote_cast",
        "data": {"voted_count": result["voted_count"], "total_human": result["total_human"]},
    })

    if result["all_voted"]:
        # Auto-advance from voting → ending
        await game_service.advance_phase(game_id, force=True)
        await ws.broadcast_game_state(room_code, game_id, game_service)
        asyncio.create_task(_generate_ending_background(game_id, room_code, game_service, ws))


async def handle_room_message(
    room_code: str,
    player_id: str,
    data: dict,
    ws: WSManager,
    players: dict[str, str],
):
    text = data.get("text", "")
    if not text:
        return
    char_name = players.get(player_id, "")
    # TODO: send only to colocated players (need selection data)
    await ws.broadcast(room_code, {
        "type": "room_message",
        "data": {"sender_id": player_id, "sender_name": char_name, "text": text},
    })


PHASE_TRANSITION_SEC = 3


async def _finalize_phase_start(
    game_id: str,
    room_code: str,
    phase: Phase,
    discovery_service: DiscoveryService,
    game_service: GameService,
    ws: WSManager,
):
    """Wait for transition period, finalize phase, send 2nd game.state, start timer."""
    logger.info("_finalize_phase_start: %s %s (duration=%ds)", room_code, phase.phase_type, phase.duration_sec)
    try:
        await _finalize_phase_start_inner(game_id, room_code, phase, discovery_service, game_service, ws)
    except Exception:
        logger.exception("_finalize_phase_start FAILED for %s, recovering", room_code)
        # Recover: mark phase as ready so game can continue
        async with game_service._sf() as db:
            from sqlalchemy import select

            phase_obj = await db.execute(select(Phase).where(Phase.id == phase.id))
            p = phase_obj.scalar_one_or_none()
            if p and p.discoveries_status != "ready":
                p.discoveries_status = "ready"
                p.started_at = datetime.utcnow()
                p.deadline_at = datetime.utcnow() + timedelta(seconds=max(p.duration_sec, 60))
                await db.commit()
        await ws.broadcast_game_state(room_code, game_id, game_service)
        schedule_phase_timer(game_id, room_code, max(phase.duration_sec, 60), game_service, discovery_service, ws)


async def _finalize_phase_start_inner(
    game_id: str,
    room_code: str,
    phase: Phase,
    discovery_service: DiscoveryService,
    game_service: GameService,
    ws: WSManager,
):
    if phase.phase_type == PhaseType.investigation:
        # Run discovery generation with retry (3 attempts)
        last_error = None
        for attempt in range(3):
            try:
                await asyncio.gather(
                    asyncio.sleep(PHASE_TRANSITION_SEC),
                    _generate_discoveries_background(
                        game_id, room_code, phase.id, discovery_service, game_service, ws
                    ),
                )
                last_error = None
                break
            except Exception as e:
                last_error = e
                logger.warning("Discovery generation attempt %d failed for %s: %s", attempt + 1, room_code, e)
                if attempt < 2:
                    await asyncio.sleep(3)
        if last_error:
            logger.error("Discovery generation failed after 3 attempts for %s", room_code)
        # AI players auto-keep one discovery each
        await _ai_auto_keep_evidence(game_id, phase.id, game_service)
    else:
        await asyncio.sleep(PHASE_TRANSITION_SEC)

    # Mark phase as ready, reset started_at so remaining_sec = duration_sec
    async with game_service._sf() as db:
        from sqlalchemy import select

        phase_obj = await db.execute(select(Phase).where(Phase.id == phase.id))
        p = phase_obj.scalar_one()
        p.discoveries_status = "ready"
        p.started_at = datetime.utcnow()
        p.deadline_at = datetime.utcnow() + timedelta(seconds=p.duration_sec)
        await db.commit()

    # 2nd broadcast: phase ready
    await ws.broadcast_game_state(room_code, game_id, game_service)

    # Notify colocated players for investigation
    if phase.phase_type == PhaseType.investigation:
        await _notify_colocated_players(game_id, room_code, phase.id, game_service, ws)

    # Schedule phase timer (starts counting from now, after transition)
    schedule_phase_timer(game_id, room_code, phase.duration_sec, game_service, discovery_service, ws)

    # Start AI speech for discussion/opening phases
    if phase.phase_type in (PhaseType.discussion, PhaseType.opening):
        asyncio.create_task(
            _ai_speech_background(game_id, room_code, phase.id, game_service, ws)
        )


# --- Background jobs ---


async def _generate_discoveries_background(
    game_id: str,
    room_code: str,
    phase_id: str,
    discovery_service: DiscoveryService,
    game_service: GameService,
    ws: WSManager,
):
    logger.info("Starting discovery generation for %s", room_code)
    await discovery_service.generate_all(game_id, phase_id)
    logger.info("Discovery generation complete for %s", room_code)


async def _notify_colocated_players(
    game_id: str,
    room_code: str,
    phase_id: str,
    game_service: GameService,
    ws: WSManager,
):
    """Send colocated player lists to each player in investigation phase."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from madaminu.models import Game
    from madaminu.models.investigation_selection import InvestigationSelection

    async with game_service._sf() as db:
        game_result = await db.execute(
            select(Game).options(selectinload(Game.players)).where(Game.id == game_id)
        )
        game = game_result.scalar_one()

        sel_result = await db.execute(
            select(InvestigationSelection).where(InvestigationSelection.phase_id == phase_id)
        )
        selections = sel_result.scalars().all()

        # Group by location
        location_players: dict[str, list[str]] = {}
        for s in selections:
            location_players.setdefault(s.location_id, []).append(s.player_id)

        id_to_info = {
            p.id: {"player_id": p.id, "character_name": p.character_name or p.display_name}
            for p in game.players
        }

        for _location_id, player_ids in location_players.items():
            if len(player_ids) < 2:
                continue
            for pid in player_ids:
                others = [id_to_info[oid] for oid in player_ids if oid != pid and oid in id_to_info]
                await ws.send_to(room_code, pid, {
                    "type": "location.colocated",
                    "data": {"players": others},
                })


async def _ai_auto_keep_evidence(game_id: str, phase_id: str, game_service: GameService):
    """AI players automatically keep one discovery each."""
    import random
    import uuid

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from madaminu.models import Evidence, Game

    async with game_service._sf() as db:
        game_result = await db.execute(
            select(Game).options(selectinload(Game.players)).where(Game.id == game_id)
        )
        game = game_result.scalar_one()

        for player in game.players:
            if not player.is_ai:
                continue

            # Get this AI's discoveries for this phase
            disc_result = await db.execute(
                select(Evidence).where(
                    Evidence.game_id == game_id,
                    Evidence.player_id == player.id,
                    Evidence.phase_id == phase_id,
                    Evidence.source == "discovery",
                )
            )
            discoveries = disc_result.scalars().all()
            if not discoveries:
                continue

            # Pick one to keep
            chosen = random.choice(discoveries)
            db.add(Evidence(
                id=str(uuid.uuid4()),
                game_id=game_id,
                player_id=player.id,
                phase_id=phase_id,
                title=chosen.title,
                content=chosen.content,
                source="investigation",
            ))

        await db.commit()
    logger.info("AI players auto-kept evidence for phase %s", phase_id)


async def _ai_speech_background(
    game_id: str,
    room_code: str,
    phase_id: str,
    game_service: GameService,
    ws: WSManager,
):
    """Generate speech for AI players during discussion/opening phases."""
    import json
    import random

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from madaminu.llm.client import LIGHT_MODEL, llm_client
    from madaminu.models import Evidence, Game, SpeechLog

    try:
        async with game_service._sf() as db:
            game_result = await db.execute(
                select(Game).options(selectinload(Game.players)).where(Game.id == game_id)
            )
            game = game_result.scalar_one()
            ai_players = [p for p in game.players if p.is_ai]
            if not ai_players:
                return

            # Gather public evidence
            ev_result = await db.execute(
                select(Evidence).where(Evidence.game_id == game_id, Evidence.source != "discovery")
            )
            all_evidence = ev_result.scalars().all()

            # Gather speech logs
            speech_result = await db.execute(
                select(SpeechLog).where(SpeechLog.game_id == game_id).order_by(SpeechLog.created_at)
            )
            speech_logs = speech_result.scalars().all()

            context = {
                "scenario": json.dumps(game.scenario_skeleton or {}, ensure_ascii=False)[:2000],
                "evidence": [{"title": e.title, "content": e.content, "player_id": e.player_id} for e in all_evidence],
                "speeches": [{"player_id": s.player_id, "transcript": s.transcript} for s in speech_logs[-20:]],
                "players": {
                    p.id: {
                        "name": p.character_name or p.display_name,
                        "role": p.role,
                        "public_info": p.public_info,
                    }
                    for p in game.players
                },
            }

        # Generate speech for each AI player (no DB session held)
        random.shuffle(ai_players)
        revealed_player_ids: set[str] = set()

        for ai_player in ai_players:
            await asyncio.sleep(random.randint(10, 30))

            # Check phase is still active
            async with game_service._sf() as db:
                game_check = await db.execute(select(Game).where(Game.id == game_id))
                g = game_check.scalar_one()
                if g.current_phase_id != phase_id:
                    return

            player_info = context["players"].get(ai_player.id, {})
            char_name = player_info.get("name", "")
            evidence_text = "\n".join(f"- {e['title']}: {e['content']}" for e in context["evidence"])
            speech_text = "\n".join(
                f"- {context['players'].get(s['player_id'], {}).get('name', '?')}: {s['transcript']}"
                for s in context["speeches"]
            )

            prompt = f"""あなたは「{char_name}」というキャラクターです。
公開情報: {player_info.get('public_info', 'なし')}

これまでに公開された証拠:
{evidence_text or 'まだなし'}

これまでの発言:
{speech_text or 'まだなし'}

この情報に基づいて、議論に参加する短い発言を1つ生成してください。
- 自分の公開情報に基づいた視点で発言
- 他のプレイヤーの発言に反応しても良い
- 30〜80文字程度
- キャラクターの口調で
- JSON形式: {{"speech": "発言内容"}}"""

            try:
                raw, usage = await llm_client.generate_json(
                    "あなたはマーダーミステリーゲームのAIプレイヤーです。",
                    prompt,
                    model=LIGHT_MODEL,
                )
                from madaminu.services.scenario_engine import _parse_scenario_json

                result = _parse_scenario_json(raw)
                transcript = result.get("speech", "")
                if not transcript:
                    continue

                import uuid

                async with game_service._sf() as db:
                    db.add(SpeechLog(
                        id=str(uuid.uuid4()),
                        game_id=game_id,
                        player_id=ai_player.id,
                        phase_id=phase_id,
                        transcript=transcript,
                    ))
                    await db.commit()

                await ws.broadcast(room_code, {
                    "type": "speech",
                    "data": {"player_id": ai_player.id, "character_name": char_name, "transcript": transcript},
                })
                logger.info("AI speech: %s said '%s'", char_name, transcript[:50])

                # 80% chance to reveal evidence after speaking
                if random.random() < 0.8:
                    revealed = await _ai_reveal_evidence(
                        game_id, room_code, ai_player.id, char_name, game_service, ws
                    )
                    if revealed:
                        revealed_player_ids.add(ai_player.id)

            except Exception:
                logger.exception("AI speech generation failed for %s", ai_player.id)

        # If nobody revealed evidence yet, force one AI to reveal
        if not revealed_player_ids:
            unrevealed = [p for p in ai_players if p.id not in revealed_player_ids]
            if unrevealed:
                fallback = random.choice(unrevealed)
                fb_name = context["players"].get(fallback.id, {}).get("name", "")
                await asyncio.sleep(random.randint(5, 15))
                await _ai_reveal_evidence(
                    game_id, room_code, fallback.id, fb_name, game_service, ws
                )

    except Exception:
        logger.exception("AI speech background failed for %s", room_code)


async def _ai_reveal_evidence(
    game_id: str,
    room_code: str,
    player_id: str,
    char_name: str,
    game_service: GameService,
    ws: WSManager,
) -> bool:
    """AI reveals one kept evidence. Returns True if revealed."""
    import random

    from sqlalchemy import select

    from madaminu.models import Evidence

    async with game_service._sf() as db:
        ev_result = await db.execute(
            select(Evidence).where(
                Evidence.game_id == game_id,
                Evidence.player_id == player_id,
                Evidence.source == "investigation",
            )
        )
        evidences = ev_result.scalars().all()
        if not evidences:
            return False

        ev = random.choice(evidences)
        await ws.broadcast(room_code, {
            "type": "evidence_revealed",
            "data": {
                "player_id": player_id,
                "player_name": char_name,
                "title": ev.title,
                "content": ev.content,
            },
        })
        logger.info("AI revealed evidence: %s - %s", char_name, ev.title)
        return True


async def _generate_ending_background(
    game_id: str,
    room_code: str,
    game_service: GameService,
    ws: WSManager,
):
    logger.info("Starting ending generation for %s", room_code)
    try:
        from madaminu.services.scenario_engine import generate_ending

        async with game_service._sf() as db:
            ending, usage = await generate_ending(db, game_id)
            logger.info("Ending generated for %s (cost: $%.4f)", room_code, usage.estimated_cost_usd)

        await ws.broadcast_game_state(room_code, game_id, game_service)
    except Exception:
        logger.exception("Ending generation FAILED for %s", room_code)
