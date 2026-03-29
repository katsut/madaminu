# コードベース構造仕様書

## ディレクトリ構成

### サーバー (Python/FastAPI)

```
server/src/madaminu/
├── main.py                    # FastAPI app、ライフサイクル、WS エンドポイント
├── config.py                  # 環境変数設定 (Settings)
├── db/
│   ├── __init__.py            # get_db 依存性注入
│   └── database.py            # engine, async_session 定義
├── models/                    # SQLAlchemy ORM モデル
│   ├── base.py                # Base, TimestampMixin, UUIDPrimaryKeyMixin
│   ├── game.py                # Game, GameStatus
│   ├── player.py              # Player, PlayerRole, ConnectionStatus
│   ├── phase.py               # Phase, PhaseType
│   ├── evidence.py            # Evidence, EvidenceSource
│   ├── speech_log.py          # SpeechLog
│   ├── vote.py                # Vote
│   ├── game_ending.py         # GameEnding
│   ├── note.py                # Note
│   └── payment.py             # Payment, PaymentStatus
├── routers/                   # HTTP API エンドポイント
│   ├── rooms.py               # ルーム CRUD、参加、準備、削除
│   ├── game.py                # ゲーム開始、状態取得、デバッグ
│   ├── characters.py          # キャラクター作成
│   ├── images.py              # 画像配信 (scene, portrait, map)
│   └── schemas.py             # Pydantic リクエスト/レスポンス型
├── schemas/
│   └── game.py                # build_game_state (WS用ゲーム状態構築)
├── repositories/              # DB クエリ抽象化
│   ├── game_repository.py
│   ├── phase_repository.py
│   └── player_repository.py
├── services/                  # ビジネスロジック
│   ├── scenario_engine.py     # LLM シナリオ生成・調査・改ざん・エンディング
│   ├── phase_manager.py       # フェーズ遷移・タイマー・発見管理・エンディング
│   ├── speech_manager.py      # 発言権管理 (割り込み制)
│   ├── room_manager.py        # ルーム作成・参加・再参加
│   ├── ai_player.py           # AIプレイヤー動的生成・AI発言
│   ├── map_builder.py         # マップグラフ自動構築・ルートテキスト生成
│   ├── map_renderer.py        # SVG マップレンダリング
│   ├── map_validator.py       # マップ構造バリデーション
│   ├── image_generator.py     # OpenAI 画像生成
│   └── errors.py              # カスタム例外 (InvalidTransition)
├── templates/                 # LLM プロンプトテンプレート (.txt)
│   ├── scenario_generate.txt  # シナリオ全体生成
│   ├── scenario_system.txt    # システムプロンプト
│   ├── investigation.txt      # 調査結果生成
│   ├── tamper_evidence.txt    # 証拠改ざん
│   ├── phase_adjustment.txt   # フェーズ調整 (追加証拠)
│   └── ending_generation.txt  # エンディング生成
├── llm/
│   ├── client.py              # LLMClient (OpenAI wrapper)
│   └── prompts.py             # テンプレートローダー
├── events/
│   ├── bus.py                 # EventBus
│   └── types.py               # ScenarioReady, ImagesReady
└── ws/
    ├── handler.py             # WS メッセージルーティング
    └── messages.py            # WSMessage, Pydantic データ型
```

### iOS (Swift/SwiftUI)

