# クラス設計 v3

## デザインパターン

### サーバー側

| パターン | 適用箇所 | 目的 |
|---------|---------|------|
| **Repository** | DB アクセス層 | SQLAlchemy クエリをサービスから分離 |
| **Service** | ビジネスロジック層 | フェーズ遷移、発言権、discoveries 生成。メモリ状態なし |
| **Router** | HTTP API 層 | ゲーム外操作（ルーム作成等） |
| **WS Handler** | WS メッセージ処理 | メッセージの振り分け、バリデーション、サービス呼び出し |
| **Background Job** | LLM 呼び出し | WS をブロックせず非同期で実行 |
| **Observer (WS)** | リアルタイム通知 | 状態変更時に接続中クライアントへ game.state 送信 |

### iOS 側

| パターン | 適用箇所 | 目的 |
|---------|---------|------|
| **Store (ObservableObject)** | 状態管理 | 単方向データフロー |
| **State Machine** | シーン切り替え | active / transitioning の2状態 |
| **GameStateSync** | 差分検出 | game.state 受信時にローカルとの差分を適用 |
| **WS Client** | 全ゲーム通信 | 送受信、ping/pong、再接続 |
| **API Client** | ゲーム外操作 | ルーム作成、画像取得等 |

---

## サーバー モジュール構成

```
server/src/madaminu/
├── main.py                        # FastAPI app、lifespan、ping タスク
├── config.py                      # 環境変数
│
├── models/                        # SQLAlchemy ORM
│   ├── game.py                    # Game, GameStatus
│   ├── player.py                  # Player, PlayerRole
│   ├── phase.py                   # Phase, PhaseType（storytelling 追加）
│   ├── evidence.py                # Evidence, EvidenceSource（discovery 追加）
│   ├── investigation_selection.py # NEW
│   ├── speech_log.py              # SpeechLog
│   ├── vote.py                    # Vote
│   ├── game_ending.py             # GameEnding
│   └── note.py                    # Note
│
├── repositories/                  # DB クエリ
│   ├── game_repo.py
│   ├── phase_repo.py              # 排他制御つき advance
│   ├── player_repo.py
│   ├── evidence_repo.py
│   ├── selection_repo.py          # NEW
│   └── speech_repo.py
│
├── services/                      # ビジネスロジック（メモリ状態なし）
│   ├── game_service.py            # NEW: フェーズ遷移
│   ├── speech_service.py          # NEW: 発言権管理（DB）
│   ├── discovery_service.py       # NEW: discoveries 生成（LLM + DB）
│   ├── scenario_engine.py         # シナリオ生成、改ざん、エンディング
│   ├── map_builder.py             # マップ構築
│   ├── map_renderer.py            # SVG 描画
│   ├── ai_player.py               # AI プレイヤー生成・発言
│   └── image_generator.py         # 画像生成
│
├── routers/                       # HTTP API（ゲーム外操作）
│   ├── rooms.py                   # ルーム CRUD、参加、準備完了
│   ├── game.py                    # ゲーム開始、状態取得、discoveries 取得
│   ├── characters.py              # キャラクター作成
│   └── images.py                  # 画像配信
│
├── ws/                            # WebSocket（ゲーム中の全通信）
│   ├── manager.py                 # 接続管理、broadcast、game.state 送信
│   ├── handler.py                 # メッセージルーティング
│   └── actions.py                 # NEW: 各アクションの処理（handler から呼ばれる）
│
├── jobs/                          # NEW: バックグラウンドジョブ
│   ├── discovery_job.py           # discoveries 一括生成
│   ├── ending_job.py              # エンディング生成
│   └── ai_speech_job.py           # AI 発言生成
│
└── templates/                     # LLM プロンプト
```

---

## サーバー クラス設計

### GameService

フェーズ遷移のコア。全て DB 操作。メモリ状態なし。

