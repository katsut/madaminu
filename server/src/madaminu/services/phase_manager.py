import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from madaminu.models import Game, GameStatus, Phase, PhaseType
from madaminu.ws.messages import (
    PhaseEndedData,
    PhaseStartedData,
    PhaseTimerData,
    WSMessage,
)

logger = logging.getLogger(__name__)

TIMER_TICK_INTERVAL = 10
EXTEND_DURATION_SEC = 60


class PhaseManager:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory
        self._timers: dict[str, asyncio.Task] = {}
        self._investigation_selections: dict[str, dict[str, dict]] = {}
        self._discoveries: dict[str, dict[str, list[dict]]] = {}
        self._intro_ready: dict[str, set[str]] = {}
        self._paused: dict[str, int] = {}  # game_id -> remaining_sec when paused

    def set_investigation_selection(
        self, room_code: str, player_id: str, location_id: str | None, feature: str | None = None,
    ):
        if room_code not in self._investigation_selections:
            self._investigation_selections[room_code] = {}
        self._investigation_selections[room_code][player_id] = {"location_id": location_id, "feature": feature}

    def get_investigation_selections(self, room_code: str) -> dict[str, dict]:
        return dict(self._investigation_selections.get(room_code, {}))

    def clear_investigation_selections(self, room_code: str):
        self._investigation_selections.pop(room_code, None)

    def add_discovery(self, room_code: str, player_id: str, discovery: dict):
        if room_code not in self._discoveries:
            self._discoveries[room_code] = {}
        if player_id not in self._discoveries[room_code]:
            self._discoveries[room_code][player_id] = []
        self._discoveries[room_code][player_id].append(discovery)

    def get_discoveries(self, room_code: str, player_id: str) -> list[dict]:
        return list(self._discoveries.get(room_code, {}).get(player_id, []))

    def replace_discovery(self, room_code: str, player_id: str, discovery_id: str, new_discovery: dict):
        discoveries = self._discoveries.get(room_code, {}).get(player_id, [])
        for i, d in enumerate(discoveries):
            if d["id"] == discovery_id:
                discoveries[i] = new_discovery
                break

    def clear_discoveries(self, room_code: str):
        self._discoveries.pop(room_code, None)

    def set_intro_ready(self, room_code: str, player_id: str):
        if room_code not in self._intro_ready:
            self._intro_ready[room_code] = set()
        self._intro_ready[room_code].add(player_id)

    def get_intro_ready_count(self, room_code: str) -> int:
        return len(self._intro_ready.get(room_code, set()))

    def clear_intro_ready(self, room_code: str):
        self._intro_ready.pop(room_code, None)

    async def start_first_phase(self, game_id: str, room_code: str) -> Phase:
        async with self._session_factory() as db:
            result = await db.execute(select(Phase).where(Phase.game_id == game_id).order_by(Phase.phase_order))
            phases = result.scalars().all()
            if not phases:
                raise ValueError("No phases found for game")

            first_phase = next((p for p in phases if p.duration_sec > 0), phases[0])
            first_phase.started_at = datetime.utcnow()
            first_phase.deadline_at = datetime.utcnow() + timedelta(seconds=first_phase.duration_sec)

            game_result = await db.execute(select(Game).where(Game.id == game_id))
            game = game_result.scalar_one()
            game.current_phase_id = first_phase.id
            total_phases = len(phases)
            await db.commit()

        await self._broadcast_phase_started(room_code, first_phase, total_phases=total_phases)
        self._start_timer(game_id, room_code, first_phase)
        asyncio.create_task(self._schedule_ai_speeches(game_id, room_code, first_phase))
        return first_phase

    async def advance_phase(self, game_id: str, room_code: str) -> Phase | None:
        logger.info("advance_phase called for game %s room %s", game_id, room_code)
        self._cancel_timer(game_id)

        async with self._session_factory() as db:
            game_result = await db.execute(select(Game).options(selectinload(Game.phases)).where(Game.id == game_id))
            game = game_result.scalar_one()

            current_phase = next((p for p in game.phases if p.id == game.current_phase_id), None)
            if current_phase is None:
                raise ValueError("No current phase")

            current_phase.ended_at = datetime.utcnow()

            sorted_phases = sorted(game.phases, key=lambda p: p.phase_order)
            current_idx = next(i for i, p in enumerate(sorted_phases) if p.id == current_phase.id)

            if current_idx + 1 >= len(sorted_phases):
                game.status = GameStatus.ended
                await db.commit()
                await self._broadcast_phase_ended(room_code, current_phase, None)
                await self._generate_and_broadcast_ending(game.id, room_code)
                return None

            next_phase = sorted_phases[current_idx + 1]
            next_phase.started_at = datetime.utcnow()
            next_phase.deadline_at = datetime.utcnow() + timedelta(seconds=next_phase.duration_sec)
            game.current_phase_id = next_phase.id

            if next_phase.phase_type == PhaseType.voting:
                game.status = GameStatus.voting

            await db.commit()

        await self._broadcast_phase_ended(room_code, current_phase, next_phase)

        if current_phase.phase_type == PhaseType.investigation:
            self.clear_discoveries(room_code)

        if current_phase.phase_type != PhaseType.planning:
            await self._run_phase_adjustment(game_id, room_code, current_phase.id)

        if next_phase.phase_type == PhaseType.investigation:
            await self._send_travel_narratives(game_id, room_code)
            await self._generate_room_discoveries(game_id, room_code)
            async with self._session_factory() as db:
                phase_result = await db.execute(select(Phase).where(Phase.id == next_phase.id))
                next_phase = phase_result.scalar_one()
                next_phase.started_at = datetime.utcnow()
                next_phase.deadline_at = datetime.utcnow() + timedelta(seconds=next_phase.duration_sec)
                await db.commit()

        await self._broadcast_phase_started(room_code, next_phase)
        self._start_timer(game_id, room_code, next_phase)

        if next_phase.phase_type != PhaseType.investigation:
            asyncio.create_task(self._schedule_ai_speeches(game_id, room_code, next_phase))

        return next_phase

    async def extend_phase(self, game_id: str, room_code: str, extra_sec: int = EXTEND_DURATION_SEC) -> Phase:
        self._cancel_timer(game_id)

        async with self._session_factory() as db:
            game_result = await db.execute(select(Game).where(Game.id == game_id))
            game = game_result.scalar_one()

            phase_result = await db.execute(select(Phase).where(Phase.id == game.current_phase_id))
            phase = phase_result.scalar_one()
            phase.duration_sec += extra_sec
            await db.commit()

        self._start_timer(game_id, room_code, phase)

        from madaminu.ws.handler import manager

        await manager.broadcast(
            room_code,
            WSMessage(
                type="phase.extended",
                data={"extra_sec": extra_sec, "new_duration_sec": phase.duration_sec},
            ),
        )
        return phase

    async def pause_phase(self, game_id: str, room_code: str):
        from madaminu.ws.handler import manager

        self._cancel_timer(game_id)

        async with self._session_factory() as db:
            game_result = await db.execute(select(Game).where(Game.id == game_id))
            game = game_result.scalar_one()
            phase_result = await db.execute(select(Phase).where(Phase.id == game.current_phase_id))
            phase = phase_result.scalar_one()

            elapsed = (datetime.utcnow() - phase.started_at).total_seconds() if phase.started_at else 0
            remaining = max(0, phase.duration_sec - int(elapsed))
            self._paused[game_id] = remaining

        await manager.broadcast(
            room_code,
            WSMessage(type="phase.paused", data={"remaining_sec": remaining}),
        )

    async def resume_phase(self, game_id: str, room_code: str):
        from madaminu.ws.handler import manager

        remaining = self._paused.pop(game_id, None)
        if remaining is None:
            return

        async with self._session_factory() as db:
            game_result = await db.execute(select(Game).where(Game.id == game_id))
            game = game_result.scalar_one()
            phase_result = await db.execute(select(Phase).where(Phase.id == game.current_phase_id))
            phase = phase_result.scalar_one()

            phase.started_at = datetime.utcnow()
            phase.duration_sec = remaining
            phase.deadline_at = datetime.utcnow() + timedelta(seconds=remaining)
            await db.commit()

        self._start_timer(game_id, room_code, phase)

        await manager.broadcast(
            room_code,
            WSMessage(type="phase.resumed", data={"remaining_sec": remaining}),
        )

    def cleanup_game(self, game_id: str):
        self._cancel_timer(game_id)

    def _start_timer(self, game_id: str, room_code: str, phase: Phase):
        self._cancel_timer(game_id)
        task = asyncio.create_task(self._run_timer(game_id, room_code, phase.id, phase.duration_sec, phase.started_at))
        self._timers[game_id] = task

    def _cancel_timer(self, game_id: str):
        task = self._timers.pop(game_id, None)
        if task and not task.done():
            task.cancel()

    async def _run_timer(
        self,
        game_id: str,
        room_code: str,
        phase_id: str,
        duration_sec: int,
        started_at: datetime,
    ):
        from madaminu.ws.handler import manager

        try:
            while True:
                elapsed = (datetime.utcnow() - started_at).total_seconds()
                remaining = max(0, duration_sec - int(elapsed))

                await manager.broadcast(
                    room_code,
                    WSMessage(
                        type="phase.timer",
                        data=PhaseTimerData(
                            phase_id=phase_id,
                            remaining_sec=remaining,
                        ).model_dump(),
                    ),
                )

                if remaining <= 0:
                    break

                await asyncio.sleep(min(TIMER_TICK_INTERVAL, remaining))
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("Timer error for game %s", game_id)
            return

        logger.info("Phase timer expired for game %s, phase %s", game_id, phase_id)

        # Don't auto-advance voting phase - wait for all votes
        async with self._session_factory() as db:
            phase_result = await db.execute(select(Phase).where(Phase.id == phase_id))
            phase = phase_result.scalar_one_or_none()
            if phase and phase.phase_type == PhaseType.voting:
                logger.info("Voting phase timer expired but waiting for all votes")
                return

        try:
            await self.advance_phase(game_id, room_code)
        except Exception:
            logger.exception("advance_phase failed after timer expired for game %s", game_id)

    async def _generate_room_discoveries(self, game_id: str, room_code: str):
        import random

        from madaminu.services.scenario_engine import investigate_location
        from madaminu.ws.handler import manager

        selections = self.get_investigation_selections(room_code)

        # Assign random locations to players who didn't select
        async with self._session_factory() as db:
            game_result = await db.execute(
                select(Game).options(selectinload(Game.players)).where(Game.id == game_id)
            )
            game = game_result.scalar_one()
            map_data = (game.scenario_skeleton or {}).get("map", {})
            all_rooms = []
            for area in map_data.get("areas", []):
                for room in area.get("rooms", []):
                    room_type = room.get("room_type", "room")
                    if room_type not in ("corridor", "entrance", "stairs"):
                        all_rooms.append(room["id"])

            for player in game.players:
                if player.id not in selections and all_rooms:
                    loc = random.choice(all_rooms)
                    self.set_investigation_selection(room_code, player.id, loc)
                    logger.info("Auto-assigned location %s to player %s", loc, player.id)

        selections = self.get_investigation_selections(room_code)
        logger.info("Generating discoveries for %s: %d selections", room_code, len(selections))
        if not selections:
            logger.warning("No selections found for room %s", room_code)
            return

        try:
            for player_id, sel in selections.items():
                location_id = sel.get("location_id")
                if not location_id:
                    continue

                async with self._session_factory() as db:
                    game_result = await db.execute(
                        select(Game).options(selectinload(Game.players)).where(Game.id == game_id)
                    )
                    game = game_result.scalar_one()
                    map_data = (game.scenario_skeleton or {}).get("map", {})
                    location = None
                    for area in map_data.get("areas", []):
                        for room in area.get("rooms", []):
                            if room["id"] == location_id:
                                location = room
                                break

                    if location is None:
                        logger.warning("Location %s not found in map for player %s", location_id, player_id)
                        continue

                    features = location.get("features", [])
                    if not features:
                        logger.warning("No features for location %s", location_id)
                        continue

                    logger.info("Generating %d discoveries for player %s at %s", len(features), player_id, location_id)

                    is_alone = all(
                        other_sel.get("location_id") != location_id
                        for other_id, other_sel in selections.items()
                        if other_id != player_id
                    )

                    discoveries = []
                    for feature in features:
                        try:
                            discovery, usage = await investigate_location(
                                db, game_id, player_id, location_id, feature
                            )
                            logger.info(
                                "Discovery result for %s: %s",
                                feature, type(discovery).__name__ if discovery else "None",
                            )
                            if discovery:
                                discovery["can_tamper"] = is_alone
                                discoveries.append(discovery)
                                self.add_discovery(room_code, player_id, discovery)
                        except Exception:
                            logger.exception("Discovery generation failed: %s/%s", location_id, feature)

                    logger.info("Total discoveries for %s: %d", player_id, len(discoveries))
                    if discoveries:
                        await manager.send_to_player(
                            room_code,
                            player_id,
                            WSMessage(
                                type="investigate.discoveries",
                                data={"discoveries": discoveries},
                            ),
                        )
        except Exception:
            logger.exception("Room discovery generation failed for game %s", game_id)

    async def _execute_investigation_selections(self, game_id: str, room_code: str):
        from madaminu.services.scenario_engine import investigate_location
        from madaminu.ws.handler import manager

        selections = self.get_investigation_selections(room_code)
        self.clear_investigation_selections(room_code)

        if not selections:
            return

        for player_id, selection in selections.items():
            location_id = selection.get("location_id")
            feature = selection.get("feature")
            if not location_id:
                continue
            try:
                async with self._session_factory() as db:
                    evidence, usage = await investigate_location(db, game_id, player_id, location_id, feature)
                    if evidence:
                        await manager.send_to_player(
                            room_code,
                            player_id,
                            WSMessage(
                                type="investigate.result",
                                data={
                                    "title": evidence.title,
                                    "content": evidence.content,
                                    "location_id": location_id,
                                    "hint": "",
                                },
                            ),
                        )
                        logger.info("Investigation result sent to %s for %s/%s", player_id, location_id, feature)
            except Exception:
                logger.exception("Investigation failed for player %s location %s", player_id, location_id)

    async def _schedule_ai_speeches(self, game_id: str, room_code: str, phase: Phase):
        if phase.phase_type not in (PhaseType.discussion, PhaseType.opening, PhaseType.voting):
            return

        try:
            await asyncio.sleep(15)

            from madaminu.services.ai_player import generate_ai_speech
            from madaminu.ws.handler import manager

            async with self._session_factory() as db:
                game_result = await db.execute(
                    select(Game).options(selectinload(Game.players)).where(Game.id == game_id)
                )
                game = game_result.scalar_one()
                ai_players = [p for p in game.players if p.is_ai]

            for ai_player in ai_players:
                await asyncio.sleep(10)
                try:
                    async with self._session_factory() as db:
                        text, usage = await generate_ai_speech(db, game_id, ai_player.id, phase.id)
                    if text:
                        await manager.broadcast(
                            room_code,
                            WSMessage(
                                type="speech.ai",
                                data={
                                    "player_id": ai_player.id,
                                    "character_name": ai_player.character_name,
                                    "transcript": text,
                                },
                            ),
                        )
                        logger.info("AI player %s spoke: %s", ai_player.character_name, text[:50])
                except Exception:
                    logger.exception("AI speech failed for %s", ai_player.id)
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("AI speech scheduling failed for game %s", game_id)

    async def _send_travel_narratives(self, game_id: str, room_code: str):
        from madaminu.services.map_builder import generate_travel_narrative
        from madaminu.ws.handler import manager

        try:
            selections = self.get_investigation_selections(room_code)
            if not selections:
                return

            async with self._session_factory() as db:
                game_result = await db.execute(
                    select(Game).options(selectinload(Game.players)).where(Game.id == game_id)
                )
                game = game_result.scalar_one()
                map_data = (game.scenario_skeleton or {}).get("map", {})
                id_to_name = {
                    p.id: p.character_name or p.display_name
                    for p in game.players
                }

            loc_selections = {
                pid: sel.get("location_id", "")
                for pid, sel in selections.items()
                if sel.get("location_id")
            }
            narratives = generate_travel_narrative(map_data, loc_selections, id_to_name)

            for pid, text in narratives.items():
                if text:
                    await manager.send_to_player(
                        room_code, pid,
                        WSMessage(type="travel.narrative", data={"text": text}),
                    )
        except Exception:
            logger.exception("Travel narrative failed for game %s", game_id)

    async def _run_phase_adjustment(self, game_id: str, room_code: str, ended_phase_id: str):
        from madaminu.services.scenario_engine import adjust_phase
        from madaminu.ws.handler import manager

        try:
            async with self._session_factory() as db:
                adjustment, usage = await adjust_phase(db, game_id, ended_phase_id)
                logger.info("Phase adjustment for game %s: %s", game_id, usage)

                for ev in adjustment.get("evidence_distribution", []):
                    target_id = ev.get("target_player_id", "")
                    await manager.send_to_player(
                        room_code,
                        target_id,
                        WSMessage(
                            type="evidence.received",
                            data={"title": ev.get("title", ""), "content": ev.get("content", "")},
                        ),
                    )
        except Exception:
            logger.exception("Phase adjustment failed for game %s", game_id)

    async def _broadcast_phase_started(self, room_code: str, phase: Phase, total_phases: int | None = None):
        from madaminu.ws.handler import manager

        total_turns = 3
        if total_phases is None:
            async with self._session_factory() as db:
                from sqlalchemy import func

                count_result = await db.execute(
                    select(func.count()).select_from(Phase).where(Phase.game_id == phase.game_id)
                )
                total_phases = count_result.scalar_one()

                game_result = await db.execute(select(Game).where(Game.id == phase.game_id))
                game = game_result.scalar_one()
                total_turns = game.turn_count or 3
        else:
            total_turns = max(1, (total_phases - 1) // 3)

        adjusted_order = max(0, phase.phase_order - 2)  # skip initial + opening
        turn_number = adjusted_order // 3 + 1

        await manager.broadcast(
            room_code,
            WSMessage(
                type="phase.started",
                data=PhaseStartedData(
                    phase_id=phase.id,
                    phase_type=phase.phase_type,
                    phase_order=phase.phase_order,
                    total_phases=total_phases,
                    duration_sec=phase.duration_sec,
                    turn_number=turn_number,
                    total_turns=total_turns,
                    investigation_locations=phase.investigation_locations,
                ).model_dump(),
            ),
        )

    async def _broadcast_phase_ended(self, room_code: str, ended_phase: Phase, next_phase: Phase | None):
        from madaminu.ws.handler import manager

        await manager.broadcast(
            room_code,
            WSMessage(
                type="phase.ended",
                data=PhaseEndedData(
                    phase_id=ended_phase.id,
                    phase_type=ended_phase.phase_type,
                    next_phase_type=next_phase.phase_type if next_phase else None,
                ).model_dump(),
            ),
        )

    async def _generate_and_broadcast_ending(self, game_id: str, room_code: str):
        from madaminu.models import Evidence, SpeechLog, Vote
        from madaminu.services.scenario_engine import generate_ending
        from madaminu.ws.handler import manager

        try:
            async with self._session_factory() as db:
                ending, usage = await generate_ending(db, game_id)
                logger.info("Ending generated for %s: %s", room_code, usage)

                # Build vote results
                game_result = await db.execute(
                    select(Game).options(selectinload(Game.players)).where(Game.id == game_id)
                )
                game = game_result.scalar_one()
                id_to_name = {p.id: p.character_name or p.display_name for p in game.players}

                votes_result = await db.execute(select(Vote).where(Vote.game_id == game_id))
                votes = votes_result.scalars().all()
                vote_details = [
                    {
                        "voter": id_to_name.get(v.voter_player_id, "?"),
                        "suspect": id_to_name.get(v.suspect_player_id, "?"),
                    }
                    for v in votes
                ]
                vote_counts: dict[str, int] = {}
                for v in votes:
                    name = id_to_name.get(v.suspect_player_id, "?")
                    vote_counts[name] = vote_counts.get(name, 0) + 1
                arrested_name = max(vote_counts, key=vote_counts.get) if vote_counts else None

                # Build scores: speech=1pt, evidence_reveal tracked per player
                logs_result = await db.execute(select(SpeechLog).where(SpeechLog.game_id == game_id))
                all_logs = logs_result.scalars().all()
                speech_counts: dict[str, int] = {}
                for log in all_logs:
                    speech_counts[log.player_id] = speech_counts.get(log.player_id, 0) + 1

                # Evidence reveals: count evidences with source="investigation" per player
                ev_result = await db.execute(
                    select(Evidence).where(Evidence.game_id == game_id, Evidence.source == "investigation")
                )
                all_evidence = ev_result.scalars().all()
                evidence_counts: dict[str, int] = {}
                for ev in all_evidence:
                    evidence_counts[ev.player_id] = evidence_counts.get(ev.player_id, 0) + 1

                rankings = []
                for p in game.players:
                    speeches = speech_counts.get(p.id, 0)
                    evidences = evidence_counts.get(p.id, 0)
                    score = speeches * 1 + evidences * 3
                    rankings.append({
                        "player_id": p.id,
                        "character_name": p.character_name or p.display_name,
                        "speech_count": speeches,
                        "evidence_count": evidences,
                        "score": score,
                    })
                rankings.sort(key=lambda x: -x["score"])

                # Character reveals
                reveals = []
                for p in game.players:
                    reveals.append({
                        "player_id": p.id,
                        "character_name": p.character_name or p.display_name,
                        "role": p.role,
                        "secret_info": p.secret_info,
                        "objective": p.objective,
                    })

            await manager.broadcast(
                room_code,
                WSMessage(
                    type="game.ending",
                    data={
                        "ending_text": ending.ending_text,
                        "true_criminal_id": ending.true_criminal_id,
                        "objective_results": ending.objective_results,
                        "vote_details": vote_details,
                        "vote_counts": vote_counts,
                        "arrested_name": arrested_name,
                        "rankings": rankings,
                        "character_reveals": reveals,
                    },
                ),
            )
        except Exception:
            logger.exception("Ending generation failed for game %s", game_id)
            await manager.broadcast(
                room_code,
                WSMessage(type="error", data={"message": "エンディング生成に失敗しました"}),
            )
