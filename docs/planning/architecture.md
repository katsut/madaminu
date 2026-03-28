# マダミヌ アーキテクチャ設計書

## 概要

マダミヌは AI が生成するマーダーミステリーをリアルタイムでプレイするモバイルゲーム。
サーバーが WebSocket でゲーム進行を制御し、LLM がシナリオ・証拠・エンディングを動的に生成する。

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| iOS | Swift / SwiftUI |
| サーバー | Python / FastAPI |
| DB | PostgreSQL (本番) / SQLite (開発) |
| ORM | SQLAlchemy (async) |
| マイグレーション | Alembic |
| LLM | OpenAI gpt-5.4-mini (シナリオ), gpt-5.4-nano (調査・調整) |
| 画像生成 | OpenAI gpt-image-1 |
| デプロイ | Railway (Docker) |

## サーバーアーキテクチャ

```
Router (HTTP/WS)
  ├── rooms.py      — ルーム CRUD、参加、準備
  ├── game.py       — ゲーム開始、状態取得
  ├── characters.py — キャラクター作成
  └── images.py     — 画像配信

Service
  ├── scenario_engine.py — LLM シナリオ生成・調査・改ざん・エンディング
  ├── phase_manager.py   — フェーズ遷移・タイマー・発見管理
  ├── speech_manager.py  — 発言権管理
  ├── ai_player.py       — AI プレイヤー補充
  ├── image_generator.py — 画像生成
  └── map_renderer.py    — SVG マップ生成

WebSocket
  ├── handler.py   — メッセージルーティング
  ├── manager.py   — 接続管理・ブロードキャスト
  └── messages.py  — メッセージ型定義
```

## ゲーム状態遷移

```
waiting ──→ generating ──→ playing ──→ voting ──→ ended
              │                │
              └── (失敗) ──→ waiting
              (playing から直接 ended も可)
```

## フェーズサイクル構造

```
initial(0s) → opening(0s) → [ planning(180s) → investigation(120s) → discussion(300s) ] × N → voting(180s)
                              └─────────────── 1ターン ───────────────┘
```

- `initial` / `opening`: duration=0、自動スキップ（初期証拠・アリバイ配布用）
- `planning`: 場所選択 + 会話。マップ表示、調査先を決定
- `investigation`: 選択した場所の features を調査。発見→保持/改ざん
- `discussion`: 証拠公開 + 発言。口頭=1pt、証拠カード=3pt
- `voting`: 犯人投票。全員投票完了でエンディング生成
- ターン数 N はルーム作成時に設定（デフォルト=3）

## iOS アーキテクチャ

```
AppStore (ObservableObject)
  ├── RoomStore      — ルーム情報・プレイヤーリスト
  ├── GamePlayStore  — フェーズ・発見・証拠・発言
  └── NotebookStore  — 手帳（証拠一覧）

dispatch(AppAction) → async メソッド → API/WS

WSMessageAdapter — WS メッセージを Store 状態に変換
```

**制約**:
- `ObservableObject` + `@Published`（`@Observable` は使わない）
- async メソッドに `@MainActor`、クラスには付けない
- WS コールバック内は `DispatchQueue.main.async`

## 画面遷移

```
home → lobby → generating → intro → playing → ended
  │      ↑         │                    │
  │      └─────────┘ (失敗時)           │
  └── characterCreation                 └→ voting → ended
```

## データモデル

### Game
- `id`, `room_code`, `status`, `password`
- `host_player_id`, `current_phase_id`
- `scenario_skeleton` (JSON), `gm_state` (JSON)
- `turn_count`, `total_llm_cost_usd`
- `scene_image`, `victim_image`, `map_svg`

### Player
- `id`, `game_id`, `device_id`, `session_token`
- `display_name`, `character_name`, `character_*` (プロフィール)
- `role` (criminal/witness/related/innocent)
- `secret_info`, `objective`, `public_info`
- `is_host`, `is_ai`, `is_ready`
- `portrait_image`, `connection_status`

### Phase
- `id`, `game_id`, `phase_type`, `phase_order`
- `duration_sec`, `started_at`, `deadline_at`

### Evidence
- `id`, `game_id`, `player_id`, `phase_id`
- `title`, `content`, `source` (gm_push/investigation)

## 外部依存

- OpenAI API: シナリオ生成、調査、改ざん、フェーズ調整、エンディング
- Railway: サーバーホスティング + PostgreSQL
- GitHub Actions: CI
