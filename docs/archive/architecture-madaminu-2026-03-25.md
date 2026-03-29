# System Architecture: マダミヌ

**Date:** 2026-03-25
**Architect:** katsut
**Version:** 1.0
**Project Type:** mobile-app
**Project Level:** 2
**Status:** Draft

---

## Document Overview

This document defines the system architecture for マダミヌ. It provides the technical blueprint for implementation, addressing all functional and non-functional requirements from the PRD.

**Related Documents:**
- Product Requirements Document: docs/prd-madaminu-2026-03-24.md
- Product Brief: docs/product-brief-madaminu-2026-03-24.md

---

## Executive Summary

マダミヌは、iOS クライアント + Python/FastAPI バックエンド + LLM API の3層構成。WebSocket によるリアルタイム同期、LLM（GM）によるシナリオ動的制御、プレイヤーごとの秘密情報隔離を実現する。個人開発のシンプルさを維持しつつ、将来のスケールに備えたモジュラーモノリス構成を採用する。

---

## Architectural Drivers

設計に大きく影響する要件:

1. **NFR-004: LLM APIコスト ≤ $1.5/ゲーム** → プロンプト最適化、モデル使い分け、テンプレート活用
2. **NFR-006: 秘密情報の隔離** → サーバーサイドでplayer_idベースのフィルタリング。クライアントに他者情報を送らない
3. **NFR-001: LLM応答 ≤ 10秒** → ストリーミング応答、事前生成、バックグラウンド処理
4. **NFR-005: ゲーム中断耐性** → サーバーサイドでゲーム状態永続化、WebSocket再接続対応
5. **NFR-002: WebSocket同期 ≤ 500ms** → 軽量JSONメッセージ、インメモリ状態管理

---

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────┐
│                   iOS Client                     │
│              (Swift + SwiftUI)                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │キャラ作成 │ │個人手帳UI│ │発言権制マイク入力│  │
│  └──────────┘ └──────────┘ └──────────────────┘ │
└──────────┬──────────────────────┬────────────────┘
           │ REST API (HTTPS)     │ WebSocket (WSS)
           ▼                      ▼
┌─────────────────────────────────────────────────┐
│          Backend Server (Python/FastAPI)          │
│  ┌───────────┐ ┌───────────┐ ┌───────────────┐  │
│  │ Room/Game  │ │ Scenario  │ │  Speech       │  │
│  │ Manager    │ │ Engine    │ │  Processor    │  │
│  └─────┬─────┘ └─────┬─────┘ └───────┬───────┘  │
│        │              │               │           │
│  ┌─────┴──────────────┴───────────────┴───────┐  │
│  │           Game State Store                  │  │
│  └─────────────────┬───────────────────────────┘  │
└────────────────────┼─────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   ┌─────────┐ ┌──────────┐ ┌──────────┐
   │ SQLite  │ │ LLM API  │ │ Apple    │
   │   DB    │ │(Claude)  │ │ Speech   │
   └─────────┘ └──────────┘ └──────────┘
                              (iOS側処理)
