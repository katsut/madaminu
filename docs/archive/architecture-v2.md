# マダミヌ アーキテクチャ v2

## 概要

対面プレイ用マーダーミステリー iOS アプリ。サーバーがゲームロジックの権威、iOS はステートストア + ビュー層。

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| サーバー | Python 3.13 / FastAPI / SQLAlchemy (async) |
| DB | PostgreSQL (Railway) |
| リアルタイム | WebSocket (FastAPI native) |
| LLM | OpenAI gpt-5.4-mini / gpt-5.4-nano |
| 画像生成 | OpenAI gpt-image-1 |
| iOS | Swift 6 / SwiftUI / ObservableObject |
| CI | GitHub Actions |
| デプロイ | Railway (Docker) |

## サーバーアーキテクチャ

```
Router（薄い: バリデーション + Service呼び出し）
  → Service（ビジネスロジック）
    → Repository（データアクセス: SQLAlchemy）
    → EventBus（非同期イベント配信）
  → WebSocket Handler（リアルタイム配信）
```

### ディレクトリ構成

```
server/src/madaminu/
├── main.py              # FastAPI app, lifespan
├── config.py            # 環境変数設定
├── db/                  # DB接続
├── models/              # SQLAlchemy ORM
├── schemas/             # Pydantic I/O型 + 共有ロジック
├── repositories/        # データアクセス層
├── routers/             # HTTP エンドポイント
├── ws/                  # WebSocket 接続管理
├── services/            # ビジネスロジック
├── events/              # EventBus + イベント型
├── llm/                 # LLM クライアント + プロンプト
└── templates/           # LLM プロンプトテンプレート

server/alembic/          # DB マイグレーション
```

### デザインパターン

| パターン | 適用箇所 |
|---------|---------|
| Repository | GameRepository, PlayerRepository, PhaseRepository |
| EventBus | GameStarted, ScenarioReady, ImagesReady, PhaseAdvanced |
| State Machine | GameStatus: waiting → generating → playing → voting → ended |
| Background Task | シナリオ生成, 画像生成 (asyncio.create_task) |
| DI (Depends) | FastAPI の依存性注入で Repository/Service を注入 |

### DB マイグレーション

- **Alembic** で管理
- Dockerfile: `alembic upgrade head` → `uvicorn` の順で起動
- 新カラム追加時: `uv run alembic revision --autogenerate -m "add xxx"`

### WebSocket メッセージ

| メッセージ | 方向 | 内容 |
|-----------|------|------|
| game.state | S→C | 全ゲーム状態（接続時 + シナリオ完了時） |
| game.generating | S→C | シナリオ生成開始 |
| game.ready | S→C | 全準備完了 |
| progress | S→C | 準備ステップ完了通知 |
| images.ready | S→C | 画像生成完了 |
| phase.started | S→C | フェーズ開始 |
| phase.timer | S→C | タイマー更新 |
| phase.ended | S→C | フェーズ終了 |
| speech.granted/denied | S→C | 発言権 |
| speech.active/released | S→C | 発言状態 |
| speech.ai | S→C | AI発言 |
| investigate.result/denied | S→C | 調査結果 |
| evidence.received | S→C | 証拠配布 |
| vote.results | S→C | 投票結果 |
| game.ending | S→C | エンディング |
| error | S→C | エラー |
| speech.request/release | C→S | 発言要求/解放 |
| investigate | C→S | 調査リクエスト |
| vote.submit | C→S | 投票 |
| phase.advance/extend | C→S | ホスト操作 |

## iOS アーキテクチャ

```
User Action → AppStore.dispatch(.action) → API/WebSocket → Server
Server → WebSocket → WSMessageAdapter → AppStore → SwiftUI
```

### ディレクトリ構成

```
ios/Madaminu/Sources/
├── App/                 # エントリポイント
├── Models/              # データ型 (Codable, Sendable)
├── Store/               # 状態管理
│   ├── AppStore.swift   # 中央ステートストア
│   ├── RoomStore.swift  # ルーム状態
│   ├── GamePlayStore.swift # ゲーム進行状態
│   ├── NotebookStore.swift # 手帳状態
│   ├── AppAction.swift  # アクション enum
│   ├── Screen.swift     # 画面遷移 enum
│   └── ErrorLevel.swift # エラーレベル
├── Network/             # 通信層
│   ├── APIClient.swift  # REST API
│   ├── WebSocketClient.swift # WebSocket
│   └── WSMessageAdapter.swift # メッセージ→状態変換
├── Services/            # デバイス機能
│   └── SpeechRecognizer.swift
├── Views/               # UI (画面単位)
│   ├── HomeView.swift
│   ├── RoomLobbyView.swift
│   ├── CharacterCreationView.swift
│   ├── IntroView.swift
│   ├── GamePlayView.swift
│   ├── NotebookView.swift
│   └── TranscriptEditView.swift
└── DesignSystem/        # 共通UIコンポーネント
```

### デザインパターン

| パターン | 適用箇所 |
|---------|---------|
| Unidirectional Data Flow | Action → Store → View |
| Command | AppAction enum + dispatch() |
| State Machine | Screen enum: home → lobby → generating → intro → playing → ended |
| Observer | ObservableObject + @Published |
| Adapter | WSMessageAdapter (WS → Store変換) |
| Error Level | transient(5s) / recoverable / fatal(→lobby) |

### 重要な制約

- `ObservableObject` を使う（`@Observable` は使わない — Main Thread Checker 問題）
- クラスに `@MainActor` をつけない（SwiftUI observation と競合）
- async メソッドには `@MainActor` をつける
- WebSocket コールバックは `DispatchQueue.main.async` で保護
- `@unchecked Sendable` で isolation boundary を越える

## ゲームフロー

```
ホーム → ルーム作成/参加 → ロビー → キャラ作成
→ ゲーム開始 → [準備画面: チェックリスト]
  ✅ AIプレイヤー補充
  ✅ シナリオ生成
  ✅ 画像生成
  ✅ 準備完了
→ イントロ (物語/登場人物/秘密)
→ 調査フェーズ → 議論フェーズ → 投票フェーズ
→ エンディング
```
