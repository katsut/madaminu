# メッセージ設計 v3

## WS メッセージフォーマット

全メッセージは JSON。`type` で識別。

```json
{
  "type": "message_type",
  "data": { ... }
}
```

サーバーからのレスポンスは同じ WS 接続で返す。エラーは `error` type で返す。

---

## クライアント → サーバー

### ゲーム進行

v3 ハンドラは新旧 type 名の両方を受け付ける（カッコ内は legacy alias）。

| type | data | フェーズ | バリデーション |
|------|------|---------|-------------|
| `advance` (`phase.advance`, `phase.timer_expired`) | `{force?: bool}` | 全て | deadline_at 超過チェック。force はホストのみ。Phase.ended_at IS NULL で排他 |
| `phase.extend` / `phase.pause` / `phase.resume` / `phase.timer` | — | — | **未実装（受信されるが何もしない）**。延長・一時停止機能は v3 で取り下げ。将来追加する場合はここに仕様追加すること |

#### advance のレスポンス（game.state で返す）

advance 成功時はサーバーが全クライアントに `game.state` を送信。送信元クライアントもこれで遷移を検知する。

advance が不要だった場合（期限前、既に遷移済み）は送信元にのみ `error` を返す。

```json
// 期限前
{"type": "error", "data": {"code": "not_expired", "remaining_sec": 45}}

// 既に遷移済み（game.state が別途届くので何もしなくて良い）
{"type": "error", "data": {"code": "already_advanced"}}
```

### イントロ

| type | data | バリデーション |
|------|------|-------------|
| `intro.ready` | — | ゲーム状態が playing、イントロ中 |
| `intro.unready` | — | 同上 |
| `intro.start` | — | **未実装**。現状はイントロ全員 ready のシグナルとして `intro.all_ready` をサーバーから broadcast するのみ |

### 調査

| type | data | フェーズ | バリデーション |
|------|------|---------|-------------|
| `select_location` (`investigate.select`) | `{location_id}` | planning | location_id がマップに存在するか |
| `keep_evidence` (`investigate.keep`) | `{discovery_id}` | investigation | 同フェーズで未 keep。discovery_id が自分のものか |
| `tamper_evidence` (`investigate.tamper`) | `{discovery_id}` | investigation | **v3 では未実装**。改ざん機能は仕様策定中 |

### 発言

| type | data | フェーズ | バリデーション |
|------|------|---------|-------------|
| `speech.request` | — | storytelling/opening/discussion/voting | 発言可能フェーズか |
| `speech.release` | `{transcript}` | 同上 | current_speaker_id == 自分 |

### 議論

| type | data | フェーズ | バリデーション |
|------|------|---------|-------------|
| `reveal_evidence` (`evidence.reveal`) | `{evidence_id}` | discussion | evidence_id が自分のもの。未公開か |
| `room_message` (`room_message.send`) | `{text}` | investigation | 同室にいるか |

### 投票

| type | data | フェーズ | バリデーション |
|------|------|---------|-------------|
| `vote` (`vote.submit`) | `{suspect_player_id}` | voting | 未投票か。suspect が有効プレイヤーか |

---

## サーバー → クライアント

### game.state（フルステート）

最も重要なメッセージ。以下のタイミングで送信：
- WS 接続確立時（自動）
- フェーズ変更時（全員に）
- discoveries 生成完了時（全員に）
- 投票完了でゲーム終了時（全員に）

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
      "deadline_at": "2026-03-31T10:02:00Z",
      "started_at": "2026-03-31T10:00:00Z",
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
    "scene_image_url": "/api/v1/images/...",
    "victim_image_url": "/api/v1/images/...",
    "map_url": "/api/v1/images/.../map",

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

    "storytelling_reader_id": "...",
    "intro_ready_count": 3
  }
}
```

### ライフサイクル通知

| type | data | 説明 |
|------|------|------|
| `game.generating` | `{room_code}` | start_game 受領直後 |
| `game.ready` | `{room_code}` | シナリオ + 画像生成完了 |
| `game.generation_failed` | `{room_code}` | シナリオ生成 3 回リトライ全滅。status は waiting に戻る |
| `progress` | `{step, status}` | `step ∈ {scenario, scene_image, portraits}`、`status ∈ {in_progress, done}` |
| `player.connected` / `player.disconnected` | `{player_id}` | WS 接続変動（同室全員に） |

### リアルタイム通知

| type | data | 説明 |
|------|------|------|
| `speech.granted` | `{player_id}` | 発言権が付与された（送信元のみ） |
| `speech.active` | `{player_id}` | 誰かが発言中（全員に） |
| `speech` | `{player_id, character_name, transcript}` | 発言終了（人間・AI 共通） |
| `evidence_revealed` | `{player_id, player_name, title, content}` | 証拠公開（全員に） |
| `vote_cast` | `{voted_count, total_human}` | 投票（全員に） |
| `room_message` | `{sender_id, sender_name, text}` | 同室チャット（同室のみ） |
| `intro.ready.count` | `{count}` | イントロ準備人数 |
| `intro.all_ready` | — | 全員 ready |
| `location.colocated` | `{players: [...]}` | 同じ場所のプレイヤー（投入は investigation 開始直後 1 回） |

> **Note**: `phase.started` / `phase.ended` / `phase.timer` 等の個別フェーズイベントは v3 では送信しない。フェーズ遷移は常に `game.state` の `current_phase` 差分で表現する。

### エラー

```json
{
  "type": "error",
  "data": {
    "code": "not_expired",
    "message": "フェーズはまだ終了していません",
    "remaining_sec": 45
  }
}
```

| code | 説明 |
|------|------|
| `not_expired` | まだ deadline 前 |
| `already_advanced` | 他プレイヤーが先に遷移済み |
| `already_kept` | 同フェーズで既に keep 済み |
| `already_voted` | 既に投票済み |
| `not_your_turn` | 発言権がない |
| `invalid_phase` | 現フェーズではできない操作 |
| `not_host` | ホスト権限が必要 |
| `not_found` | 指定リソースが見つからない |

---

## メッセージフロー例

### フェーズ遷移（discussion → planning）

```
Client A                    Server                  Client B
  │                           │                       │
  │ {advance}                 │                       │
  │──────────────────────────→│                       │
  │                           │ DB: discussion → planning
  │                           │                       │
  │ {game.state}              │ {game.state}          │
  │←──────────────────────────│──────────────────────→│
  │                           │                       │
  │ phase_id が違う           │      phase_id が違う  │
  │ → 遷移画面表示            │     → 遷移画面表示    │