```python
class GameService:
    def __init__(self, session_factory):
        self._sf = session_factory

    async def advance_phase(self, game_id: str, force: bool = False) -> AdvanceResult:
        """フェーズを次に進める。DB 排他制御で1回だけ遷移。"""
        async with self._sf() as db:
            game = await phase_repo.get_game_with_phases(db, game_id)
            phase = game.current_phase

            # 期限チェック（force でない場合）
            if not force and phase.deadline_at and utcnow() < phase.deadline_at:
                remaining = (phase.deadline_at - utcnow()).total_seconds()
                return AdvanceResult("not_expired", remaining_sec=int(remaining))

            # 排他制御: ended_at IS NULL のもののみ更新
            updated = await phase_repo.end_phase(db, phase.id)
            if not updated:
                current = await phase_repo.get_current(db, game_id)
                return AdvanceResult("already_advanced", phase=current)

            # 次フェーズ開始
            next_phase = await phase_repo.get_next(db, game, phase)
            if next_phase is None:
                game.status = GameStatus.ended
                await db.commit()
                return AdvanceResult("game_ended")

            next_phase.started_at = utcnow()
            next_phase.deadline_at = utcnow() + timedelta(seconds=next_phase.duration_sec)
            game.current_phase_id = next_phase.id
            await db.commit()

            return AdvanceResult("advanced", phase=next_phase)

    async def get_state(self, game_id: str, player_id: str) -> dict:
        """プレイヤー視点のゲーム状態を構築。"""

    async def select_location(self, game_id: str, player_id: str, phase_id: str, location_id: str):
        """調査場所を選択。DB に保存。"""

    async def auto_assign_locations(self, game_id: str, phase_id: str):
        """未選択プレイヤーにランダム割り当て。advance 内で呼ぶ。"""
```

### AdvanceResult

```python
@dataclass
class AdvanceResult:
    status: str  # "advanced" | "already_advanced" | "not_expired" | "game_ended"
    phase: Phase | None = None
    remaining_sec: int | None = None
```

### SpeechService

発言権管理。全て DB。

```python
class SpeechService:
    def __init__(self, session_factory):
        self._sf = session_factory

    async def request_speech(self, game_id: str, player_id: str) -> tuple[bool, str | None]:
        """発言権を取得。戻り値: (granted, prev_speaker_id)"""
        async with self._sf() as db:
            phase = await phase_repo.get_current(db, game_id)
            prev = phase.current_speaker_id
            if prev == player_id:
                return True, None
            phase.current_speaker_id = player_id
            await db.commit()
            return True, prev

    async def release_speech(self, game_id: str, player_id: str, transcript: str) -> bool:
        """発言終了。SpeechLog に保存。"""
        async with self._sf() as db:
            phase = await phase_repo.get_current(db, game_id)
            if phase.current_speaker_id != player_id:
                return False
            phase.current_speaker_id = None
            if transcript:
                db.add(SpeechLog(...))
            await db.commit()
            return True
```

### DiscoveryService

discoveries 生成。LLM 呼び出し中は DB セッションを保持しない。

```python
class DiscoveryService:
    def __init__(self, session_factory):
        self._sf = session_factory

    async def generate_all(self, game_id: str, phase_id: str):
        """バックグラウンドジョブとして実行。"""

        # 1. DB から情報取得 → セッション閉じる
        async with self._sf() as db:
            context = await self._load_context(db, game_id, phase_id)
            phase = await db.get(Phase, phase_id)
            phase.discoveries_status = "generating"
            await db.commit()

        # 2. LLM 呼び出し（並列、DB 不要）
        results = await asyncio.gather(*[
            self._call_llm(context, player, location)
            for player, location in context.selections
        ])

        # 3. 結果を DB に保存 → セッション閉じる
        async with self._sf() as db:
            for player_id, discoveries in results:
                for d in discoveries:
                    db.add(Evidence(source="discovery", ...))
            phase = await db.get(Phase, phase_id)
            phase.discoveries_status = "ready"
            await db.commit()

        # 4. 全クライアントに game.state 送信
        await ws_manager.broadcast_game_state(game_id)

    async def get_discoveries(self, game_id: str, player_id: str, phase_id: str) -> list[dict]:
        """DB から discoveries を取得。"""
```

### WSManager

接続管理と通知。

```python
class WSManager:
    def __init__(self):
        self._connections: dict[str, dict[str, WebSocket]] = {}

    async def connect(self, room_code: str, player_id: str, ws: WebSocket, game_service: GameService):
        """接続時に game.state を自動送信。"""
        self._connections.setdefault(room_code, {})[player_id] = ws
        state = await game_service.get_state(game_id, player_id)
        await ws.send_json({"type": "game.state", "data": state})

    def disconnect(self, room_code: str, player_id: str):
        conns = self._connections.get(room_code, {})
        conns.pop(player_id, None)

    async def broadcast_game_state(self, game_id: str, game_service: GameService):
        """全プレイヤーに各自の game.state を送信。"""
        for player_id, ws in self._get_connections(game_id):
            state = await game_service.get_state(game_id, player_id)
            await ws.send_json({"type": "game.state", "data": state})

    async def broadcast(self, room_code: str, message: dict, exclude: str | None = None):
        """通知を全員に送信。"""
        for pid, ws in self._connections.get(room_code, {}).items():
            if pid != exclude:
                await ws.send_json(message)

    async def send_to(self, room_code: str, player_id: str, message: dict):
        """特定プレイヤーに送信。"""
        ws = self._connections.get(room_code, {}).get(player_id)
        if ws:
            await ws.send_json(message)
```

