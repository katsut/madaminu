"""Speech management service. All state in DB, no memory state."""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from madaminu.models import SpeechLog
from madaminu.repositories import phase_repo

logger = logging.getLogger(__name__)


class SpeechService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._sf = session_factory

    async def request_speech(self, game_id: str, player_id: str) -> tuple[bool, str | None]:
        """Request speech. Returns (granted, previous_speaker_id)."""
        async with self._sf() as db:
            phase = await phase_repo.get_current_phase(db, game_id)
            if not phase:
                return False, None

            prev = phase.current_speaker_id
            if prev == player_id:
                return True, None

            phase.current_speaker_id = player_id
            await db.commit()
            return True, prev

    async def release_speech(self, game_id: str, player_id: str, transcript: str) -> bool:
        """Release speech and save transcript."""
        async with self._sf() as db:
            phase = await phase_repo.get_current_phase(db, game_id)
            if not phase or phase.current_speaker_id != player_id:
                return False

            phase.current_speaker_id = None

            if transcript:
                db.add(
                    SpeechLog(
                        id=str(uuid.uuid4()),
                        game_id=game_id,
                        player_id=player_id,
                        phase_id=phase.id,
                        transcript=transcript,
                    )
                )

            await db.commit()
            return True

    async def get_current_speaker(self, game_id: str) -> str | None:
        async with self._sf() as db:
            phase = await phase_repo.get_current_phase(db, game_id)
            return phase.current_speaker_id if phase else None