```

### 発言

```
Client A                    Server                  Client B
  │                           │                       │
  │ {speech.request}          │                       │
  │──────────────────────────→│                       │
  │                           │ DB: speaker = A
  │ {speech.granted, A}       │ {speech.active, A}    │
  │←──────────────────────────│──────────────────────→│
  │                           │                       │
  │ (録音中...)               │                       │
  │                           │                       │
  │ {speech.release, "..."}   │                       │
  │──────────────────────────→│                       │
  │                           │ DB: speaker = null
  │                           │ DB: SpeechLog 保存
  │ {speech, A, "..."}        │ {speech, A, "..."}    │
  │←──────────────────────────│──────────────────────→│
```

### 調査（planning → investigation → discussion）

```
Client A                    Server                  Client B
  │                           │                       │
  │ {select_location, "study"}│                       │
  │──────────────────────────→│                       │
  │                           │ DB: selection 保存     │
  │                           │                       │
  │ {advance}                 │                       │
  │──────────────────────────→│                       │
  │                           │ DB: planning → investigation
  │                           │ DB: discoveries_status = generating
  │                           │ create_task(generate)
  │                           │                       │
  │ {game.state}              │ {game.state}          │
  │ (status=generating)       │ (status=generating)   │
  │←──────────────────────────│──────────────────────→│
  │                           │                       │
  │ 遷移画面「準備中...」     │ 遷移画面「準備中...」 │
  │                           │                       │
  │                           │ [LLM 3-5秒]          │
  │                           │ DB: evidences 保存    │
  │                           │ DB: status = ready    │
  │                           │                       │
  │ {game.state}              │ {game.state}          │
  │ (status=ready)            │ (status=ready)        │
  │←──────────────────────────│──────────────────────→│
  │                           │                       │
  │ 遷移画面消去              │ 遷移画面消去          │
  │ GET /discoveries          │ GET /discoveries      │
  │──────────────────────────→│←──────────────────────│
  │ feature 一覧表示          │ feature 一覧表示      │
  │                           │                       │
  │ {keep_evidence, "ev123"}  │                       │
  │──────────────────────────→│                       │
  │                           │ DB: Evidence保存       │
  │ {game.state}              │                       │
  │ (my_evidences 更新)       │                       │
  │←──────────────────────────│                       │
```

### 投票 → エンディング

```
Client A                    Server                  Client B
  │                           │                       │
  │ {vote, suspect: B}        │                       │
  │──────────────────────────→│                       │
  │                           │ DB: Vote 保存          │
  │ {vote_cast, 1/4}          │ {vote_cast, 1/4}      │
  │←──────────────────────────│──────────────────────→│
  │                           │                       │
  │                           │ (Client B も投票)      │
  │                           │                       │
  │                           │ [全員投票完了]         │
  │                           │ DB: game → ended       │
  │                           │ create_task(generate_ending)
  │                           │                       │
  │ {game.state}              │ {game.state}          │
  │ (status=ended, ending生成中)                      │
  │←──────────────────────────│──────────────────────→│
  │                           │                       │
  │                           │ [LLM でエンディング生成]
  │                           │                       │
  │ {game.state}              │ {game.state}          │
  │ (ending_data 含む)        │ (ending_data 含む)    │
  │←──────────────────────────│──────────────────────→│
  │                           │                       │
  │ リビール演出開始          │ リビール演出開始      │
```

---

## WS 再接続シーケンス

```
Client                      Server
  │                           │
  │ (接続切断検知)            │
  │                           │
  │ 1秒待機                   │
  │ WS 接続                   │
  │──────────────────────────→│
  │                           │ DB からプレイヤー認証
  │                           │ DB から最新 game.state 構築
  │ {game.state}              │
  │←──────────────────────────│
  │                           │
  │ ローカル状態と比較        │
  │ phase_id が違う → 遷移    │
  │ 同じ → タイマー等更新     │
```

再接続プロトコルは特別なものではない。新規接続と同じ。
サーバーは接続時に必ず `game.state` を送る。クライアントは受信したら差分適用する。それだけ。