```

### Architectural Pattern

**Pattern:** モジュラーモノリス

**Rationale:** 個人開発・Level 2プロジェクトに最適。単一デプロイでシンプルな運用。モジュール境界で関心を分離し、将来のサービス分割にも備える。Python/FastAPIの非同期サポートによりWebSocket・LLM API呼び出しを効率的に処理。

---

## Technology Stack

### Frontend (iOS)

**Choice:** Swift + SwiftUI

**Rationale:** iOS専用アプリの要件。SwiftUIでモダンな宣言的UI。iOS 17+ターゲットで最新APIを活用。

**主要ライブラリ:**
- SwiftUI: UI構築
- URLSession + WebSocket: サーバー通信
- Speech Framework: 音声認識（端末側処理）
- StoreKit 2: In-App Purchase

### Backend

**Choice:** Python + FastAPI

**Rationale:** 高速な開発サイクル。非同期WebSocketのネイティブサポート。LLM API（Anthropic SDK）との親和性が高い。型ヒント + PydanticでAPIスキーマの自動バリデーション。

**主要ライブラリ:**
- FastAPI: Web framework + WebSocket
- uvicorn: ASGI server
- anthropic: Claude API SDK
- pydantic: データバリデーション
- aiosqlite: 非同期SQLiteアクセス
- SQLAlchemy: ORM（async対応）

### Database

**Choice:** SQLite (aiosqlite)

**Rationale:** 個人開発の初期フェーズで十分。デプロイがシンプル（ファイルベース）。ゲーム状態の永続化に軽量・高速。将来PostgreSQLへの移行はSQLAlchemyのORM層で吸収可能。

### Infrastructure

**Choice:** Railway

**Rationale:** 個人開発で手軽にデプロイ。GitHub連携で自動デプロイ。Pythonアプリを直接実行可能。スケール時はAWSへ移行。

### Third-Party Services

| サービス | 用途 | 選定理由 |
|---|---|---|
| Claude API (Anthropic) | シナリオ生成・動的調整・エンディング生成 | 物語生成品質。モデル使い分けでコスト最適化 |
| Apple Speech Framework | 音声認識 | iOS標準。追加コストなし。端末側処理で低レイテンシ |
| App Store (StoreKit 2) | In-App Purchase | iOS課金の必須要件 |

### Development & Deployment

| カテゴリ | 選定 |
|---|---|
| VCS | Git + GitHub |
| CI/CD | GitHub Actions |
| パッケージ管理 (Python) | uv |
| パッケージ管理 (iOS) | Swift Package Manager |
| テスト (Python) | pytest + pytest-asyncio |
| テスト (iOS) | XCTest |
| リンター | ruff |
| フォーマッター | ruff format |

---

## System Components

### Component 1: Room Manager

**Purpose:** ルーム・ゲームセッションのライフサイクル管理とWebSocket接続管理

**Responsibilities:**
- ルーム作成・参加コード発行・プレイヤー管理
- WebSocket接続管理・再接続処理
- ゲーム状態の同期ブロードキャスト（プレイヤーごとにフィルタリング）
- フェーズ進行管理（タイマー・遷移）
- 発言権の排他制御

**Interfaces:**
- REST API: ルーム作成・参加
- WebSocket: ゲーム中のリアルタイム通信

**FRs Addressed:** FR-002, FR-003, FR-006

### Component 2: Character Service

**Purpose:** キャラクター作成・管理

**Responsibilities:**
- キャラクター情報のバリデーション・保存
- 公開情報と秘密情報の分離管理

**Interfaces:**
- REST API: キャラクター作成・取得

**FRs Addressed:** FR-001

### Component 3: Scenario Engine

**Purpose:** LLM（GM）によるシナリオ生成・動的制御の中核

**Responsibilities:**
- テンプレート選択・LLM呼び出しによるシナリオ骨格生成
- 秘密情報・個人目的（Objective）の意図的設計
- 各秘密に紐づく内部展開シナリオの保持
- フェーズごとの動的調整（発言ログ分析→展開生成）
- 調査リクエストへのGM判断による結果生成
- GM主導の情報配布（停滞打破・クライマックス誘導）
- エンディング生成（投票結果＋行動履歴）
- バリデーションレイヤー（論理矛盾チェック）

**Interfaces:**
- 内部呼び出し（Room Managerから）

**Dependencies:**
- Claude API (anthropic SDK)
- テンプレートデータ

**FRs Addressed:** FR-004, FR-008, FR-009, FR-014, FR-015

### Component 4: Speech Processor

**Purpose:** 発言ログの管理

**Responsibilities:**
- 音声認識結果（transcript）の受信・保存
- 発言ログの話者付き時系列管理
- transcript修正の反映

**Interfaces:**
- WebSocket: transcript受信・修正

**FRs Addressed:** FR-007, FR-011

### Component 5: Notebook Service

**Purpose:** プレイヤーごとの個人手帳データ管理

**Responsibilities:**
- 秘密情報・個人目的の配信
- 証拠カードの管理・配信
- メモの保存
- **プレイヤーIDに基づくアクセス制御**（NFR-006の核心）

**Interfaces:**
- WebSocket: 手帳データ配信・メモ更新

**FRs Addressed:** FR-005

### Component 6: Payment Service

**Purpose:** IAP課金処理

**Responsibilities:**
- StoreKit 2のレシート検証（App Store Server API）
- 課金状態管理

**Interfaces:**
- REST API: レシート検証

**FRs Addressed:** FR-010

---

## Data Architecture

### Data Model

```
Game
├── id: UUID (PK)
├── room_code: str (UNIQUE, 6文字)
├── host_player_id: UUID (FK → Player)
├── status: enum (waiting, generating, playing, voting, ended)
├── current_phase_id: UUID (FK → Phase, nullable)
├── template_id: str
├── scenario_skeleton: JSON  # LLM生成のシナリオ骨格
├── gm_internal_state: JSON  # GM用内部制御情報（展開シナリオ等）
├── created_at: datetime
└── updated_at: datetime

