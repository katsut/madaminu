import asyncio
import logging
from datetime import datetime

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

    async def start_first_phase(self, game_id: str, room_code: str) -> Phase:
        async with self._session_factory() as db:
            result = await db.execute(select(Phase).where(Phase.game_id == game_id).order_by(Phase.phase_order))
            phases = result.scalars().all()
            if not phases:
                raise ValueError("No phases found for game")

            first_phase = phases[0]
            first_phase.started_at = datetime.utcnow()

            game_result = await db.execute(select(Game).where(Game.id == game_id))
            game = game_result.scalar_one()
            game.current_phase_id = first_phase.id
            await db.commit()

        await self._broadcast_phase_started(room_code, first_phase)
        self._start_timer(game_id, room_code, first_phase)
        asyncio.create_task(self._schedule_ai_speeches(game_id, room_code, first_phase))
        return first_phase

    async def advance_phase(self, game_id: str, room_code: str) -> Phase | None:
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
                return None

            next_phase = sorted_phases[current_idx + 1]
            next_phase.started_at = datetime.utcnow()
            game.current_phase_id = next_phase.id

            if next_phase.phase_type == PhaseType.voting:
                game.status = GameStatus.voting

            await db.commit()

        await self._broadcast_phase_ended(room_code, current_phase, next_phase)

        await self._run_phase_adjustment(game_id, room_code, current_phase.id)

        await self._broadcast_phase_started(room_code, next_phase)
        self._start_timer(game_id, room_code, next_phase)
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
        await self.advance_phase(game_id, room_code)

    async def _schedule_ai_speeches(self, game_id: str, room_code: str, phase: Phase):
        if phase.phase_type not in (PhaseType.discussion, PhaseType.investigation):
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

    async def _broadcast_phase_started(self, room_code: str, phase: Phase):
        from madaminu.ws.handler import manager

        await manager.broadcast(
            room_code,
            WSMessage(
                type="phase.started",
                data=PhaseStartedData(
                    phase_id=phase.id,
                    phase_type=phase.phase_type,
                    phase_order=phase.phase_order,
                    duration_sec=phase.duration_sec,
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
