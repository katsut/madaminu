# クラス設計 v3

## デザインパターン

### サーバー側

| パターン | 適用箇所 | 目的 |
|---------|---------|------|
| **Repository** | DB アクセス層 | SQLAlchemy クエリをサービスから分離 |
| **Service** | ビジネスロジック層 | フェーズ遷移、発言権、discoveries 生成 |
| **Router** | HTTP API 層 | リクエスト検証、サービス呼び出し、レスポンス構築 |
| **Background Job** | LLM 呼び出し | API をブロックせず非同期で実行 |
| **Observer (WS)** | リアルタイム通知 | 状態変更時に接続中クライアントへ通知 |

### iOS 側

| パターン | 適用箇所 | 目的 |
|---------|---------|------|
| **Store (ObservableObject)** | 状態管理 | 単方向データフロー |
| **State Machine** | シーン切り替え | active / transitioning の2状態で制御 |
| **API Client** | HTTP 通信 | 型安全なリクエスト/レスポンス |
| **WS Client** | リアルタイム受信 | game.state の差分検出 |

---

## サーバー モジュール構成

```
server/src/madaminu/
├── main.py                     # FastAPI app、lifespan
├── config.py                   # 環境変数
│
├── models/                     # SQLAlchemy ORM
│   ├── game.py                 # Game, GameStatus
│   ├── player.py               # Player, PlayerRole
│   ├── phase.py                # Phase, PhaseType
│   ├── evidence.py             # Evidence, EvidenceSource
│   ├── investigation_selection.py  # NEW: InvestigationSelection
│   ├── speech_log.py           # SpeechLog
│   ├── vote.py                 # Vote
│   ├── game_ending.py          # GameEnding
│   └── note.py                 # Note
│
├── repositories/               # DB クエリ
│   ├── game_repo.py            # Game CRUD
│   ├── phase_repo.py           # Phase CRUD + 排他制御
│   ├── player_repo.py          # Player CRUD
│   ├── evidence_repo.py        # Evidence CRUD
│   ├── selection_repo.py       # NEW: InvestigationSelection CRUD
│   └── speech_repo.py          # SpeechLog CRUD
│
├── services/                   # ビジネスロジック
│   ├── game_service.py         # NEW: フェーズ遷移、ゲーム進行
│   ├── speech_service.py       # NEW: 発言権管理（DB ベース）
│   ├── discovery_service.py    # NEW: discoveries 生成（LLM + DB）
│   ├── scenario_engine.py      # シナリオ生成、証拠改ざん、エンディング
│   ├── map_builder.py          # マップ構築
│   ├── map_renderer.py         # SVG 描画
│   ├── ai_player.py            # AI プレイヤー生成・発言
│   └── image_generator.py      # 画像生成
│
├── routers/                    # HTTP API
│   ├── rooms.py                # ルーム CRUD、参加
│   ├── game.py                 # ゲーム開始、advance、state
│   ├── investigation.py        # NEW: select-location、keep、tamper、discoveries
│   ├── speech.py               # NEW: speech/request、speech/release
│   ├── characters.py           # キャラクター作成
│   └── images.py               # 画像配信
│
├── ws/                         # WebSocket
│   ├── manager.py              # 接続管理、broadcast
│   └── handler.py              # 接続時 game.state 送信、ping/pong
│
├── jobs/                       # NEW: バックグラウンドジョブ
│   ├── discovery_job.py        # discoveries 一括生成
│   ├── ending_job.py           # エンディング生成
│   └── ai_speech_job.py        # AI 発言生成
│
└── templates/                  # LLM プロンプト
```

---

## サーバー クラス設計

### GameService

フェーズ遷移のコア。メモリ状態なし、全て DB 操作。

```python
class GameService:
    def __init__(self, session_factory):
        self._sf = session_factory

    async def advance_phase(self, game_id: str, force: bool = False) -> AdvanceResult:
        """フェーズを次に進める。排他制御付き。"""
        async with self._sf() as db:
            game = await db.execute(select(Game).where(Game.id == game_id))
            phase = await db.execute(select(Phase).where(Phase.id == game.current_phase_id))

            if not force and phase.deadline_at and datetime.utcnow() < phase.deadline_at:
                return AdvanceResult(status="not_expired", remaining_sec=...)

            # 排他制御: ended_at が NULL のもののみ更新
            result = await db.execute(
                update(Phase)
                .where(Phase.id == phase.id, Phase.ended_at.is_(None))
                .values(ended_at=datetime.utcnow())
            )
            if result.rowcount == 0:
                # 他クライアントが先に遷移済み
                current = await self._get_current_phase(db, game_id)
                return AdvanceResult(status="already_advanced", phase=current)

            next_phase = await self._get_next_phase(db, game, phase)
            next_phase.started_at = datetime.utcnow()
            next_phase.deadline_at = datetime.utcnow() + timedelta(seconds=next_phase.duration_sec)
            game.current_phase_id = next_phase.id
            await db.commit()

            return AdvanceResult(status="advanced", phase=next_phase)

    async def get_state(self, game_id: str, player_id: str) -> GameState:
        """プレイヤー視点のゲーム状態を返す。"""

    async def select_location(self, game_id: str, player_id: str, location_id: str):
        """調査場所を選択。investigation_selections に保存。"""

    async def auto_assign_locations(self, game_id: str, phase_id: str):
        """未選択プレイヤーにランダム割り当て。"""
```

