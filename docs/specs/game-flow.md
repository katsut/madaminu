# ゲームフロー仕様書

## 概要

ゲーム開始からエンディングまでの全シーケンスを定義する。

## 1. ゲーム開始シーケンス

```
iOS (Host)              Server                    iOS (All Players)
    │                      │                          │
    │  screen=generating   │                          │
    │  POST /start         │                          │
    │─────────────────────→│                          │
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

**ポイント**:
- iOS はAPIを呼ぶ前に screen=generating に遷移（即座にフィードバック）
- AIプレイヤーはLLMで動的生成（シナリオ設定に合ったキャラクター）
- 生成失敗時は game.status を waiting に戻し、ロビーに復帰

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

イントロ画面の構成（9ページ）:
1. オープニング（舞台説明）
2. 被害者紹介
3. 自分のプロフィール
4. 公開情報（この集まりでの立場）
5. 秘密情報
6. 個人目的（※他のプレイヤーにバレてはいけない）
7. 初期証拠・アリバイ
8. 全キャラクター一覧
9. 準備完了（ロビー形式、全員 ready でホストが開始）

## 3. 自己紹介フェーズ（opening）

```
Server (PhaseManager)              iOS (All Players)
    │                                  │
    │  ===== Opening Phase (300s) ==== │
    │  WS: phase.started               │
    │  {type: opening}                 │
    │─────────────────────────────────→│
    │                                  │  自己紹介画面
    │  WS: speech.request              │  発言ボタンで自己紹介
    │←─────────────────────────────────│
    │  WS: speech.granted              │
    │─────────────────────────────────→│
    │                                  │
    │  WS: speech.ai                   │
    │─────────────────────────────────→│  AI も一人称で自己紹介
    │                                  │
    │  [時間切れ or advance]           │
    │  WS: phase.ended                 │
    │─────────────────────────────────→│  フェーズ遷移UI表示
```

**ポイント**:
- AI発言は「私は〇〇です」と一人称視点で自己紹介（推理禁止）
- 発言ボタンは画面下部に常時表示
- 手帳を開いたままでも発言可能

## 4. フェーズサイクルシーケンス

1ターン = planning → investigation → discussion

### フェーズ遷移UI

全フェーズ遷移で `phase.ended` 受信時に即座にオーバーレイ表示:
- 次フェーズ名・ターン数・ガイド・制限時間
- LLM処理中はスピナー表示
- `phase.started` 受信後3秒で自動消去

```
Server (PhaseManager)              iOS (All Players)
    │                                  │
    │  ===== Planning Phase =====      │
    │  WS: phase.started               │
    │  {type: planning, turn: 1/3}     │
    │─────────────────────────────────→│
    │                                  │  マップ表示 + 場所選択
    │  WS: phase.timer (10秒毎)        │
    │─────────────────────────────────→│
    │                                  │
    │  WS: investigate.select          │
    │←─────────────────────────────────│  場所決定
    │  WS: location.colocated          │
    │─────────────────────────────────→│  同室者表示
    │                                  │
    │  [時間切れ or advance]           │
    │  未選択者にランダム場所割当      │
    │  WS: phase.ended                 │
    │─────────────────────────────────→│  遷移UI表示（スピナー）
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
    │─────────────────────────────────→│  遷移UI表示
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
    │←─────────────────────────────────│  発言権要求(割り込み可)
    │  WS: speech.granted              │
    │─────────────────────────────────→│  録音開始
    │  WS: speech.release              │
    │←─────────────────────────────────│  発言終了+文字起こし
    │  WS: speech.released             │
    │─────────────────────────────────→│  発言履歴に追加(アバター付き)
    │                                  │
    │  WS: evidence.reveal             │
    │←─────────────────────────────────│  証拠公開(提出済みは除外)
    │  WS: evidence.revealed           │
    │─────────────────────────────────→│  全員に公開(アバター付き)
    │                                  │
    │  [時間切れ]                       │
    │  議論記録を手帳に自動保存        │
    │  WS: phase.ended                 │
    │─────────────────────────────────→│
    │                                  │
    │  ── ターン2, 3 も同様 ──         │
```

## 5. 投票・エンディングシーケンス

```
Server (PhaseManager)              iOS (All Players)
    │                                  │
    │  ===== Voting Phase =====        │
    │  WS: phase.started               │
    │  {type: voting}                  │
    │─────────────────────────────────→│  投票画面(アバター付き)
    │                                  │  + 発言ボタン
    │  WS: speech.request              │
    │←─────────────────────────────────│  最後の主張
    │                                  │
    │  WS: vote.submit                 │
    │←─────────────────────────────────│  犯人投票
    │  WS: vote.cast                   │
    │─────────────────────────────────→│  投票済み表示
    │                                  │
    │  [全員投票完了]                   │
    │  ※タイマーでは自動進行しない     │
    │  WS: vote.results                │
    │─────────────────────────────────→│
    │                                  │
    │  WS: phase.ended                 │
    │─────────────────────────────────→│  「結果発表」遷移UI
    │                                  │
    │  generate_ending() → LLM         │
    │  + スコア計算 + 投票集計          │
    │                                  │
    │  WS: game.ending                 │
    │  {ending_text, true_criminal_id, │
    │   objective_results, rankings,   │
    │   vote_details, vote_counts,     │
    │   arrested_name,                 │
    │   character_reveals}             │
    │─────────────────────────────────→│  screen=ended
