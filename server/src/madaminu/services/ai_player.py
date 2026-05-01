import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from madaminu.llm.client import LIGHT_MODEL, LLMUsage, llm_client
from madaminu.models import ConnectionStatus, Game, Player, SpeechLog

logger = logging.getLogger(__name__)


async def _generate_ai_character(existing_characters: list[str], setting: str) -> dict:
    system_prompt = "あなたはマーダーミステリーのキャラクター生成AIです。"
    user_prompt = (
        f"以下の設定に合ったオリジナルのキャラクターを1人生成してください。\n\n"
        f"## 舞台設定\n{setting}\n\n"
        f"## 既存キャラクター（重複しないこと）\n"
        f"{', '.join(existing_characters) if existing_characters else 'なし'}\n\n"
        f"JSONで返してください:\n"
        f'{{"character_name": "名前", "character_name_kana": "なまえ", '
        f'"character_gender": "男/女", "character_age": "年齢", '
        f'"character_occupation": "職業", '
        f'"character_appearance": "外見の説明（2文）", '
        f'"character_personality": "性格の説明（2〜3文）", '
        f'"character_background": "経歴の説明（2〜3文）"}}\n\n'
        f"キャラクターは舞台設定に自然に存在する人物にしてください。"
        f"既存キャラクターと名前・職業が被らないようにしてください。"
    )
    raw, usage = await llm_client.generate_json(system_prompt, user_prompt, model=LIGHT_MODEL)
    from madaminu.services.scenario_engine import _parse_scenario_json

    return _parse_scenario_json(raw), usage


async def fill_ai_players(db: AsyncSession, game_id: str, target_count: int = 4) -> list[Player]:
    result = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.id == game_id))
    game = result.scalar_one()

    human_count = len(game.players)
    needed = max(0, target_count - human_count)
    if needed == 0:
        return []

    existing_names = [p.character_name for p in game.players if p.character_name]
    setting = ""
    if game.scenario_skeleton:
        s = game.scenario_skeleton.get("setting", {})
        setting = s.get("location", "") or s.get("situation", "") or ""

    logger.info("fill_ai_players: game=%s needed=%d setting=%r", game_id, needed, setting)
    ai_players = []
    for i in range(needed):
        try:
            char, usage = await _generate_ai_character(existing_names, setting)
            game.total_llm_cost_usd += usage.estimated_cost_usd
            name = char.get("character_name", f"AI_{uuid.uuid4().hex[:6]}")
            logger.info("fill_ai_players: generated AI %d/%d name=%s", i + 1, needed, name)
            player = Player(
                id=str(uuid.uuid4()),
                game_id=game_id,
                session_token=str(uuid.uuid4()),
                display_name=f"AI・{name}",
                character_name=name,
                character_name_kana=char.get("character_name_kana", ""),
                character_gender=char.get("character_gender", "不明"),
                character_age=char.get("character_age", "不明"),
                character_occupation=char.get("character_occupation", "不明"),
                character_appearance=char.get("character_appearance", ""),
                character_personality=char.get("character_personality", ""),
                character_background=char.get("character_background", ""),
                is_host=False,
                is_ai=True,
                is_ready=True,
                connection_status=ConnectionStatus.online,
            )
            db.add(player)
            ai_players.append(player)
            existing_names.append(name)
        except Exception:
            logger.exception("fill_ai_players: failed to generate AI character %d/%d", i + 1, needed)

    await db.commit()
    logger.info("Added %d AI players to game %s", len(ai_players), game_id)
    return ai_players


PHASE_SPEECH_INSTRUCTIONS = {
    "opening": (
        "今は自己紹介タイムです。"
        "必ず一人称（「私は」「俺は」「僕は」等）で自分の名前から始めてください。"
        "例: 「私は〇〇です。今日は△△として参りました。」"
        "この集まりに来た理由、自分の職業や立場を紹介してください。"
        "推理や事件の話はまだしないでください。"
    ),
    "discussion": (
        "今は議論フェーズです。"
        "推理や質問、意見を述べてください。"
        "他のプレイヤーの発言に反応することも大切です。"
        "証拠に基づいた主張を心がけてください。"
    ),
    "voting": (
        "今は投票フェーズです。"
        "誰が犯人だと思うか、最後の主張をしてください。"
        "これまでの議論を踏まえた発言をしてください。"
    ),
}


async def generate_ai_speech(
    db: AsyncSession,
    game_id: str,
    player_id: str,
    phase_id: str,
) -> tuple[str, LLMUsage]:
    from madaminu.models import Phase

    game_result = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.id == game_id))
    game = game_result.scalar_one()

    player = next((p for p in game.players if p.id == player_id), None)
    if player is None:
        return "", LLMUsage(model=LIGHT_MODEL, input_tokens=0, output_tokens=0, duration_ms=0)

    phase_result = await db.execute(select(Phase).where(Phase.id == phase_id))
    phase = phase_result.scalar_one_or_none()
    phase_type = phase.phase_type if phase else "discussion"

    logs_result = await db.execute(
        select(SpeechLog)
        .where(SpeechLog.game_id == game_id, SpeechLog.phase_id == phase_id)
        .order_by(SpeechLog.created_at)
    )
    recent_logs = logs_result.scalars().all()

    id_to_name = {p.id: p.character_name or p.display_name for p in game.players}
    conversation = "\n".join(f"[{id_to_name.get(log.player_id, '?')}]: {log.transcript}" for log in recent_logs[-10:])

    phase_instruction = PHASE_SPEECH_INSTRUCTIONS.get(
        phase_type,
        PHASE_SPEECH_INSTRUCTIONS["discussion"],
    )
    system_prompt = (
        f"あなたは「{player.character_name}」本人です。"
        f"あなたの一人称視点で話してください。"
        f"地の文やナレーションは禁止。台詞のみを出力してください。"
        f"自然な日本語で1〜3文の短い発言をしてください。"
        f"{phase_instruction}"
    )

    user_prompt = (
        f"## あなた（{player.character_name}）の情報\n"
        f"性格: {player.character_personality}\n"
        f"秘密（他の人には言えない）: {player.secret_info or 'なし'}\n"
        f"目的（他の人にバレてはいけない）: {player.objective or 'なし'}\n\n"
        f"## これまでの会話\n{conversation if conversation else '(まだ発言なし)'}\n\n"
        f"「{player.character_name}」として1〜3文で発言してください。"
        f"台詞のみ。「」やナレーション不要。"
    )

    text, usage = await llm_client.generate(system_prompt, user_prompt, model=LIGHT_MODEL, max_tokens=200)

    speech_log = SpeechLog(
        id=str(uuid.uuid4()),
        game_id=game_id,
        player_id=player_id,
        phase_id=phase_id,
        transcript=text.strip(),
    )
    db.add(speech_log)
    await db.commit()

    return text.strip(), usage
