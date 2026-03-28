# ゲームフロー仕様書

## 概要

ゲーム開始からエンディングまでの全シーケンスを定義する。

## 1. ゲーム開始シーケンス

```
iOS (Host)              Server                    iOS (All Players)
    │                      │                          │
    │  POST /start         │                          │
    │─────────────────────→│                          │
    │  screen=generating   │                          │
    │                      │  WS: game.generating     │
    │                      │─────────────────────────→│
    │                      │                          │  screen=generating
    │                      │  [Background Task]       │
    │                      │  generate_scenario()     │
    │                      │  (最大3回リトライ)       │
    │                      │                          │
    │                      │  WS: progress            │
    │                      │  {scenario: done}        │
    │                      │─────────────────────────→│
    │                      │                          │
    │                      │  start_first_phase()     │
    │                      │                          │
    │                      │  WS: game.state          │
    │                      │  (各プレイヤー個別)      │
    │                      │─────────────────────────→│
    │                      │                          │
    │                      │  generate_images()       │
    │                      │  (並列: scene+portraits) │
    │                      │                          │
    │                      │  WS: game.state          │
    │                      │  (画像URL付き)           │
    │                      │─────────────────────────→│
    │                      │                          │
    │                      │  WS: game.ready          │
    │                      │─────────────────────────→│
    │  200 OK              │                          │  screen=intro
    │←─────────────────────│                          │  (or playing)
```

### 失敗時

```
Server                    iOS (All Players)
  │  [例外発生]             │
  │  status → waiting       │
  │  WS: game.generation_failed
  │────────────────────────→│
  │                         │  screen=lobby
  │                         │  エラーメッセージ表示
```

## 2. イントロシーケンス

```
iOS (Player)            Server                    iOS (All Players)
    │                      │                          │
    │  WS: intro.ready     │                          │
    │─────────────────────→│                          │
    │                      │  WS: intro.ready.count   │
    │                      │─────────────────────────→│
    │                      │                          │
    │  [全員 ready]        │                          │
    │  WS: intro.start_game│                          │
    │─────────────────────→│                          │
    │                      │  WS: intro.start_game    │
    │                      │─────────────────────────→│
    │                      │                          │  screen=playing
```

## 3. フェーズサイクルシーケンス

1ターン = planning → investigation → discussion

```
Server (PhaseManager)              iOS (All Players)
    │                                  │
    │  ===== Planning Phase =====      │
    │  WS: phase.started               │
    │  {type: planning, turn: 1/3}     │
    │─────────────────────────────────→│
    │                                  │  マップ表示
    │  WS: phase.timer (10秒毎)        │  場所選択
    │─────────────────────────────────→│
    │                                  │
    │  WS: investigate.select          │
    │←─────────────────────────────────│  場所決定
    │  WS: location.colocated          │
    │─────────────────────────────────→│  同室者表示
    │                                  │
    │  [時間切れ or advance]           │
    │  WS: phase.ended                 │
    │─────────────────────────────────→│
    │                                  │
    │  ===== Investigation Phase ===== │
    │  _generate_room_discoveries()    │
    │  (全 features → LLM 並列呼出)   │
    │                                  │
    │  WS: phase.started               │
    │  {type: investigation}           │
    │─────────────────────────────────→│
    │  WS: investigate.discoveries     │
    │  [{id, title, content, can_tamper}]
    │─────────────────────────────────→│  発見一覧表示
    │                                  │
    │  WS: investigate.keep            │
    │←─────────────────────────────────│  1つ保持
    │  keep_evidence() → DB保存        │
    │  WS: investigate.kept            │
    │─────────────────────────────────→│  手帳に追加
    │                                  │
    │  WS: investigate.tamper          │
    │←─────────────────────────────────│  1つ改ざん (単独時のみ)
    │  tamper_evidence() → LLM        │
    │  WS: investigate.tampered        │
    │─────────────────────────────────→│  内容書き換え
    │                                  │
    │  [時間切れ]                       │
    │  WS: phase.ended                 │
    │─────────────────────────────────→│
    │                                  │
    │  ===== Discussion Phase =====    │
    │  adjust_phase() → LLM           │
    │  (追加証拠配布)                   │
    │                                  │
    │  WS: phase.started               │
    │  {type: discussion}              │
    │─────────────────────────────────→│
    │                                  │
    │  WS: speech.request              │
    │←─────────────────────────────────│  発言権要求
    │  WS: speech.granted              │
    │─────────────────────────────────→│  録音開始
    │  WS: speech.release              │
    │←─────────────────────────────────│  発言終了+文字起こし
    │  WS: speech.active / released    │
    │─────────────────────────────────→│  発言履歴に追加
    │                                  │
    │  WS: evidence.reveal             │
    │←─────────────────────────────────│  証拠公開
    │  WS: evidence.revealed           │
    │─────────────────────────────────→│  全員に公開
    │                                  │
    │  [時間切れ]                       │
    │  WS: phase.ended                 │
    │─────────────────────────────────→│
    │                                  │
    │  ── ターン2, 3 も同様 ──         │
```