Player
├── id: UUID (PK)
├── game_id: UUID (FK → Game)
├── session_token: str
├── display_name: str
├── character_name: str
├── character_personality: text
├── character_background: text
├── secret_info: text         # 秘密情報（本人のみ閲覧可）
├── objective: text           # 個人目的
├── role: enum (criminal, witness, related, innocent)
├── is_host: bool
├── connection_status: enum (online, offline)
└── created_at: datetime

Phase
├── id: UUID (PK)
├── game_id: UUID (FK → Game)
├── phase_type: enum (investigation, discussion, voting)
├── phase_order: int
├── duration_sec: int
├── scenario_update: JSON     # このフェーズでのGM調整内容
├── investigation_locations: JSON  # 調査可能な場所/対象リスト
├── started_at: datetime
└── ended_at: datetime (nullable)

SpeechLog
├── id: UUID (PK)
├── game_id: UUID (FK → Game)
├── player_id: UUID (FK → Player)
├── phase_id: UUID (FK → Phase)
├── transcript: text
├── corrected_transcript: text (nullable)
└── created_at: datetime

Evidence
├── id: UUID (PK)
├── game_id: UUID (FK → Game)
├── player_id: UUID (FK → Player)
├── phase_id: UUID (FK → Phase)
├── title: str
├── content: text
├── source: enum (investigation, gm_push)  # 能動的探索 or GM配布
└── revealed_at: datetime

Note
├── id: UUID (PK)
├── player_id: UUID (FK → Player)
├── game_id: UUID (FK → Game)
├── content: text
└── updated_at: datetime

Vote
├── id: UUID (PK)
├── game_id: UUID (FK → Game)
├── voter_player_id: UUID (FK → Player)
├── suspect_player_id: UUID (FK → Player)
└── created_at: datetime

GameEnding
├── id: UUID (PK)
├── game_id: UUID (FK → Game)
├── ending_text: text
├── true_criminal_id: UUID (FK → Player)
├── objective_results: JSON  # 各プレイヤーの目的達成状況
└── created_at: datetime

Payment
├── id: UUID (PK)
├── game_id: UUID (FK → Game)
├── player_id: UUID (FK → Player)
├── receipt_data: text
├── status: enum (pending, verified, failed)
└── verified_at: datetime (nullable)
```

### Database Design

- SQLite単一ファイル（`madaminu.db`）
- SQLAlchemy AsyncSession + aiosqlite
- インデックス: `Game.room_code`, `Player.game_id`, `Player.session_token`, `SpeechLog.game_id+phase_id`, `Evidence.player_id+game_id`
- `gm_internal_state` は他プレイヤーに絶対に露出しないカラム（API/WebSocketレスポンスに含めない）

### Data Flow

```
[シナリオ生成]
キャラ作成完了
  → Scenario Engine
  → Claude API (テンプレート + キャラ情報)
  → シナリオ骨格 + 秘密情報 + 個人目的 + GM内部状態を生成
  → Game/Player/Phase/Evidence に保存
  → プレイヤーごとに自分の情報のみWebSocket配信

[能動的探索（調査フェーズ）]
プレイヤーが場所/対象を選択
  → WebSocket → Room Manager → Scenario Engine
  → Claude API (GM内部状態 + 発言ログ + 選択した場所)
  → 調査結果を生成 → Evidence保存
  → 該当プレイヤーの手帳にWebSocket配信

[GM主導配布]
フェーズ中/フェーズ遷移時
  → Scenario Engine が発言ログ + GM内部状態を分析
  → 「今出すべき情報」を判断
  → Evidence保存 → 該当プレイヤーにWebSocket配信

[フェーズ遷移]
タイマー終了/ホスト操作
  → Room Manager → Scenario Engine
  → Claude API (発言ログ + 現在シナリオ + GM内部状態)
  → 動的調整結果 → Phase/Evidence更新
  → 次フェーズ開始を全員に通知

[エンディング]
全員投票完了
  → Vote集計 → Scenario Engine
  → Claude API (投票結果 + 全行動履歴 + GM内部状態)
  → エンディング + 目的達成状況を生成
  → GameEnding保存 → 全員に同時配信