```
ios/Madaminu/Sources/
├── App/
│   └── MadaminuApp.swift          # @main エントリーポイント
├── Models/
│   ├── GameState.swift            # PhaseInfo, EndingData, DiscoveryItem 等
│   └── Room.swift                 # CreateRoomResponse, PlayerInfo, RoomListItem 等
├── Network/
│   ├── APIClient.swift            # HTTP API クライアント
│   ├── WebSocketClient.swift      # WS 接続・再接続・メッセージ受信
│   ├── WSMessageAdapter.swift     # WS メッセージ → Store 状態変換
│   └── ImageCache.swift           # 非同期画像キャッシュ
├── Services/
│   ├── DeviceIdentifier.swift     # デバイスID管理
│   └── SpeechRecognizer.swift     # 音声認識 (Speech Framework)
├── Store/
│   ├── AppStore.swift             # メインStore (dispatch, performXxx)
│   ├── AppAction.swift            # アクション enum
│   ├── Screen.swift               # 画面遷移 enum
│   ├── ErrorLevel.swift           # エラーレベル enum
│   ├── RoomStore.swift            # ルーム状態
│   ├── GamePlayStore.swift        # ゲームプレイ状態
│   └── NotebookStore.swift        # 手帳状態 (証拠, 議論記録)
├── Views/
│   ├── HomeView.swift             # ホーム画面、ルーム一覧、作成/参加シート
│   ├── RoomLobbyView.swift        # ロビー画面
│   ├── CharacterCreationView.swift # キャラクター作成
│   ├── IntroView.swift            # イントロ (9ページ)
│   ├── GamePlayView.swift         # メインゲーム画面 (全フェーズ, エンディング)
│   ├── NotebookView.swift         # 手帳 (6タブ)
│   └── TranscriptEditView.swift   # 文字起こし編集
└── DesignSystem/
    ├── ColorTokens.swift          # カラーパレット
    ├── SpacingTokens.swift        # スペーシング定数
    ├── TypographyTokens.swift     # フォントスタイル
    ├── MDButton.swift             # ボタンコンポーネント
    ├── MDCard.swift               # カードコンポーネント
    ├── MDTextField.swift          # テキストフィールド
    ├── MDTextEditor.swift         # テキストエディタ
    ├── MDLoadingView.swift        # ローディング表示
    └── MDModal.swift              # モーダル
```

## サーバー データモデル

### Game

```python
class GameStatus(StrEnum):
    waiting, generating, playing, voting, ended

class Game(Base):
    id: str (UUID)
    room_code: str (6文字, unique)
    room_name: str | None
    host_player_id: str | None → Player.id
    status: GameStatus
    current_phase_id: str | None → Phase.id
    password: str | None
    scenario_skeleton: dict | None (JSON)  # シナリオ全体、map、route_text 含む
    gm_internal_state: dict | None (JSON)  # GM戦略、プレイヤーノート
    scene_image: str | None (base64)
    victim_image: str | None (base64)
    total_llm_cost_usd: float
    turn_count: int (default=3)
    # relationships
    players: list[Player]
    phases: list[Phase]
    speech_logs: list[SpeechLog]
```

### Player

```python
class PlayerRole(StrEnum):
    criminal, witness, related, innocent

class ConnectionStatus(StrEnum):
    online, offline

class Player(Base):
    id: str (UUID)
    game_id: str → Game.id
    device_id: str | None      # 再参加用デバイス識別子
    session_token: str (UUID)  # 認証トークン
    display_name: str
    character_name: str | None
    character_name_kana: str | None
    character_gender: str | None
    character_age: str | None
    character_occupation: str | None
    character_appearance: str | None
    character_personality: str | None
    character_background: str | None
    role: PlayerRole | None
    secret_info: str | None
    objective: str | None
    public_info: str | None
    is_host: bool
    is_ai: bool (default=False)
    is_ready: bool (default=False)
    portrait_image: str | None (base64)
    connection_status: ConnectionStatus
```

### Phase

```python
class PhaseType(StrEnum):
    initial, opening, planning, investigation, discussion, voting

class Phase(Base):
    id: str (UUID)
    game_id: str → Game.id
    phase_type: PhaseType
    phase_order: int
    duration_sec: int
    started_at: datetime | None
    deadline_at: datetime | None
    ended_at: datetime | None
    investigation_locations: list[dict] | None (JSON)
```

### Evidence

```python
class EvidenceSource(StrEnum):
    gm_push, investigation

class Evidence(Base):
    id: str (UUID)
    game_id: str → Game.id
    player_id: str → Player.id
    phase_id: str → Phase.id
    title: str
    content: str
    source: EvidenceSource
    revealed_at: datetime
```

