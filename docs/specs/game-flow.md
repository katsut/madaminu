# ゲームフロー仕様書 (v3)

> v3 アーキテクチャに合わせて全面改訂（2026-05-02）。フェーズ遷移は **個別の `phase.*` イベントを送らず、すべて `game.state` の差分で表現する**。旧仕様（phase.started/ended ベース）は廃止。

## 概要

ゲーム開始からエンディングまでの全シーケンス。詳細メッセージ仕様は [message-design-v3.md](./message-design-v3.md)、アーキ全景は [architecture-v3.md](./architecture-v3.md) を参照。

---

## 1. ゲーム開始シーケンス

```
iOS (Host)              Server                         iOS (All Players)
    │                      │                              │
    │ POST /start          │                              │
    │ (X-Session-Token)    │                              │
    │─────────────────────→│                              │
    │                      │ ▼ start_game endpoint        │
    │                      │  • is_ready チェック         │
    │                      │  • 4人未満なら fill_ai_players│
    │                      │  • status = generating       │
    │                      │  • create_task(_generate_..) │
    │                      │                              │
    │                      │ WS: game.generating          │
    │                      │─────────────────────────────→│ screen=generating
    │ 200 OK               │                              │
    │←─────────────────────│                              │
    │                      │                              │
    │                      │ ▼ background task            │
    │                      │  generate_scenario() ×3 retry│
    │                      │ WS: progress(scenario,done)  │
    │                      │─────────────────────────────→│
    │                      │                              │
    │                      │  _generate_images() (並列)   │
    │                      │  • scene + victim + portraits│
    │                      │ WS: progress(scene_image,..)│
    │                      │ WS: progress(portraits,..)  │
    │                      │─────────────────────────────→│
    │                      │                              │
    │                      │  advance_phase() → 第1フェーズ│
    │                      │  (storytelling, status=preparing)
    │                      │ WS: game.state               │
    │                      │─────────────────────────────→│ 1st game.state: 遷移パネル
    │                      │                              │
    │                      │  3秒待機 → status=ready      │
    │                      │ WS: game.state               │
    │                      │─────────────────────────────→│ 2nd game.state: 画面表示
    │                      │ WS: game.ready               │
    │                      │─────────────────────────────→│
```

### 失敗時

シナリオ生成が 3 回リトライ全滅した場合のみ。

```
Server                          iOS (All Players)
  │ status → waiting              │
  │ WS: game.generation_failed    │
  │──────────────────────────────→│ screen=lobby + エラー表示
```

### Acceptance

- ホストが `screen=generating` を即座に表示する（API レスポンス前）
- 4 人未満のとき AI が動的生成され `is_ready=True` で参加する
- 生成失敗時はロビーに復帰、`game.total_llm_cost_usd` は累積したまま
- LLM コストが `LLM_COST_LIMIT_USD = 2.0` 超過なら start で 429 を返す

---

## 2. 2 段階フェーズ遷移プロトコル

すべてのフェーズ遷移はこの形式で起こる。

| # | サーバー処理 | broadcast | クライアント表示 |
|---|------------|-----------|-----------------|
| 1 | advance（旧フェーズ ended_at 設定 → 新フェーズ started_at 設定 / `discoveries_status=preparing`） | 1st `game.state` | `current_phase.id` 差分検知 → 遷移パネル表示 |
| 2 | 3 秒後（investigation は LLM discovery 完了待ち）に `discoveries_status=ready` を設定 | 2nd `game.state` | `discoveries_status=ready` 検知 → 遷移パネル消去 → フェーズ画面 |
| 3 | `schedule_phase_timer(duration_sec)` | — | `current_phase.deadline_at` でタイマー開始 |

`duration_sec == 0` のフェーズ（storytelling / briefing）はホスト手動 `advance` でのみ進む。

---

## 3. イントロシーケンス

ゲーム開始直後の opening よりさらに前段。プレイヤーが自分のキャラ情報・秘密・目的を確認する画面。

```
iOS (各プレイヤー)         Server
    │                         │
    │ WS: intro.ready          │
    │ (またはintro.unready)    │
    │────────────────────────→│
    │                         │ 全員に broadcast
    │ WS: intro.ready.count   │
    │←────────────────────────│
    │                         │
    │                         │ 全員 ready 検知
    │ WS: intro.all_ready     │
    │←────────────────────────│ → 自動的に opening へ
```