### AdvanceResult

```python
@dataclass
class AdvanceResult:
    status: str  # "advanced" | "already_advanced" | "not_expired"
    phase: Phase | None = None
    remaining_sec: int | None = None
```

### SpeechService

発言権管理。全て DB ベース。

```python
class SpeechService:
    def __init__(self, session_factory):
        self._sf = session_factory

    async def request_speech(self, game_id: str, player_id: str) -> bool:
        """発言権を取得。現在の発言者がいれば割り込み。"""
        async with self._sf() as db:
            phase = await self._get_current_phase(db, game_id)
            if phase.current_speaker_id == player_id:
                return True
            # 前の発言者を解放
            prev_speaker = phase.current_speaker_id
            phase.current_speaker_id = player_id
            await db.commit()
            return True  # prev_speaker があれば WS で通知

    async def release_speech(self, game_id: str, player_id: str, transcript: str) -> bool:
        """発言終了。SpeechLog に保存。"""
        async with self._sf() as db:
            phase = await self._get_current_phase(db, game_id)
            if phase.current_speaker_id != player_id:
                return False
            phase.current_speaker_id = None
            if transcript:
                db.add(SpeechLog(game_id=game_id, player_id=player_id, phase_id=phase.id, transcript=transcript))
            await db.commit()
            return True
```

### DiscoveryService

discoveries 生成。LLM 呼び出しは DB セッション外で行う。

```python
class DiscoveryService:
    def __init__(self, session_factory):
        self._sf = session_factory

    async def generate_all(self, game_id: str, phase_id: str):
        """全プレイヤーの discoveries を一括生成。バックグラウンドジョブとして実行。"""

        # 1. DB から必要情報を取得
        async with self._sf() as db:
            game, players, selections = await self._load_context(db, game_id, phase_id)
            phase = await db.execute(select(Phase).where(Phase.id == phase_id))
            phase.discoveries_status = "generating"
            await db.commit()
        # DB セッション解放

        # 2. LLM 呼び出し（並列、DB 不要）
        results = await asyncio.gather(*[
            self._generate_for_player(game, player, location)
            for player, location in selections
        ])

        # 3. 結果を DB に保存
        async with self._sf() as db:
            for player_id, discoveries in results:
                for d in discoveries:
                    db.add(Evidence(source="discovery", ...))
            phase = await db.execute(select(Phase).where(Phase.id == phase_id))
            phase.discoveries_status = "ready"
            await db.commit()
        # DB セッション解放

        # 4. WS 通知
        await ws_manager.broadcast_game_state(game_id)

    async def _generate_for_player(self, game, player, location) -> tuple[str, list[dict]]:
        """1プレイヤー分の discoveries を LLM で生成。DB アクセスなし。"""
        raw, usage = await llm_client.generate_json(system_prompt, user_prompt)
        return player.id, parse_discoveries(raw)

    async def get_discoveries(self, game_id: str, player_id: str, phase_id: str) -> list[dict]:
        """DB から discoveries を取得。"""
        async with self._sf() as db:
            result = await db.execute(
                select(Evidence).where(
                    Evidence.game_id == game_id,
                    Evidence.player_id == player_id,
                    Evidence.phase_id == phase_id,
                    Evidence.source == "discovery",
                )
            )
            return [{"id": e.id, "title": e.title, "content": e.content, "feature": ...} for e in result.scalars()]
```

### WSManager

通知のみ。データは最小限。

```python
class WSManager:
    def __init__(self):
        self._connections: dict[str, dict[str, WebSocket]] = {}  # room_code -> {player_id: ws}

    async def connect(self, room_code: str, player_id: str, ws: WebSocket):
        """接続時に game.state を自動送信。"""
        self._connections.setdefault(room_code, {})[player_id] = ws
        state = await game_service.get_state(game_id, player_id)
        await ws.send_json({"type": "game.state", "data": state})

    async def broadcast_game_state(self, game_id: str):
        """全プレイヤーに game.state を送信。フェーズ変更時に呼ぶ。"""
        for player_id, ws in self._connections.get(room_code, {}).items():
            state = await game_service.get_state(game_id, player_id)
            await ws.send_json({"type": "game.state", "data": state})

    async def broadcast(self, room_code: str, message: dict):
        """軽量通知を全員に送信。"""
        for ws in self._connections.get(room_code, {}).values():
            await ws.send_json(message)

    async def send_ping(self):
        """20秒間隔で全接続に ping。lifespan の定期タスクとして実行。"""
```