```

### エンディング画面の構成

#### シーン1: ドラマチックリビール（黒背景、4秒）
```
[アバター]
〇〇は・・・・
```

#### シーン2: 判定（5秒）
```
[アバター]
犯人でした / 冤罪でした
真犯人を見事に見抜きました / 無実の人が監禁されてしまいました...
```

#### エンディング画面（スクロール）
1. **投票結果** — 誰に何票。最多票に「監禁」マーク
2. **エピローグ** — LLM生成。監禁→真相解明→結末
   - 犯人当て: 告白・動機・トリック
   - 冤罪: 後味の悪い結末。真犯人の冷笑、残された者の後悔
3. **最終スコア** — ランキング(🥇🥈🥉)。発言×1pt + 証拠×3pt
4. **個人目的の達成状況** — アバター + ○/× + 説明
5. **ネタバラシ** — 全キャラの役割・秘密を公開
6. **「もう一度見る」/ 「ホームに戻る」** ボタン

## 6. ホスト操作

| 操作 | WS メッセージ | 効果 |
|------|-------------|------|
| フェーズ進行 | `phase.advance` | 即座に次フェーズへ |
| フェーズ延長 | `phase.extend` | +60秒 |
| 一時停止 | `phase.pause` | タイマー停止 |
| 再開 | `phase.resume` | タイマー再開 |

## 7. ルーム再参加

```
iOS                     Server
  │  POST /join           │
  │  (X-Device-Id)        │
  │──────────────────────→│
  │                       │  device_id で既存 Player 検索
  │                       │  → 存在: session_token 更新、既存 Player 返却
  │                       │  → 不在 & waiting: 新規 Player 作成
  │                       │  → 不在 & started: エラー
  │  200 OK               │
  │←──────────────────────│
  │                       │
  │  WS 接続              │
  │──────────────────────→│
  │                       │  WS: game.state (現在の状態)
  │                       │──→ screen 復帰
```

## 8. WebSocket メッセージ一覧

### サーバー → クライアント

| type | data | 用途 |
|------|------|------|
| `game.generating` | `{room_code}` | シナリオ生成開始 |
| `game.ready` | `{room_code}` | ゲーム準備完了 |
| `game.generation_failed` | `{room_code}` | 生成失敗→ロビー復帰 |
| `game.state` | (後述) | ゲーム全状態(プレイヤー個別) |
| `game.ending` | `{ending_text, true_criminal_id, objective_results, rankings, vote_details, vote_counts, arrested_name, character_reveals}` | エンディング |
| `progress` | `{step, status}` | 生成進捗 |
| `phase.started` | `{phase_id, phase_type, duration_sec, turn_number, total_turns, investigation_locations}` | フェーズ開始 |
| `phase.timer` | `{remaining_sec}` | タイマー (10秒毎) |
| `phase.ended` | `{phase_type, next_phase_type}` | フェーズ終了→遷移UI |
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
| `speech.released` | `{player_id, character_name, transcript}` | 発言終了 |
| `speech.ai` | `{player_id, character_name, transcript}` | AI発言 |
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
| `speech.request` | - | 発言権要求(割り込み可) |
| `speech.release` | `{transcript}` | 発言終了 |
| `evidence.reveal` | `{evidence_id}` | 証拠公開 |
| `vote.submit` | `{suspect_player_id}` | 犯人投票 |
| `room_message.send` | `{text}` | ルームチャット送信 |
| `phase.advance` | - | フェーズ進行 (ホスト) |
| `phase.extend` | - | フェーズ延長 (ホスト) |
| `phase.pause` | - | 一時停止 (ホスト) |
| `phase.resume` | - | 再開 (ホスト) |

## 9. game.state データ構造

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

## 10. フェーズ時間設定

| フェーズ | デフォルト時間 | 説明 |
|---------|-------------|------|
| initial | 0秒 | 自動スキップ |
| opening | 300秒 (5分) | 自己紹介 + 状況共有 |
| planning | 180秒 (3分) | 場所選択 + 会話 |
| investigation | 120秒 (2分) | 調査実行 |
| discussion | 300秒 (5分) | 議論 + 証拠公開 |
| voting | 180秒 (3分) | 犯人投票(自動進行しない) |

1ターン合計: 10分。自己紹介(5分) + 3ターン(30分) + 投票(3分) = 約38分。

## 11. LLM 呼び出しポイント

| タイミング | 関数 | モデル | 用途 |
|-----------|------|--------|------|
| ゲーム開始 | `generate_scenario()` | gpt-5.4-mini | シナリオ全体生成 |
| AI補充時 | `_generate_ai_character()` | gpt-5.4-nano | AIキャラ動的生成 |
| investigation 開始 | `investigate_location()` | gpt-5.4-nano | 各 feature の発見生成 |
| investigate.tamper | `tamper_evidence()` | gpt-5.4-nano | 証拠改ざん |
| discussion 開始 | `adjust_phase()` | gpt-5.4-nano | 追加証拠配布 |
| AI発言 | `generate_ai_speech()` | gpt-5.4-nano | フェーズ別AI発言 |
| 全員投票後 | `generate_ending()` | gpt-5.4-mini | エンディング生成 |

コスト上限: $2.00 / ゲーム
JSON修復: `json-repair` ライブラリで壊れたLLM出力を自動修復

## 12. エンディングテンプレート構成

1. **監禁**: 最多票キャラが監禁される描写
2. **真相解明**: 犯人当て→告白 / 冤罪→真犯人逃走（後味悪い結末）
3. **各キャラのその後**: 事件後の運命

ending_text は最低15文以上。