## 4. 投票・エンディングシーケンス

```
Server (PhaseManager)              iOS (All Players)
    │                                  │
    │  ===== Voting Phase =====        │
    │  WS: phase.started               │
    │  {type: voting}                  │
    │─────────────────────────────────→│
    │                                  │
    │  WS: vote.submit                 │
    │←─────────────────────────────────│  犯人投票
    │  WS: vote.cast                   │
    │─────────────────────────────────→│  投票済み表示
    │                                  │
    │  [全員投票完了]                   │
    │  WS: vote.results                │
    │─────────────────────────────────→│
    │                                  │
    │  generate_ending() → LLM         │
    │                                  │
    │  WS: game.ending                 │
    │  {ending_text, true_criminal_id, │
    │   objective_results}             │
    │─────────────────────────────────→│  screen=ended
```

## 5. ホスト操作

| 操作 | WS メッセージ | 効果 |
|------|-------------|------|
| フェーズ進行 | `phase.advance` | 即座に次フェーズへ |
| フェーズ延長 | `phase.extend` | +60秒 |
| 一時停止 | `phase.pause` | タイマー停止 |
| 再開 | `phase.resume` | タイマー再開 |

## 6. ルーム再参加

```
iOS                     Server
  │  POST /join           │
  │  (X-Device-Id)        │
  │──────────────────────→│
  │                       │  device_id で既存 Player 検索
  │                       │  → 存在: session_token 更新、既存 Player 返却
  │                       │  → 不在: 新規 Player 作成
  │  200 OK               │
  │←──────────────────────│
  │                       │
  │  WS 接続              │
  │──────────────────────→│
  │                       │  WS: game.state (現在の状態)
  │                       │──→ screen 復帰
```

## 7. WebSocket メッセージ一覧

### サーバー → クライアント

| type | data | 用途 |
|------|------|------|
| `game.generating` | `{room_code}` | シナリオ生成開始 |
| `game.ready` | `{room_code}` | ゲーム準備完了 |
| `game.generation_failed` | `{room_code}` | 生成失敗 |
| `game.state` | (後述) | ゲーム全状態 |
| `game.ending` | `{ending_text, true_criminal_id, objective_results}` | エンディング |
| `progress` | `{step, status}` | 生成進捗 |
| `phase.started` | `{phase_id, phase_type, duration_sec, turn_number, total_turns, investigation_locations}` | フェーズ開始 |
| `phase.timer` | `{remaining_sec}` | タイマー (10秒毎) |
| `phase.ended` | `{phase_type, next_phase_type}` | フェーズ終了 |
| `phase.paused` | `{remaining_sec}` | 一時停止 |
| `phase.resumed` | `{remaining_sec}` | 再開 |
| `phase.extended` | `{extra_sec, new_duration_sec}` | 延長 |
| `investigate.discoveries` | `{discoveries[]}` | 発見一覧 |
| `investigate.kept` | `{id, title, content}` | 保持完了 |
| `investigate.tampered` | `{id, content}` | 改ざん完了 |
| `location.colocated` | `{players[]}` | 同室プレイヤー |
| `speech.granted` | - | 発言権付与 |
| `speech.denied` | - | 発言権拒否 |
| `speech.active` | `{player_id}` | 発言中 |
| `speech.released` | `{character_name, transcript}` | 発言終了 |
| `evidence.revealed` | `{player_id, player_name, title, content}` | 証拠公開 |
| `evidence.received` | `{title, content}` | 証拠受け取り |
| `vote.cast` | `{voter_id}` | 投票済み |
| `vote.results` | `{votes}` | 投票結果 |
| `room_message.received` | `{sender_id, sender_name, text}` | ルームチャット |
| `intro.ready.count` | `{count}` | イントロ準備人数 |
| `intro.start_game` | - | イントロ終了→プレイ開始 |
| `player.connected` | `{player_id}` | 接続通知 |
| `player.disconnected` | `{player_id}` | 切断通知 |