```

---

## API Design

### API Architecture

- **REST API (HTTPS):** ゲーム準備系（ルーム・キャラ・課金）
- **WebSocket (WSS):** ゲームプレイ中のリアルタイム通信すべて
- **データ形式:** JSON
- **認証:** セッショントークン（ルーム参加時に発行）

### REST Endpoints

```
POST   /api/v1/rooms                    ルーム作成 → {room_code, player_id, session_token}
POST   /api/v1/rooms/:code/join         ルーム参加 → {player_id, session_token}
GET    /api/v1/rooms/:code              ルーム情報（プレイヤー一覧・ステータス）
POST   /api/v1/rooms/:code/characters   キャラクター作成・更新
POST   /api/v1/rooms/:code/start        ゲーム開始（ホストのみ）
POST   /api/v1/payments/verify          レシート検証
GET    /api/v1/games/:id/history        プレイ履歴詳細
GET    /api/v1/history                  過去ゲーム一覧
```

### WebSocket Protocol

**接続:** `wss://{host}/ws/{room_code}?token={session_token}`

**Server → Client:**

| type | 内容 | 送信先 |
|---|---|---|
| `game.started` | シナリオ概要 + 自分の秘密情報 + 個人目的 | 個別 |
| `phase.changed` | フェーズ遷移 + タイマー + 調査場所リスト | 全員（調査場所は個別差異あり） |
| `phase.update` | GM動的調整結果 + 新証拠 | 個別 |
| `investigation.result` | 調査結果（証拠カード） | 個別（調査者のみ） |
| `evidence.push` | GM主導配布の証拠/情報 | 個別 |
| `speech.started` | 発言者ID | 全員 |
| `speech.ended` | 発言者ID + transcript | 全員 |
| `speech.denied` | 発言権取得失敗（他者が発言中） | 個別 |
| `player.connected` | プレイヤー接続 | 全員 |
| `player.disconnected` | プレイヤー切断 | 全員 |
| `vote.result` | 投票結果 | 全員 |
| `game.ending` | エンディング + 真相 + 目的達成状況 | 全員 |
| `error` | エラー | 個別 |

**Client → Server:**

| type | 内容 |
|---|---|
| `speech.request` | 発言権リクエスト |
| `speech.release` | 発言権解放 + transcript |
| `speech.correct` | transcript修正 |
| `investigate` | 調査リクエスト（場所/対象ID） |
| `note.update` | メモ更新 |
| `vote.submit` | 投票（suspect_player_id） |
| `phase.extend` | フェーズ延長（ホストのみ） |
| `phase.advance` | フェーズ強制進行（ホストのみ） |

### Authentication & Authorization

- **認証方式:** セッショントークン（ルーム作成/参加時に発行、UUIDv4）
- **WebSocket認証:** 接続時のクエリパラメータでトークン検証
- **ホスト権限:** サーバーサイドで `player.is_host` を検証（フェーズ操作・ゲーム開始）
- **秘密情報隔離:** 全メッセージ送信時に `player_id` ベースでペイロードをフィルタ
- **アカウント不要:** 対面プレイ前提のため匿名セッションで十分

---

## Non-Functional Requirements Coverage

### NFR-001: LLM応答速度

**Requirement:** シナリオ生成≤30秒、動的調整≤10秒、エンディング≤15秒

**Solution:**
- Claude APIのストリーミングレスポンスを活用し、UIに段階的に表示
- フェーズ間にバックグラウンドで次フェーズの準備を事前生成
- テンプレートで骨格を制約しLLMの生成量を最小化
- 待機中はローディング演出（「GMがシナリオを準備中...」）

**Validation:** 各LLM呼び出しのレイテンシをログに記録。p95で目標値以内を確認。

### NFR-002: WebSocket同期遅延

**Requirement:** ゲーム状態同期の遅延が500ms以内

**Solution:**
- FastAPIのWebSocketネイティブサポートで直接通信
- メッセージは軽量JSON（最小限のフィールドのみ）
- アクティブゲーム状態をインメモリ（Pythonオブジェクト）で保持

**Validation:** WebSocketメッセージのラウンドトリップタイムを計測。

### NFR-003: 音声認識レイテンシ

**Requirement:** 発言終了から文字起こし表示まで3秒以内

**Solution:**
- Apple Speech Framework（iOS端末側処理）で音声認識を実行
- サーバーへはtranscriptテキストのみ送信（音声データは送らない）
- ネットワーク遅延は最小（テキスト送信のみ）

**Validation:** iOS側でSpeech Framework完了→WebSocket送信→受信までの時間計測。

### NFR-004: LLM APIコスト

**Requirement:** 1ゲームあたりのLLM APIコスト ≤ $1.5