> **未実装**: 旧仕様にあった `intro.start_game`（ホスト送信）はサーバーで処理されない。現状は全員 ready で自動進行。

イントロ画面（9 ページ）:
1. オープニング（舞台説明）
2. 被害者紹介
3. 自分のプロフィール
4. 公開情報（この集まりでの立場）
5. 秘密情報
6. 個人目的（**他のプレイヤーにバレてはいけない**）
7. 初期証拠・アリバイ
8. 全キャラクター一覧
9. 準備完了（全員 ready で開始）

---

## 4. フェーズフロー

```
storytelling → opening → briefing → [discussion → planning → investigation] × turn_count → voting → ending
                                    ▲ 1 ターン分
```

`turn_count` はルーム作成時に 2〜5 で指定（既定 3）。

### 4.1 storytelling（読み合わせ・ホスト手動 0s）

ホストが NovelTextView（サウンドノベル風）で物語を読み上げ。被害者は生きている前提。最後に被害者が参加者に自己紹介を促す。

ホストが `advance` を送ると次フェーズへ。

### 4.2 opening（自己紹介・タイマー 300s）

各プレイヤーが順に `speech.request` → `speech.release {transcript}` で自己紹介。AI も一人称で `speech` を発信する（推理禁止のシステムプロンプト）。

### 4.3 briefing（事件概要・ホスト手動 0s）

`murder_discovery` テキストで事件発覚を演出。被害者情報、発見状況、事件詳細、カード配布、秘密・目的確認。

ホスト `advance` で discussion へ。

### 4.4 discussion（議論・タイマー 180s）

- `speech.request` → `speech.release` で発言（割り込み可）
- `reveal_evidence` で手持ち証拠を全員に公開（`evidence_revealed` ブロードキャスト）
- AI も 10〜30 秒間隔で `speech` を発信
- AI は 80% 確率で kept evidence を公開、全 AI が公開しなかった場合 1 人が強制公開

タイマー切れ → 自動で `advance(force=True)` → planning へ。

### 4.5 planning（調査計画・タイマー 120s）

- マップ表示。`select_location {location_id}` で各自が調査場所を選択
- 未選択者にはサーバーがランダム割当
- タイマー切れ → 自動で investigation へ

### 4.6 investigation（調査・タイマー 120s）

遷移時にサーバーが LLM (`gpt-5.4-nano`) で各部屋の `features` を調査結果に変換 → `discoveries_status=ready` を broadcast。

- `keep_evidence {discovery_id}` で 1 つだけ手帳に保持（同フェーズ内 1 回のみ）
- 同室プレイヤーには `location.colocated` で互いを通知
- 同室者間で `room_message {text}` のチャットが可能
- AI は自動で 1 つ keep する
- `tamper_evidence`（証拠改ざん）は **v3 では未実装**

タイマー切れ → 次ターン discussion へ（残ターンがあれば）。最終ターン後は voting へ。

### 4.7 voting（投票・タイマー 300s）

- 最終議論（`speech.request` で発言可）
- `vote {suspect_player_id}` で投票（1 人 1 回）
- 各投票で `vote_cast {voted_count, total_human}` をブロードキャスト
- **全員投票完了で即座に ending へ遷移（タイマーを待たない）**

### 4.8 ending（結果発表）

サーバーが `generate_ending`（`gpt-5.4-mini`）でエンディング生成 + スコア計算 + 個人目的達成判定。完了次第 `game.state` で配信。

iOS 側は以下を順に演出:

1. **シーン 1（黒背景 4s）**: 「○○は・・・・」
2. **シーン 2（5s）**: 「犯人でした / 冤罪でした」
3. **エンディング画面（スクロール）**:
   1. 投票結果（最多票に「監禁」マーク）
   2. エピローグ（LLM 生成）
   3. 最終スコア（🥇🥈🥉、発言×1pt + 証拠公開×3pt）
   4. 個人目的の達成状況（○/×）
   5. ネタバラシ（全キャラの役割・秘密公開）
   6. 「もう一度見る」/ 「ホームに戻る」

---

## 5. WS 接続維持・再接続

- サーバーは URLSession の WebSocket ping フレームを 20 秒間隔で送出
- 切断検知 → クライアントが指数バックオフで再接続（1, 2, 4, 8, 16, 30 秒。最大 10 回）
- 再接続成功 → サーバーが `game.state` を自動送信 → クライアントは差分適用（遷移パネルなし、UI 更新のみ）