### クライアント → サーバー

| type | data | 用途 |
|------|------|------|
| `intro.ready` | - | イントロ準備完了 |
| `intro.unready` | - | 準備キャンセル |
| `intro.start_game` | - | ゲーム開始 (ホスト) |
| `investigate.select` | `{location_id, feature?}` | 場所/feature 選択 |
| `investigate.keep` | `{discovery_id}` | 発見を保持 |
| `investigate.tamper` | `{discovery_id}` | 発見を改ざん |
| `speech.request` | - | 発言権要求 |
| `speech.release` | `{transcript}` | 発言終了 |
| `evidence.reveal` | `{evidence_id}` | 証拠公開 |
| `vote.submit` | `{suspect_player_id}` | 犯人投票 |
| `room_message.send` | `{text}` | ルームチャット送信 |
| `phase.advance` | - | フェーズ進行 (ホスト) |
| `phase.extend` | - | フェーズ延長 (ホスト) |
| `phase.pause` | - | 一時停止 (ホスト) |
| `phase.resume` | - | 再開 (ホスト) |

## 8. game.state データ構造

各プレイヤーに個別送信される。自分の秘密情報のみ含む。

```json
{
  "status": "playing",
  "host_player_id": "...",
  "my_role": "innocent",
  "my_secret_info": "実は借金がある",
  "my_objective": "真犯人を見つける",
  "scenario_setting": "{\"location\": \"...\", \"situation\": \"...\"}",
  "victim": "{\"name\": \"...\", \"description\": \"...\"}",
  "scene_image_url": "/api/v1/images/...",
  "victim_image_url": "/api/v1/images/...",
  "map_url": "/api/v1/images/.../map",
  "players": "[{\"id\": \"...\", \"display_name\": \"...\", \"character_name\": \"...\", ...}]",
  "my_evidences": "[{\"title\": \"...\", \"content\": \"...\"}]",
  "current_phase": "{\"phase_id\": \"...\", \"phase_type\": \"planning\", ...}",
  "current_speaker_id": null
}
```

## 9. フェーズ時間設定

| フェーズ | デフォルト時間 | 説明 |
|---------|-------------|------|
| initial | 0秒 | 自動スキップ |
| opening | 0秒 | 自動スキップ |
| planning | 180秒 (3分) | 場所選択 + 会話 |
| investigation | 120秒 (2分) | 調査実行 |
| discussion | 300秒 (5分) | 議論 + 証拠公開 |
| voting | 180秒 (3分) | 犯人投票 |

1ターン合計: 10分。3ターン + 投票 = 約33分。

## 10. LLM 呼び出しポイント

| タイミング | 関数 | モデル | 用途 |
|-----------|------|--------|------|
| ゲーム開始 | `generate_scenario()` | gpt-5.4-mini | シナリオ全体生成 |
| investigation 開始 | `investigate_location()` | gpt-5.4-nano | 各 feature の発見生成 |
| investigate.tamper | `tamper_evidence()` | gpt-5.4-nano | 証拠改ざん |
| discussion 開始 | `adjust_phase()` | gpt-5.4-nano | 追加証拠配布 |
| 全員投票後 | `generate_ending()` | gpt-5.4-mini | エンディング生成 |

コスト上限: $2.00 / ゲーム
