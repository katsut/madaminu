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
        "character_name_kana": "やまだ はなこ",
        "character_gender": "女",
        "character_age": "42",
        "character_occupation": "主婦",
        "character_appearance": "小柄でふくよかな体型。明るい茶色のパーマヘアに花柄のエプロンがトレードマーク。よく笑い、表情が豊か。",
        "character_personality": "明るく社交的で、誰とでもすぐに打ち解ける。好奇心旺盛で噂話が大好きだが、根は面倒見がよく、困っている人を放っておけない。ただし秘密を守るのは苦手で、うっかり口を滑らせることがある。",
        "character_background": "この地域で20年以上暮らすベテラン主婦。町内会の副会長を務め、近隣の家庭事情や人間関係に精通している。最近、夫の定年後の生活に不安を感じており、パート先を探している。",
    },
    {
        "display_name": "AI・鈴木 太郎",
        "character_name": "鈴木 太郎",
        "character_name_kana": "すずき たろう",
        "character_gender": "男",
        "character_age": "55",
        "character_occupation": "大学教授",
        "character_appearance": "銀縁眼鏡をかけた痩身の長身。白髪交じりの短髪で、常にツイードのジャケットを着用。指にはインクの染みが残っている。",
        "character_personality": "慎重で理論的。感情的になることは滅多になく、常にデータと論理で物事を判断する。議論好きで、相手の矛盾を指摘するのが得意。ただし人情の機微には疎く、空気を読めないことがある。",
        "character_background": "東都大学で犯罪心理学を30年以上研究してきたベテラン教授。数百件の犯罪事例を分析し、プロファイリングの第一人者として知られる。退官を間近に控え、集大成となる論文の執筆に取り組んでいる。",
    },
    {
        "display_name": "AI・佐藤 美咲",
        "character_name": "佐藤 美咲",
        "character_name_kana": "さとう みさき",
        "character_gender": "女",
        "character_age": "28",
        "character_occupation": "新聞記者",
        "character_appearance": "ショートカットの黒髪で活発な印象。常にメモ帳とペンを持ち歩き、動きやすいパンツスーツを着ている。目力が強い。",
        "character_personality": "直感的で行動力があり、気になることはすぐに調べずにはいられない。正義感が強く、不正を許さない性格。ただしスクープへの執着が強く、時に周囲の迷惑を顧みないこともある。酒が入ると本音が出やすい。",
        "character_background": "全国紙の社会部で政治家の汚職や企業不正を追うエース記者。半年前、信頼していた先輩記者が不審な事故で亡くなり、その裏に大きな陰謀があると確信している。今も独自に調査を続けている。",
    },
    {
        "display_name": "AI・田中 健二",
        "character_name": "田中 健二",
        "character_name_kana": "たなか けんじ",
        "character_gender": "男",
        "character_age": "63",
        "character_occupation": "喫茶店マスター",
        "character_appearance": "がっしりした体格で、穏やかな目つきの中に鋭い眼光を隠す。白髪のオールバックに整えられた口ひげ。年季の入ったエプロンをつけている。",
        "character_personality": "穏やかで寡黙だが、洞察力が非常に鋭い。何気ない会話から嘘を見抜く能力がある。常連客の相談相手になることも多く、信頼が厚い。ただし過去のある事件がトラウマとなっており、時折暗い表情を見せる。",
        "character_background": "元警視庁捜査一課の刑事。数多くの難事件を解決してきたが、15年前に担当した事件で大きな失態を犯し、責任を取って退職。以来、下町で小さな喫茶店を営みながら静かに暮らしている。",
    },
    {
        "display_name": "AI・中村 さくら",
        "character_name": "中村 さくら",
        "character_name_kana": "なかむら さくら",
        "character_gender": "女",
        "character_age": "31",
        "character_occupation": "図書館司書",
        "character_appearance": "長い黒髪をきっちり一つにまとめ、丸い眼鏡をかけている。落ち着いた色合いの服装で、常にどこか本を一冊携えている。声が小さく、静かな雰囲気。",
        "character_personality": "控えめで口数は少ないが、芯が強く自分の意見はしっかり持っている。観察力に優れ、人の細かな変化や矛盾に気づく。記憶力が抜群で、一度読んだものは忘れない。ただし人付き合いが苦手で、大勢の場では緊張する。",
        "character_background": "市立図書館で司書として10年勤務。膨大な蔵書に囲まれて静かに過ごす日々を送っている。趣味は推理小説の読破で、実在の未解決事件についても独自にファイリングしている。最近、図書館に届いた奇妙な匿名の手紙が気になっている。",
    },
    {
        "display_name": "AI・高橋 龍一",
        "character_name": "高橋 龍一",
        "character_name_kana": "たかはし りゅういち",
        "character_gender": "男",
        "character_age": "48",
        "character_occupation": "漁師",
        "character_appearance": "日焼けした浅黒い肌と太い腕。短く刈り込んだ髪に、豪快な笑顔が特徴。手のひらにはタコが多数あり、作業着姿が板についている。",
        "character_personality": "豪快で率直。思ったことをそのまま口にする裏表のない性格。義理人情に厚く、仲間を守るためなら体を張る。ただし短気な一面があり、嘘や裏切りを極端に嫌う。海の上では誰よりも冷静な判断ができる。",
        "character_background": "三代続く漁師の家に生まれ、15歳から船に乗っている。地元の漁協でまとめ役を務め、若手の育成にも力を入れている。5年前の大型台風で漁船を失った仲間を助けるために借金を背負い、今もその返済を続けている。",
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
            character_name_kana=template["character_name_kana"],
            character_gender=template["character_gender"],
            character_age=template["character_age"],
            character_occupation=template["character_occupation"],
            character_appearance=template["character_appearance"],
            character_personality=template["character_personality"],
            character_background=template["character_background"],
            is_host=False,
            is_ai=True,
            is_ready=True,
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