**Solution:**
- タスクごとにモデル使い分け:
  - シナリオ骨格生成: Claude Sonnet（品質重視）
  - 調査結果生成: Claude Haiku（高速・低コスト）
  - GM主導配布: Claude Haiku
  - 動的調整: Claude Sonnet
  - エンディング: Claude Sonnet
- テンプレートでプロンプトの定型部分を固定化しトークン消費を削減
- 発言ログは要約してからLLMに送信（全文送信を避ける）
- 調査結果のうちキャッシュ可能なものは再利用

**Validation:** 各API呼び出しのトークン数・コストをログに記録。ゲーム単位で集計。

### NFR-005: ゲーム中断耐性

**Requirement:** ネットワーク切断時にゲーム状態が失われない

**Solution:**
- 全状態変更をSQLiteに即時書き込み（Write-Ahead Logging有効）
- WebSocket切断検知 → プレイヤーを `offline` マーク → 他プレイヤーに通知
- 再接続時にフルゲーム状態（手帳・証拠・フェーズ情報）を再送
- ゲームは切断プレイヤーなしで継続可能

**Validation:** テスト時にネットワーク切断をシミュレートし、再接続後の状態復元を確認。

### NFR-006: 秘密情報の隔離

**Requirement:** 他プレイヤーの秘密情報がクライアントに漏れない

**Solution:**
- WebSocketメッセージ送信は必ず `filter_for_player(player_id, message)` を経由
- REST APIレスポンスにも同様のフィルタリングを適用
- `gm_internal_state` は絶対にクライアントに送信しない
- `Player.secret_info`, `Player.objective`, `Player.role` は本人のみ取得可能
- LLMプロンプト・応答はサーバー内で完結（クライアントに直接返さない）

**Validation:** APIレスポンス・WebSocketメッセージの全フィールドを検査するテスト。

### NFR-007: 初心者操作性

**Requirement:** マダミス未経験者が説明なしで参加・プレイ可能

**Solution:**
- フェーズごとのコンテキストガイド（サーバーからフェーズ説明テキストを配信）
- UI要素を最小限に絞り、現在のアクション可能なボタンをハイライト
- キャラ作成はステップバイステップのウィザード形式

**Validation:** マダミス未経験者によるプレイテスト。

### NFR-008: シナリオ整合性

**Requirement:** LLM生成シナリオに推理を破綻させる矛盾がない

**Solution:**
- シナリオ生成後にバリデーション用プロンプトで整合性チェック
- テンプレートで物語構造を制約（犯人は1人、動機は論理的、等）
- 矛盾検出時はLLMに再生成を指示（最大2回リトライ）

**Validation:** 生成されたシナリオのバリデーション通過率を計測。

### NFR-009: iOS対応バージョン

**Requirement:** iOS 17以上をサポート

**Solution:** Xcode Deployment Target = iOS 17.0

### NFR-010: スケーラビリティ

**Requirement:** 将来的に同時100セッション対応

**Solution:**
- 初期: Railway単一インスタンスで10セッション程度を想定
- スケール時: SQLite → PostgreSQL (SQLAlchemyで吸収)、Redis追加（セッション共有）、複数インスタンス化
- FastAPIの非同期処理により、I/O待ちが多いLLM呼び出しを効率的に処理

---

## Security Architecture

### Authentication

- セッショントークン（UUIDv4）をルーム作成/参加時に発行
- トークンはHTTPヘッダー（REST）またはクエリパラメータ（WebSocket）で送信
- トークンの有効期限: ゲーム終了まで（短命セッション）

### Authorization

- ホスト権限: `Player.is_host` フラグをサーバーサイドで検証
- 情報アクセス: 全データ取得に `player_id` フィルタを強制
- フェーズ操作（進行・延長）はホストのみ許可

### Data Encryption

- **通信:** TLS（HTTPS / WSS）- Railway標準提供
- **保存:** SQLiteファイルのOSレベル暗号化（Railwayのディスク暗号化）
- **秘密情報:** アプリケーションレベルでの追加暗号化は初期フェーズでは不要（サーバーサイドで隔離が保証されるため）

### Security Best Practices

- 入力バリデーション: Pydanticモデルで全REST/WebSocket入力をバリデーション
- SQLインジェクション防止: SQLAlchemy ORMでパラメータ化クエリ
- レート制限: FastAPIミドルウェアでAPI・WebSocketメッセージに制限
- room_codeの推測防止: 十分なエントロピー（6文字英数字 = 約20億通り）

---

## Scalability & Performance

### Scaling Strategy