### SpeechLog

```python
class SpeechLog(Base):
    id: str (UUID)
    game_id: str → Game.id
    player_id: str → Player.id
    phase_id: str → Phase.id
    transcript: str
```

### Vote

```python
class Vote(Base):
    id: str (UUID)
    game_id: str → Game.id
    voter_player_id: str → Player.id
    suspect_player_id: str → Player.id
```

### GameEnding

```python
class GameEnding(Base):
    id: str (UUID)
    game_id: str → Game.id (unique)
    ending_text: str
    true_criminal_id: str → Player.id
    objective_results: dict | None (JSON)
```

## iOS データ型

### ゲーム状態

```swift
struct PhaseInfo: Codable, Sendable
    phaseId, phaseType, phaseOrder, totalPhases, durationSec,
    turnNumber, totalTurns, remainingSec,
    investigationLocations: [InvestigationLocation]?

struct InvestigationLocation: Codable, Identifiable, Sendable
    id, name, description, features: [String]

struct EvidenceItem: Codable, Identifiable, Sendable
    id (UUID), evidenceId: String?, title, content

struct EndingData: Codable, Sendable
    endingText, trueCriminalId,
    objectiveResults: [String: ObjectiveResult]?,
    voteDetails: [VoteDetail]?,
    voteCounts: [String: Int]?,
    arrestedName: String?,
    rankings: [PlayerRanking]?,
    characterReveals: [CharacterReveal]?

struct DiscoveryItem: Identifiable, Sendable
    id, title, content, canTamper, isTampered

struct SpeechEntry: Identifiable, Sendable
    id (UUID), playerId: String?, characterName, transcript

struct RevealedEvidence: Identifiable, Sendable
    id (UUID), playerId: String?, playerName, title, content

struct ColocatedPlayer: Identifiable, Sendable
    id, characterName, portraitUrl: String?

struct RoomMessage: Identifiable, Sendable
    id (UUID), senderId, senderName, text
```

### ルーム

```swift
struct PlayerInfo: Codable, Identifiable, Sendable
    id, displayName, characterName?, characterGender?, characterAge?,
    characterOccupation?, characterPersonality?, characterBackground?,
    characterAppearance?, isHost, isReady, connectionStatus,
    publicInfo?, portraitUrl?

struct RoomListItem: Codable, Identifiable, Sendable
    roomCode, roomName?, status, playerCount, hostName?, hasPassword

struct MyRoomItem: Codable, Identifiable, Sendable
    roomCode, status, isHost, displayName, characterName?,
    sessionToken, playerId, createdAt?
```

### Store

```swift
final class AppStore: ObservableObject
    room: RoomStore, game: GamePlayStore, notebook: NotebookStore,
    screen: Screen, ws: WebSocketClient, api: APIClient,
    isLoading, errorMessage, isHost

final class RoomStore: ObservableObject
    roomCode, displayName, playerId, sessionToken, isHost,
    players: [PlayerInfo], availableRooms, myRooms, turnCount

final class GamePlayStore: ObservableObject
    scenarioSetting, mySecretInfo, myObjective, myRole,
    currentPhase, currentSpeakerId, ending, isSpeaking,
    showPhaseTransition, nextPhaseType, travelNarrative,
    isPaused, localRemainingSec, selectedLocationId,
    discoveries, keptDiscoveryId, revealedEvidences,
    speechHistory, colocatedPlayers, roomMessages,
    introReady, introReadyCount,
    aiPlayersReady, scenarioReady, sceneImageReady, portraitsReady, allReady

final class NotebookStore: ObservableObject
    evidences: [EvidenceItem], discussionLogs: [DiscussionLogEntry], notes

enum Screen: home, characterCreation, lobby, generating, intro, playing, ended

enum AppAction
    createRoom, joinRoom, leaveRoom, startGame,
    requestSpeech, releaseSpeech, investigate, selectInvestigation,
    keepEvidence, tamperEvidence, revealEvidence, vote,
    advancePhase, extendPhase, pausePhase, resumePhase, ...
```