---

## iOS モジュール構成

```
ios/Madaminu/Sources/
├── App/
│   └── MadaminuApp.swift
│
├── Models/
│   ├── GameState.swift          # PhaseInfo, DiscoveryItem, SpeechEntry 等
│   └── Room.swift               # PlayerInfo, RoomListItem 等
│
├── Network/
│   ├── APIClient.swift          # HTTP API 呼び出し（型安全）
│   ├── WebSocketClient.swift    # WS 接続、再接続、ping/pong
│   └── ImageCache.swift         # 画像キャッシュ
│
├── Store/
│   ├── AppStore.swift           # メイン Store
│   ├── AppAction.swift          # アクション enum
│   ├── Screen.swift             # 画面遷移 enum
│   ├── PhaseScreenState.swift   # NEW: active / transitioning
│   ├── GamePlayStore.swift      # ゲーム状態
│   ├── RoomStore.swift          # ルーム状態
│   └── NotebookStore.swift      # 手帳状態
│
├── Services/
│   ├── GameStateSync.swift      # NEW: game.state 差分検出、シーン切り替え
│   ├── DeviceIdentifier.swift
│   └── SpeechRecognizer.swift
│
├── Views/
│   ├── HomeView.swift
│   ├── RoomLobbyView.swift
│   ├── CharacterCreationView.swift
│   ├── GeneratingView.swift     # フェーズガイド表示
│   ├── IntroView.swift
│   ├── GamePlayView.swift
│   ├── PhaseTransitionOverlay.swift  # 遷移画面
│   ├── NotebookView.swift
│   └── phases/                  # NEW: フェーズ別ビュー分割
│       ├── StorytellingView.swift
│       ├── OpeningView.swift
│       ├── DiscussionView.swift
│       ├── PlanningView.swift
│       ├── InvestigationView.swift
│       ├── VotingView.swift
│       └── EndingView.swift
│
└── DesignSystem/
```

---

## iOS クラス設計

### GameStateSync

game.state の差分検出とシーン切り替えの責務。

```swift
class GameStateSync {

    func apply(serverState: GameState, store: AppStore) {
        let localPhaseId = store.game.currentPhase?.phaseId
        let serverPhaseId = serverState.currentPhase?.id

        if localPhaseId != serverPhaseId {
            // フェーズが変わった → 遷移画面を表示
            store.phaseScreen = .transitioning(nextPhase: serverState.currentPhase)
            applyFullState(serverState, store: store)

            // 3秒後にアクティブに（discoveries 生成中でなければ）
            if serverState.currentPhase?.discoveriesStatus != "generating" {
                DispatchQueue.main.asyncAfter(deadline: .now() + 3) {
                    store.phaseScreen = .active
                }
            }
        } else {
            // 同じフェーズ → 差分だけ更新
            applyDiff(serverState, store: store)
        }
    }

    private func applyDiff(serverState: GameState, store: AppStore) {
        // タイマー更新
        // 発言履歴追加
        // 投票状況更新
        // discoveries_status チェック（generating → ready）
        if store.phaseScreen == .transitioning,
           serverState.currentPhase?.discoveriesStatus == "ready" {
            DispatchQueue.main.asyncAfter(deadline: .now() + 3) {
                store.phaseScreen = .active
            }
        }
    }
}
```

### PhaseScreenState

```swift
enum PhaseScreenState {
    case active                              // フェーズ画面を表示
    case transitioning(nextPhase: PhaseInfo?) // 遷移画面を表示
}
```

### APIClient（拡張）

全アクションを型安全に。

```swift
actor APIClient {
    func advance(roomCode: String) async throws -> AdvanceResponse
    func selectLocation(roomCode: String, locationId: String) async throws
    func keepEvidence(roomCode: String, discoveryId: String) async throws -> EvidenceResponse
    func requestSpeech(roomCode: String) async throws -> Bool
    func releaseSpeech(roomCode: String, transcript: String) async throws
    func revealEvidence(roomCode: String, evidenceId: String) async throws
    func vote(roomCode: String, suspectId: String) async throws
    func getState(roomCode: String) async throws -> GameState
    func getDiscoveries(roomCode: String) async throws -> [Discovery]
}

struct AdvanceResponse: Codable {
    let result: String  // "advanced" | "already_advanced" | "not_expired"
    let phase: PhaseInfo?
    let remainingSec: Int?
}
```

---

## 依存関係

```
Router → Service → Repository → DB
                 → LLM Client (jobs 経由)
                 → WS Manager (通知送信)
```

- Router は Service のみに依存（DB に直接アクセスしない）
- Service は Repository と LLM Client に依存
- Repository は SQLAlchemy のみに依存
- WS Manager は独立（Service から通知送信の依頼を受ける）
- Jobs は Service と同じ層（Service 経由で呼び出し可能）