### WS Handler

メッセージのルーティングとバリデーション。

```python
async def handle_websocket(websocket: WebSocket, room_code: str, token: str):
    # 認証
    player = await authenticate(token)
    if not player:
        await websocket.close(code=4003)
        return

    game = await get_game_by_room(room_code)
    await ws_manager.connect(room_code, player.id, websocket, game_service)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")
            msg_data = data.get("data", {})

            await dispatch_message(game.id, room_code, player.id, msg_type, msg_data)
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(room_code, player.id)
```

### WS Actions

各アクションの処理。handler から呼ばれる。

```python
async def dispatch_message(game_id, room_code, player_id, msg_type, data):
    match msg_type:
        case "advance":
            result = await game_service.advance_phase(game_id, force=data.get("force", False))
            if result.status == "advanced":
                # investigation なら discoveries 生成をバックグラウンドで開始
                if result.phase.phase_type == PhaseType.investigation:
                    asyncio.create_task(discovery_service.generate_all(game_id, result.phase.id))
                await ws_manager.broadcast_game_state(game_id, game_service)
            elif result.status == "not_expired":
                await ws_manager.send_to(room_code, player_id, {
                    "type": "error",
                    "data": {"code": "not_expired", "remaining_sec": result.remaining_sec}
                })

        case "select_location":
            await game_service.select_location(game_id, player_id, data["location_id"])

        case "keep_evidence":
            await game_service.keep_evidence(game_id, player_id, data["discovery_id"])
            await ws_manager.broadcast_game_state(game_id, game_service)

        case "speech.request":
            granted, prev = await speech_service.request_speech(game_id, player_id)
            if granted:
                await ws_manager.broadcast(room_code, {"type": "speech.active", "data": {"player_id": player_id}})
                await ws_manager.send_to(room_code, player_id, {"type": "speech.granted", "data": {"player_id": player_id}})
                if prev:
                    await ws_manager.broadcast(room_code, {"type": "speech", "data": {"player_id": prev, "character_name": "...", "transcript": ""}})

        case "speech.release":
            released = await speech_service.release_speech(game_id, player_id, data.get("transcript", ""))
            if released:
                await ws_manager.broadcast(room_code, {
                    "type": "speech",
                    "data": {"player_id": player_id, "character_name": "...", "transcript": data.get("transcript", "")}
                })

        case "reveal_evidence":
            await game_service.reveal_evidence(game_id, player_id, data["evidence_id"])
            await ws_manager.broadcast(room_code, {
                "type": "evidence_revealed",
                "data": {"player_id": player_id, ...}
            })

        case "vote":
            result = await game_service.vote(game_id, player_id, data["suspect_player_id"])
            await ws_manager.broadcast(room_code, {"type": "vote_cast", "data": {"voted_count": result.voted, "total_human": result.total}})
            if result.all_voted:
                asyncio.create_task(ending_job.generate(game_id))
                await ws_manager.broadcast_game_state(game_id, game_service)

        case "room_message":
            await ws_manager.send_to_colocated(room_code, player_id, {
                "type": "room_message",
                "data": {"sender_id": player_id, "sender_name": "...", "text": data["text"]}
            })
```

---

## iOS モジュール構成

```
ios/Madaminu/Sources/
├── App/
│   └── MadaminuApp.swift
│
├── Models/
│   ├── GameState.swift             # PhaseInfo, DiscoveryItem, SpeechEntry 等
│   └── Room.swift                  # PlayerInfo, RoomListItem 等
│
├── Network/
│   ├── APIClient.swift             # HTTP（ゲーム外操作、画像取得）
│   ├── WebSocketClient.swift       # WS 接続、再接続、ping/pong
│   └── ImageCache.swift
│
├── Store/
│   ├── AppStore.swift              # メイン Store、WS メッセージ dispatch
│   ├── AppAction.swift             # アクション enum
│   ├── Screen.swift                # 画面遷移 enum
│   ├── PhaseScreenState.swift      # NEW: active / transitioning
│   ├── GamePlayStore.swift         # ゲーム状態
│   ├── RoomStore.swift             # ルーム状態
│   └── NotebookStore.swift         # 手帳状態
│
├── Services/
│   ├── GameStateSync.swift         # NEW: game.state 差分検出、シーン切り替え
│   ├── DeviceIdentifier.swift
│   └── SpeechRecognizer.swift
│
├── Views/
│   ├── HomeView.swift
│   ├── RoomLobbyView.swift
│   ├── CharacterCreationView.swift
│   ├── GeneratingView.swift        # フェーズガイド表示
│   ├── IntroView.swift
│   ├── PhaseTransitionOverlay.swift
│   ├── NotebookView.swift
│   └── phases/                     # NEW: フェーズ別ビュー
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

game.state の差分検出。全シーン切り替えの責務。

```swift
class GameStateSync {