- **Phase 1（初期）:** 単一インスタンス（Railway）。インメモリ状態 + SQLite
- **Phase 2（成長時）:** PostgreSQL移行 + Redis（インメモリ状態共有）→ 複数インスタンス対応
- **Phase 3（スケール時）:** AWS移行。ECS/Fargate + ALB + RDS + ElastiCache

### Performance Optimization

- アクティブゲーム状態をインメモリで保持（SQLiteは永続化バックアップ）
- LLM呼び出しは `asyncio` で非同期処理（他リクエストをブロックしない）
- 発言ログの要約を活用してLLMプロンプトのトークン数を削減
- WebSocketメッセージは最小限のJSONフィールドに絞る

### Caching Strategy

- テンプレートデータ: アプリ起動時にメモリにロード
- アクティブゲーム状態: Pythonオブジェクトとしてインメモリ保持
- 調査結果: 同一場所への重複調査はキャッシュ可能なものを再利用

### Load Balancing

- 初期: 不要（単一インスタンス）
- スケール時: WebSocket接続のスティッキーセッション対応ロードバランサー（ALB）

---

## Reliability & Availability

### High Availability Design

- 初期: 単一インスタンス（個人プロジェクトとして十分）
- Railway の自動再起動でプロセスクラッシュ時に復旧
- ゲーム状態がSQLiteに永続化されているため、再起動後もゲーム復旧可能

### Disaster Recovery

- RPO: 0（全状態変更を即時SQLiteに書き込み）
- RTO: 数分（Railway自動再起動 + ゲーム状態復元）

### Backup Strategy

- SQLiteファイルの定期バックアップ（Railway Volume）
- 将来PostgreSQL移行時は自動バックアップ活用

### Monitoring & Alerting

- **ログ:** Python `logging` → stdout → Railway Logs
- **メトリクス:**
  - LLM API呼び出し: レイテンシ・トークン数・コスト
  - WebSocket: 接続数・メッセージ数
  - ゲーム: セッション数・完了率
- **アラート:** Railway のヘルスチェック + 異常時のログアラート

---

## Development Architecture

### Code Organization

```
murder/
├── ios/                          # iOS アプリ
│   └── Madaminu/
│       ├── App/                  # アプリエントリポイント
│       ├── Views/                # SwiftUI Views
│       ├── Models/               # データモデル
│       ├── Services/             # API・WebSocket通信
│       └── Resources/            # アセット
├── server/                       # Python バックエンド
│   ├── pyproject.toml
│   ├── src/
│   │   └── madaminu/
│   │       ├── __init__.py
│   │       ├── main.py           # FastAPI app エントリポイント
│   │       ├── config.py         # 設定管理
│   │       ├── models/           # SQLAlchemy モデル
│   │       │   ├── game.py
│   │       │   ├── player.py
│   │       │   ├── phase.py
│   │       │   ├── evidence.py
│   │       │   └── ...
│   │       ├── routers/          # REST API ルーター
│   │       │   ├── rooms.py
│   │       │   ├── characters.py
│   │       │   ├── payments.py
│   │       │   └── history.py
│   │       ├── ws/               # WebSocket ハンドラー
│   │       │   ├── handler.py    # WebSocket接続管理
│   │       │   └── messages.py   # メッセージ型定義
│   │       ├── services/         # ビジネスロジック
│   │       │   ├── room_manager.py
│   │       │   ├── scenario_engine.py
│   │       │   ├── speech_processor.py
│   │       │   ├── notebook_service.py
│   │       │   └── payment_service.py
│   │       ├── llm/              # LLM連携
│   │       │   ├── client.py     # Claude API クライアント
│   │       │   ├── prompts.py    # プロンプトテンプレート
│   │       │   └── validator.py  # シナリオ整合性チェック
│   │       ├── templates/        # シナリオテンプレート（50パターン）
│   │       └── db/               # データベース
│   │           ├── database.py   # セッション管理
│   │           └── migrations/   # マイグレーション
│   └── tests/
│       ├── test_room_manager.py
│       ├── test_scenario_engine.py
│       └── ...
├── docs/                         # プロジェクトドキュメント
├── research/                     # リサーチ資料
└── bmad/                         # BMAD設定
```

### Testing Strategy

- **ユニットテスト:** pytest。Scenario Engine のロジック、メッセージフィルタリング、バリデーション
- **統合テスト:** pytest-asyncio。WebSocket通信、DB操作、API エンドポイント
- **セキュリティテスト:** 秘密情報漏洩テスト（他プレイヤーの情報がレスポンスに含まれないことを検証）
- **コスト計測テスト:** LLM呼び出しのトークン数・コストを記録するインストルメンテーション
- **カバレッジ目標:** 80%（サーバーサイド）

