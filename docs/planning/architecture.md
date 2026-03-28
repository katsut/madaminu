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
| LLM | OpenAI gpt-5.4-mini (シナリオ・エンディング), gpt-5.4-nano (調査・調整・AI発言・AIキャラ生成) |
| 画像生成 | OpenAI gpt-image-1 |
| JSON修復 | json-repair (LLM出力の壊れたJSONを自動修復) |
| デプロイ | Railway (Docker, GitHub連携で自動デプロイ) |

## サーバーアーキテクチャ

```
Router (HTTP/WS)
  ├── rooms.py      — ルーム CRUD、参加(device_id再参加対応)、準備
  ├── game.py       — ゲーム開始(バックグラウンド生成)、状態取得
  ├── characters.py — キャラクター作成
  └── images.py     — 画像配信

Service
  ├── scenario_engine.py — LLM シナリオ生成・調査・改ざん・エンディング
  ├── phase_manager.py   — フェーズ遷移・タイマー・発見管理・エンディング生成
  ├── speech_manager.py  — 発言権管理(先着制、割り込み可)
  ├── ai_player.py       — AIプレイヤー動的生成(LLM)・AI発言(フェーズ別)
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
              │                                    ↑
              └── (失敗) ──→ waiting                │
                                                   │
              (全員投票完了 → エンディング生成 → ended)
```

## フェーズサイクル構造

```
initial(0s) → opening(300s) → [ planning(180s) → investigation(120s) → discussion(300s) ] × N → voting(180s) → ending
               自己紹介         └─────────────── 1ターン ───────────────┘                         タイマーで
                                                                                                 自動進行しない
```

- `initial`: duration=0、自動スキップ（初期証拠・アリバイ配布用）
- `opening`: 自己紹介タイム(300秒)。発言ボタンで自己紹介、AI も自己紹介する
- `planning`: 場所選択 + 会話。マップ表示、調査先を決定。未選択者にはランダム割当
- `investigation`: 選択した場所の features を調査。発見→保持/改ざん
- `discussion`: 証拠公開 + 発言。口頭=1pt、証拠カード=3pt。議論記録は手帳に保存
- `voting`: 犯人投票 + 発言可。タイマーで自動進行しない（全員投票完了を待つ）
- `ending`: 投票結果→犯人/冤罪リビール→エピローグ→スコア→ネタバラシ
- ターン数 N はルーム作成時に設定（デフォルト=3）

## iOS アーキテクチャ

```
AppStore (ObservableObject)
  ├── RoomStore      — ルーム情報・プレイヤーリスト
  ├── GamePlayStore  — フェーズ・発見・証拠・発言・遷移状態
  └── NotebookStore  — 手帳（証拠・議論記録・メモ）

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
  │      ↑         │                    │        │
  │      └─────────┘ (失敗時)           │        └→ リプレイ可
  └── characterCreation                 │
                                        ├→ opening (自己紹介)
                                        ├→ planning (調査計画)
                                        ├→ investigation (調査)
                                        ├→ discussion (議論)
                                        └→ voting (投票)
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
- `investigation_locations` (JSON, planning/investigation で使用)

### Evidence
- `id`, `game_id`, `player_id`, `phase_id`
- `title`, `content`, `source` (gm_push/investigation)

### GameEnding
- `id`, `game_id`, `ending_text`, `true_criminal_id`
- `objective_results` (JSON)

## 手帳（Notebook）

| タブ | 内容 |
|------|------|
| 自分 | 役割・秘密・目的(※他人にバレてはいけない)・立場 |
| 登場人物 | 全キャラのプロフィール・アバター・公開情報 |
| マップ | SVGマップ表示(ハイライト対応) |
| 証拠 | 収集した証拠カード一覧 |
| 議論 | ターン別の発言履歴+証拠提出記録(アバター付き) |
| メモ | 自由記入欄 |

手帳はオーバーレイ表示で、開いたまま発言ボタンを使える。

## スコアリング

| アクション | ポイント |
|-----------|---------|
| 口頭発言 (SpeechLog) | 1pt / 回 |
| 証拠カード提出 (Evidence) | 3pt / 件 |

エンディングでランキング形式(🥇🥈🥉)で発表。

## 発言権管理

- 発言ボタンは opening / planning / discussion / voting で使用可能
- 新しいリクエストが来ると、現在の発言者は自動キャンセルされる（割り込み制）
- AI は opening / discussion / voting で自動発言（フェーズに応じた内容）

## AIプレイヤー

- 4人未満の場合、LLM でシナリオ設定に合ったキャラクターを動的生成
- 固定テンプレートなし。毎回ユニークなキャラクター
- AI発言はフェーズごとにプロンプトが変わる:
  - opening: 一人称で自己紹介（推理禁止）
  - discussion: 推理・質問・証拠に基づく主張
  - voting: 最後の犯人指名

## ルーム再参加

- `device_id` で既存プレイヤーを検索
- 存在すれば session_token を更新して既存 Player を返却（ホスト権限維持）
- ゲーム開始後でも同じデバイスなら復帰可能

## 外部依存

- OpenAI API: シナリオ生成、調査、改ざん、フェーズ調整、エンディング、AIキャラ生成、AI発言
- Railway: サーバーホスティング + PostgreSQL（GitHub連携自動デプロイ）
- GitHub Actions: CI