    func apply(serverState: GameState, store: AppStore) {
        let localPhaseId = store.game.currentPhase?.phaseId
        let serverPhaseId = serverState.currentPhase?.id

        if localPhaseId != serverPhaseId {
            // フェーズが変わった
            store.game.applyFullState(serverState)

            if serverState.currentPhase?.discoveriesStatus == "generating" {
                // investigation 準備中 → 遷移画面維持
                store.phaseScreen = .transitioning
            } else {
                // 遷移画面3秒表示
                store.phaseScreen = .transitioning
                DispatchQueue.main.asyncAfter(deadline: .now() + 3) {
                    store.phaseScreen = .active
                    store.startLocalTimer(deadline: serverState.currentPhase?.deadlineAt)
                }
            }
        } else {
            // 同じフェーズ → 差分更新
            applyDiff(serverState, store: store)
        }
    }

    private func applyDiff(_ state: GameState, store: AppStore) {
        // discoveries_status が generating → ready に変わった
        if store.phaseScreen == .transitioning,
           state.currentPhase?.discoveriesStatus == "ready" {
            DispatchQueue.main.asyncAfter(deadline: .now() + 3) {
                store.phaseScreen = .active
                store.startLocalTimer(deadline: state.currentPhase?.deadlineAt)
            }
        }

        // 投票状況更新
        // my_evidences 更新
        // etc.
    }
}
```

### PhaseScreenState

```swift
enum PhaseScreenState {
    case active         // フェーズ画面を表示
    case transitioning  // 遷移画面を表示
}
```

### AppStore（WS メッセージ処理）

```swift
final class AppStore: ObservableObject {
    @Published var phaseScreen: PhaseScreenState = .active

    private let sync = GameStateSync()

    func onWSMessage(type: String, data: [String: Any]) {
        switch type {
        case "game.state":
            let state = parseGameState(data)
            sync.apply(serverState: state, store: self)

        case "speech.granted":
            game.isSpeaking = true
            startRecording()

        case "speech.active":
            game.currentSpeakerId = data["player_id"]

        case "speech":
            game.currentSpeakerId = nil
            game.speechHistory.append(...)

        case "evidence_revealed":
            game.revealedEvidences.insert(..., at: 0)

        case "vote_cast":
            game.votedCount = data["voted_count"]

        case "error":
            handleError(data)

        default:
            break
        }
    }

    // WS でアクション送信
    func sendAdvance(force: Bool = false) {
        phaseScreen = .transitioning
        ws.send(type: "advance", data: force ? ["force": true] : [:])
    }

    func sendKeepEvidence(discoveryId: String) {
        ws.send(type: "keep_evidence", data: ["discovery_id": discoveryId])
    }

    func sendVote(suspectId: String) {
        ws.send(type: "vote", data: ["suspect_player_id": suspectId])
    }

    // etc.
}
```

### WebSocketClient

```swift
final class WebSocketClient: Sendable {
    // 接続、送信、受信、ping/pong、再接続
    // 再接続時: サーバーが game.state を自動送信
    //           → onMessage で GameStateSync.apply が呼ばれる
    //           → ローカル状態が最新に復帰
}
```

---

## 依存関係

### サーバー

```
WS Handler → WS Actions → Service → Repository → DB
                        → Jobs (asyncio.create_task)
                        → WS Manager (通知)

Router → Service → Repository → DB

Jobs → LLM Client
    → Repository → DB
    → WS Manager (完了通知)
```

- WS Handler はメッセージを受けて Actions に振り分ける
- Actions は Service を呼び、結果に応じて WS Manager で通知
- Jobs は Service と同じ層。create_task で起動
- Service と Jobs は Repository 経由でのみ DB にアクセス
- LLM Client は Jobs からのみ呼ばれる（Service からは直接呼ばない）

### iOS

```
View → AppStore → WebSocketClient (送信)
                → APIClient (ゲーム外)

WebSocketClient (受信) → AppStore.onWSMessage → GameStateSync
                                              → Store 更新
                                              → View 再描画
```

- View は AppStore のメソッドを呼ぶ
- AppStore が WS で送信
- WS 受信は AppStore.onWSMessage でハンドリング
- GameStateSync が game.state の差分を検出してシーン切り替え