### CI/CD Pipeline

```
[Push to GitHub]
  → GitHub Actions
  → Server: uv sync → ruff check → ruff format --check → pytest
  → iOS: xcodebuild test (XCTest)
  → Deploy (mainブランチ):
      Server → Railway 自動デプロイ
      iOS → TestFlight (手動トリガー)
```

### Environments

| 環境 | 用途 | インフラ |
|---|---|---|
| dev | ローカル開発 | uvicorn ローカル + SQLite |
| staging | テスト | Railway (staging) |
| production | 本番 | Railway (production) |

---

## Requirements Traceability

### Functional Requirements Coverage

| FR ID | FR Name | Components | Notes |
|-------|---------|------------|-------|
| FR-001 | キャラクター作成 | Character Service | REST API |
| FR-002 | ルーム作成・参加 | Room Manager | REST API |
| FR-003 | ゲーム状態同期 | Room Manager | WebSocket |
| FR-004 | シナリオ骨格生成 | Scenario Engine | Claude API (Sonnet) |
| FR-005 | 個人手帳UI | Notebook Service | WebSocket + iOS |
| FR-006 | フェーズ進行管理 | Room Manager | WebSocket + タイマー |
| FR-007 | 発言権制マイク入力 | Speech Processor + Room Manager | iOS Speech + WebSocket |
| FR-008 | 動的調整 | Scenario Engine | Claude API (Sonnet) + GM内部状態 |
| FR-009 | 投票・エンディング | Scenario Engine + Room Manager | Claude API (Sonnet) |
| FR-010 | IAP課金 | Payment Service | StoreKit 2 + REST API |
| FR-011 | 音声認識修正 | Speech Processor | WebSocket |
| FR-012 | ゲーム進行ガイド | Room Manager + iOS | フェーズ説明テキスト配信 |
| FR-013 | プレイ履歴 | Game State Store | REST API |
| FR-014 | テンプレート選択 | Scenario Engine | REST API (ルーム設定) |
| FR-015 | 能動的探索 | Scenario Engine + Notebook Service | WebSocket + Claude API (Haiku) |

### Non-Functional Requirements Coverage

| NFR ID | NFR Name | Solution | Validation |
|--------|----------|----------|------------|
| NFR-001 | LLM応答速度 | ストリーミング + 事前生成 + テンプレート制約 | レイテンシログ |
| NFR-002 | WebSocket遅延 | インメモリ状態 + 軽量JSON | RTT計測 |
| NFR-003 | 音声認識レイテンシ | iOS端末側処理 | E2E時間計測 |
| NFR-004 | APIコスト | モデル使い分け + ログ要約 + テンプレート | トークン/コスト集計 |
| NFR-005 | 中断耐性 | SQLite即時書き込み + 再接続復元 | 切断シミュレーションテスト |
| NFR-006 | 秘密情報隔離 | player_idフィルタ + サーバー内完結 | レスポンス検査テスト |
| NFR-007 | 初心者操作性 | コンテキストガイド + 最小UI | プレイテスト |
| NFR-008 | シナリオ整合性 | バリデーションプロンプト + テンプレート制約 | 整合性チェック通過率 |
| NFR-009 | iOS対応 | Deployment Target iOS 17 | 実機テスト |
| NFR-010 | スケーラビリティ | SQLAlchemy抽象化 + 段階的移行計画 | 負荷テスト |

---

## Trade-offs & Decision Log

### Decision 1: Python/FastAPI（Rustではなく）

**Trade-off:**
- ✓ 開発速度が速い。LLM SDK（anthropic）との親和性が高い
- ✓ プロトタイプ→テスト→改善のサイクルを短く回せる
- ✗ Rustに比べてランタイムパフォーマンスは劣る
- **Rationale:** 個人開発でスピード重視。I/O待ち（LLM・DB）が主ボトルネックのためPythonの非同期処理で十分

### Decision 2: SQLite（PostgreSQLではなく）

**Trade-off:**
- ✓ デプロイがシンプル。追加インフラ不要
- ✓ 開発環境とプロダクション環境の差異が小さい
- ✗ 同時書き込みに弱い。複数インスタンスでの共有不可
- **Rationale:** 初期フェーズでは単一インスタンスで十分。SQLAlchemy経由でPostgreSQL移行は容易

### Decision 3: Apple Speech Framework（Whisper APIではなく）

