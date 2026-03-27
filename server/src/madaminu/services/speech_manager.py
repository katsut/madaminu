import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from madaminu.models import Game, SpeechLog
from madaminu.ws.messages import SpeechActiveData, SpeechReleasedData, WSMessage

logger = logging.getLogger(__name__)


class SpeechManager:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory
        self._locks: dict[str, asyncio.Lock] = {}
        self._speakers: dict[str, str | None] = {}

    def _get_lock(self, room_code: str) -> asyncio.Lock:
        if room_code not in self._locks:
            self._locks[room_code] = asyncio.Lock()
        return self._locks[room_code]

    async def request_speech(self, room_code: str, player_id: str) -> bool:
        lock = self._get_lock(room_code)
        if lock.locked():
            return False

        acquired = lock.locked()
        if not acquired:
            await lock.acquire()
            self._speakers[room_code] = player_id
            return True
        return False

    async def release_speech(
        self,
        room_code: str,
        player_id: str,
        transcript: str,
    ) -> bool:
        if self._speakers.get(room_code) != player_id:
            return False

        lock = self._get_lock(room_code)
        self._speakers[room_code] = None

        if lock.locked():
            lock.release()

        if transcript:
            await self._save_transcript(room_code, player_id, transcript)

        return True

    def get_current_speaker(self, room_code: str) -> str | None:
        return self._speakers.get(room_code)

    def cleanup_room(self, room_code: str):
        lock = self._locks.pop(room_code, None)
        if lock and lock.locked():
            lock.release()
        self._speakers.pop(room_code, None)

    def force_release(self, room_code: str):
        lock = self._get_lock(room_code)
        self._speakers[room_code] = None
        if lock.locked():
            lock.release()

    async def _save_transcript(self, room_code: str, player_id: str, transcript: str):
        async with self._session_factory() as db:
            game_result = await db.execute(select(Game).where(Game.room_code == room_code))
            game = game_result.scalar_one_or_none()
            if game is None or game.current_phase_id is None:
                return

            speech_log = SpeechLog(
                id=str(uuid.uuid4()),
                game_id=game.id,
                player_id=player_id,
                phase_id=game.current_phase_id,
                transcript=transcript,
            )
            db.add(speech_log)
            await db.commit()

    async def broadcast_speech_granted(self, room_code: str, player_id: str):
        from madaminu.ws.handler import manager

        await manager.broadcast(
            room_code,
            WSMessage(
                type="speech.active",
                data=SpeechActiveData(player_id=player_id).model_dump(),
            ),
        )

    async def broadcast_speech_released(self, room_code: str, player_id: str, transcript: str = ""):
        from madaminu.ws.handler import manager

        character_name = ""
        if transcript:
            async with self._session_factory() as db:
                from madaminu.models import Player

                result = await db.execute(select(Player).where(Player.id == player_id))
                player = result.scalar_one_or_none()
                if player:
                    character_name = player.character_name or player.display_name

        await manager.broadcast(
            room_code,
            WSMessage(
                type="speech.released",
                data={
                    "player_id": player_id,
                    "character_name": character_name,
                    "transcript": transcript,
                },
            ),
        )