## HTTP API エンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/v1/rooms` | ルーム一覧（待機中） |
| POST | `/api/v1/rooms` | ルーム作成 |
| POST | `/api/v1/rooms/{code}/join` | ルーム参加（device_id再参加対応） |
| GET | `/api/v1/rooms/{code}` | ルーム詳細 |
| POST | `/api/v1/rooms/{code}/ready` | 準備完了トグル |
| GET | `/api/v1/rooms/mine/list` | 自分のルーム一覧 |
| DELETE | `/api/v1/rooms/{code}` | ルーム削除（ホストのみ） |
| POST | `/api/v1/rooms/{code}/characters` | キャラクター作成 |
| POST | `/api/v1/rooms/{code}/start` | ゲーム開始 |
| GET | `/api/v1/rooms/{code}/state` | ゲーム状態取得 |
| GET | `/api/v1/rooms/{code}/debug` | デバッグ情報（ホストのみ） |
| GET | `/api/v1/images/player/{id}` | プレイヤーポートレート画像 |
| GET | `/api/v1/images/game/{code}/scene` | シーン画像 |
| GET | `/api/v1/images/game/{code}/victim` | 被害者画像 |
| GET | `/api/v1/images/game/{code}/map` | SVGマップ（?highlight=room_id） |
| GET | `/health` | ヘルスチェック |

## サービスクラス

### PhaseManager

```
状態管理（メモリ内）:
  _timers: {game_id: asyncio.Task}
  _investigation_selections: {room_code: {player_id: {location_id, feature}}}
  _discoveries: {room_code: {player_id: [discovery_dict]}}
  _intro_ready: {room_code: set[player_id]}
  _paused: {game_id: remaining_sec}

主要メソッド:
  start_first_phase(game_id, room_code) → Phase
  advance_phase(game_id, room_code) → Phase | None
  extend_phase(game_id, room_code) → Phase
  pause_phase / resume_phase
  set_investigation_selection / get_investigation_selections
  add_discovery / get_discoveries / replace_discovery
```

### SpeechManager

```
状態管理（メモリ内）:
  _locks: {room_code: asyncio.Lock}
  _speakers: {room_code: player_id | None}

主要メソッド:
  request_speech(room_code, player_id) → bool  # 割り込み制
  release_speech(room_code, player_id, transcript) → bool
  get_current_speaker(room_code) → str | None
```

### MapBuilder

```
build_map_structure(llm_map, victim?) → complete_map
  - 部屋リストからbackbone (entrance→corridor→stairs) を自動構築
  - 接続グラフを生成
  - 犯行現場を victim.crime_scene_room_id からマーク

generate_route_text(map_data, players?) → str
  - マップ構造を自然言語に変換（LLMコンテキスト用）

generate_travel_narrative(map_data, selections, id_to_name) → {player_id: text}
  - BFS で移動経路を算出、ナラティブテキスト生成
```

## テストファイル

```
server/tests/
├── test_characters.py         # キャラクター作成 API
├── test_e2e.py                # E2E (HTTP + WS)
├── test_health.py             # ヘルスチェック
├── test_investigation.py      # 調査ロジック
├── test_llm.py                # LLM テンプレート
├── test_map_builder.py        # マップグラフ構築
├── test_map_renderer.py       # SVGレンダリング
├── test_map_validation.py     # マップバリデーション
├── test_phase_manager.py      # フェーズ遷移
├── test_rejoin.py             # device_id 再参加
├── test_room_name.py          # ルーム名
├── test_rooms.py              # ルーム CRUD
├── test_scenario.py           # シナリオ生成・ゲーム開始
├── test_speech_manager.py     # 発言権管理
├── test_speech_preempt.py     # 発言割り込み
├── test_timer_resilience.py   # タイマー耐障害性
├── test_voting_ending.py      # 投票・エンディング
└── test_websocket.py          # WS 接続・メッセージ
```