**Trade-off:**
- ✓ 追加コストゼロ。端末側処理で低レイテンシ
- ✗ Whisperに比べて認識精度が劣る可能性
- **Rationale:** 発言権制により1人ずつ話すため雑音の影響は限定的。コスト削減を優先。精度不足なら将来Whisperに切り替え可能

### Decision 4: セッショントークン（JWTではなく）

**Trade-off:**
- ✓ 実装がシンプル。アカウント登録不要
- ✗ トークンの自己検証ができない（サーバー側でDB参照が必要）
- **Rationale:** 対面プレイ前提の短命セッション。ユーザー管理の複雑さを排除

### Decision 5: Railway（AWSではなく）

**Trade-off:**
- ✓ デプロイが極めてシンプル。GitHub連携で自動デプロイ
- ✗ スケーラビリティ・カスタマイズ性はAWSに劣る
- **Rationale:** 個人開発の初期フェーズ。運用負荷を最小化。スケール時にAWS移行

---

## Open Issues & Risks

1. **LLM APIコストの実測値が不明** — プロトタイプ段階で計測し、モデル選択・プロンプト最適化を調整
2. **シナリオテンプレート50パターンの設計** — 具体的な分類・構造は別途設計が必要
3. **発言権制 vs 自由議論のバランス** — プレイテストで検証し、ハイブリッド進行のルールを確定
4. **Apple Speech Frameworkの対面環境での精度** — 実機テストで検証
5. **SQLiteの同時接続制限** — ゲーム数が増えた場合のボトルネックを監視

---

## Assumptions & Constraints

### Assumptions

- プレイヤーはiPhone（iOS 17+）を所持
- 対面で4〜7人が同一Wi-Fi/LTE環境に接続可能
- Claude APIが安定稼働（SLA 99.5%以上）
- 1ゲーム30〜60分のプレイ時間

### Constraints

- 個人開発（開発リソース限定）
- LLM APIコスト ≤ $1.5/ゲーム
- App Store審査・課金ポリシー準拠
- iOS専用（Swift + SwiftUI）

---

## Future Considerations

- **PostgreSQL移行:** 同時セッション数の増加に応じて（SQLAlchemy ORMで吸収）
- **Redis導入:** 複数インスタンス対応時のインメモリ状態共有
- **AWS移行:** スケール要件発生時（ECS/Fargate + RDS + ElastiCache）
- **Whisper API導入:** Apple Speech Frameworkの精度不足時
- **Android版:** バックエンドは共通。iOS固有部分（Speech Framework, StoreKit）のみ差し替え
- **オンラインプレイ:** WebSocket基盤は流用可能。音声はWebRTC追加が必要

---

## Approval & Sign-off

**Review Status:**
- [ ] Product Owner (katsut)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-25 | katsut | Initial architecture |

---

## Next Steps

### Phase 4: Sprint Planning & Implementation

Run `/sprint-planning` to:
- Break epics into detailed user stories
- Estimate story complexity
- Plan sprint iterations
- Begin implementation following this architectural blueprint

**Key Implementation Principles:**
1. Follow component boundaries defined in this document
2. Implement NFR solutions as specified
3. Use technology stack as defined
4. Follow API contracts exactly
5. Adhere to security and performance guidelines

---

**This document was created using BMAD Method v6 - Phase 3 (Solutioning)**

*To continue: Run `/workflow-status` to see your progress and next recommended workflow.*

---

## Appendix A: LLM Cost Estimation

**1ゲーム（4人, 3フェーズ）の想定LLM呼び出し:**

| 呼び出し | モデル | 入力トークン | 出力トークン | 概算コスト |
|---|---|---|---|---|
| シナリオ骨格生成 | Sonnet | ~3,000 | ~2,000 | $0.025 |
| 秘密情報・目的生成 (×4人) | Sonnet | ~2,000 | ~1,000×4 | $0.036 |
| バリデーション | Haiku | ~3,000 | ~500 | $0.003 |
| 調査結果生成 (×8回) | Haiku | ~1,500 | ~300×8 | $0.012 |
| GM主導配布 (×3フェーズ) | Haiku | ~2,000 | ~500×3 | $0.006 |
| 動的調整 (×2回) | Sonnet | ~4,000 | ~1,500×2 | $0.039 |
| エンディング生成 | Sonnet | ~5,000 | ~2,000 | $0.035 |
| **合計** | | | | **~$0.16** |

※ 概算値。実際のプロンプト設計・モデル価格改定で変動。$1.5の予算内に十分収まる見込み。