再接続は新規接続と同じプロトコル。特別な処理はサーバーに無い。

---

## 6. ホスト操作

| 操作 | メッセージ | 効果 |
|------|-----------|------|
| フェーズ強制進行 | `advance {force: true}` | storytelling/briefing/タイマー切れ前の強制進行 |
| LLM 生成リトライ | `retry_generation` | discovery 生成失敗時に再実行 |

> **注**: 旧仕様にあった `phase.extend` / `phase.pause` / `phase.resume` は v3 ハンドラで no-op。延長・一時停止機能は v3 から取り下げ。

---

## 7. ルーム再参加

```
iOS                     Server
  │ POST /join (X-Device-Id) │
  │─────────────────────────→│
  │                          │ device_id で既存 Player 検索
  │                          │ → 存在 & ゲーム未開始: session_token 更新
  │                          │ → 不在 & waiting: 新規 Player 作成
  │                          │ → 不在 & started: 404 / 422
  │ 200 OK                   │
  │←─────────────────────────│
  │                          │
  │ WS 接続                   │
  │─────────────────────────→│ プレイヤー認証
  │ WS: game.state           │ 接続時に必ず送信
  │←─────────────────────────│ → 適切な screen に復帰
```

---

## 8. LLM 呼び出しポイント

| タイミング | 関数 | モデル | 目的 |
|-----------|------|--------|------|
| ゲーム開始 | `generate_scenario()` | `gpt-5.4-mini` | シナリオ全体生成 |
| ゲーム開始 | `_generate_ai_character()` | `gpt-5.4-nano` | AI キャラ動的生成（必要数だけ） |
| ゲーム開始 | `generate_scene_image` / `generate_victim_portrait` / `generate_character_portrait` | `gpt-image-1` | 画像生成（並列） |
| investigation 開始 | discovery 生成 | `gpt-5.4-nano` | 各部屋 features の調査結果 |
| discussion AI 発言 | `generate_ai_speech()` | `gpt-5.4-nano` | フェーズ別 AI 発言 |
| voting 終了時 | `generate_ending()` | `gpt-5.4-mini` | エンディング生成 |

コスト上限: **$2.00 / ゲーム**（超過で start 時 429）。
JSON 修復: `json-repair` ライブラリで壊れた LLM 出力を自動修復。

---

## 9. game.state データ構造

`schemas/game.py:build_game_state` が真。各プレイヤーに個別送信され、自分の秘密情報のみ含む。

```json
{
  "type": "game.state",
  "data": {
    "room_code": "ABC123",
    "status": "playing",
    "host_player_id": "...",

    "current_phase": {
      "id": "...",
      "phase_type": "investigation",
      "phase_order": 6,
      "duration_sec": 120,
      "started_at": "2026-05-02T10:00:00Z",
      "deadline_at": "2026-05-02T10:02:00Z",
      "turn_number": 2,
      "total_turns": 3,
      "discoveries_status": "ready",
      "current_speaker_id": null,
      "investigation_locations": [
        {"id": "study", "name": "書斎", "features": ["本棚", "机", "窓"]}
      ]
    },

    "my_role": "innocent",
    "my_secret_info": "...",
    "my_objective": "...",
    "my_location_id": "study",

    "scenario_setting": {"location": "...", "situation": "..."},
    "victim": {"name": "...", "description": "..."},
    "scene_image_url": "/api/v1/images/game/ABC123/scene",
    "victim_image_url": "/api/v1/images/game/ABC123/victim",
    "map_url": "/api/v1/images/game/ABC123/map",

    "players": [
      {
        "id": "...",
        "display_name": "Alice",
        "character_name": "探偵",
        "is_host": true,
        "is_ai": false,
        "is_ready": true,
        "connection_status": "online",
        "portrait_url": "/api/v1/images/player/..."
      }
    ],

    "my_evidences": [
      {"id": "...", "title": "...", "content": "...", "evidence_id": "..."}
    ],

    "vote_status": {
      "voted_count": 2,
      "total_human": 4,
      "my_vote": null
    },

    "ending_data": null,

    "intro_ready_count": 3,
    "storytelling_reader_id": "..."
  }
}
```
