import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from madaminu.llm.client import LIGHT_MODEL, LLMUsage, llm_client
from madaminu.models import ConnectionStatus, Game, Player, SpeechLog

logger = logging.getLogger(__name__)

AI_CHARACTER_TEMPLATES = [
    {
        "display_name": "AI・山田 花子",
        "character_name": "山田 花子",
        "character_personality": "明るく社交的。好奇心旺盛で、ちょっとおせっかい。",
        "character_background": "近所に住む主婦。地域の噂話に詳しい。",
    },
    {
        "display_name": "AI・鈴木 太郎",
        "character_name": "鈴木 太郎",
        "character_personality": "慎重で理論的。物事を冷静に分析する。",
        "character_background": "大学教授。犯罪心理学を専門としている。",
    },
    {
        "display_name": "AI・佐藤 美咲",
        "character_name": "佐藤 美咲",
        "character_personality": "直感的で行動力がある。正義感が強い。",
        "character_background": "新聞記者。事件の真相を追い求めている。",
    },
    {
        "display_name": "AI・田中 健二",
        "character_name": "田中 健二",
        "character_personality": "穏やかだが洞察力が鋭い。人の嘘を見抜く。",
        "character_background": "引退した刑事。今は喫茶店のマスター。",
    },
    {
        "display_name": "AI・中村 さくら",
        "character_name": "中村 さくら",
        "character_personality": "控えめだが芯が強い。観察力に優れている。",
        "character_background": "図書館司書。静かに周囲を観察している。",
    },
    {
        "display_name": "AI・高橋 龍一",
        "character_name": "高橋 龍一",
        "character_personality": "豪快で率直。思ったことをそのまま言う。",
        "character_background": "地元の漁師。海の男で義理人情に厚い。",
    },
]


async def fill_ai_players(db: AsyncSession, game_id: str, target_count: int = 4) -> list[Player]:
    result = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.id == game_id))
    game = result.scalar_one()

    human_count = len(game.players)
    needed = max(0, target_count - human_count)
    if needed == 0:
        return []

    used_names = {p.character_name for p in game.players if p.character_name}
    available = [t for t in AI_CHARACTER_TEMPLATES if t["character_name"] not in used_names]

    ai_players = []
    for i in range(min(needed, len(available))):
        template = available[i]
        player = Player(
            id=str(uuid.uuid4()),
            game_id=game_id,
            session_token=str(uuid.uuid4()),
            display_name=template["display_name"],
            character_name=template["character_name"],
            character_personality=template["character_personality"],
            character_background=template["character_background"],
            is_host=False,
            is_ai=True,
            connection_status=ConnectionStatus.online,
        )
        db.add(player)
        ai_players.append(player)

    await db.commit()
    logger.info("Added %d AI players to game %s", len(ai_players), game_id)
    return ai_players


async def generate_ai_speech(
    db: AsyncSession,
    game_id: str,
    player_id: str,
    phase_id: str,
) -> tuple[str, LLMUsage]:
    game_result = await db.execute(select(Game).options(selectinload(Game.players)).where(Game.id == game_id))
    game = game_result.scalar_one()

    player = next((p for p in game.players if p.id == player_id), None)
    if player is None:
        return "", LLMUsage(model=LIGHT_MODEL, input_tokens=0, output_tokens=0, duration_ms=0)

    logs_result = await db.execute(
        select(SpeechLog)
        .where(SpeechLog.game_id == game_id, SpeechLog.phase_id == phase_id)
        .order_by(SpeechLog.created_at)
    )
    recent_logs = logs_result.scalars().all()

    id_to_name = {p.id: p.character_name or p.display_name for p in game.players}
    conversation = "\n".join(f"[{id_to_name.get(log.player_id, '?')}]: {log.transcript}" for log in recent_logs[-10:])

    system_prompt = (
        "あなたはマーダーミステリーゲームのAIプレイヤーです。"
        "キャラクターになりきって、自然な日本語で1〜3文の短い発言をしてください。"
        "推理や質問、意見を述べてください。他のプレイヤーの発言に反応することも大切です。"
    )

    user_prompt = (
        f"## あなたのキャラクター\n"
        f"名前: {player.character_name}\n"
        f"性格: {player.character_personality}\n"
        f"秘密: {player.secret_info or 'なし'}\n"
        f"目的: {player.objective or 'なし'}\n\n"
        f"## シナリオ\n{game.scenario_skeleton}\n\n"
        f"## これまでの会話\n{conversation if conversation else '(まだ発言なし)'}\n\n"
        f"キャラクターとして1〜3文で発言してください。JSON不要、発言テキストのみ。"
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
