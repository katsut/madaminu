# アーキテクチャ v3

## 設計原則

1. **全状態は DB に永続化** — メモリ内状態ゼロ。サーバー再起動でゲームが壊れない
2. **HTTP でアクション、WS で通知** — 役割を明確に分離
3. **フォールバック禁止** — 正規の処理が確実に動く設計にする
4. **不要な try-catch 禁止** — 起きるはずのない例外は握りつぶさない
5. **LLM は API をブロックしない** — バックグラウンドで実行、結果は DB に保存

---

## ゲームフェーズ

### フェーズ一覧

| # | フェーズ | 時間 | 内容 | 遷移画面メッセージ |
|---|---------|------|------|------------------|
| 1 | initial | 0秒 | 初期証拠・アリバイ配布 | (なし) |
| 2 | storytelling | 3分 | 指名されたプレイヤーがシナリオを読み上げ | 「物語の始まり」「〇〇さん、ストーリーを読み上げてください」 |
| 3 | opening | 人数×1分 | 自己紹介 | 「自己紹介タイム」「まずはお互いを知りましょう」 |
| 4 | discussion | 3分 | 議論・証拠公開 | 「議論」「集めた情報をもとに推理を話し合いましょう」 |
| 5 | planning | 2分 | 調査場所選択 | 「調査計画」「みんなで相談して、次に調べる場所を決めましょう」 |
| 6 | investigation | 2分 | 調査・証拠保持 | 「調査」「選んだ場所で手がかりを探しましょう」 |
| | *(4→5→6 を3ターン)* | | | |
| 7 | voting | 5分 | 最終議論＆投票 | 「最終議論 & 投票」「最後の議論と投票です。犯人だと思う人物を選んでください」 |
| 8 | ending | — | 結果発表・エピローグ | 「結果発表」「投票結果とエピローグを生成中です...」 |

### フロー

```
initial → storytelling → opening → [discussion → planning → investigation] × 3 → voting → ending
```

### generating 画面（シナリオ生成中）に表示するフェーズガイド

| # | フェーズ | やること |
|---|---------|---------|
| 1 | 📖 物語の読み上げ | 指名された人がストーリーを声に出して読み上げる |
| 2 | 🤝 自己紹介 | 発言ボタンを押して自分のキャラクターを紹介する |
| 3 | 💬 議論 | 情報を共有し、推理を話し合う。証拠カードを公開できる |
| 4 | 🗺️ 調査計画 | マップを見て、次に調べる場所をみんなで相談して決める |
| 5 | 🔍 調査 | 選んだ場所を調べる。発見物から1つだけ持ち帰れる |
| | *3→4→5 を3回繰り返し* | |
| 6 | 🗳️ 最終議論 & 投票 | 最後の話し合いをして、犯人だと思う人に投票する |
| 7 | 📜 結果発表 | 真相が明かされる |

### 各フェーズ詳細

#### initial（0秒・自動スキップ）
- サーバーがシナリオ生成完了後、初期証拠・アリバイをプレイヤーに配布
- DB: Evidence（source=gm_push）を各プレイヤーに作成
- 即座に storytelling へ遷移

#### storytelling（3分）
- 人間プレイヤーからランダムに1人を指名
- 画面にシナリオテキスト（舞台・状況・被害者）を大きく表示
- 「〇〇さん、読み上げてください」と表示
- 発言ボタンはなし（読み上げのみ）
- 他プレイヤーは聞いている。手帳は開ける

#### opening（人数×1分）
- 発言ボタンで自己紹介
- AI も一人称で自己紹介（推理はしない）
- 手帳で自分の情報を確認

#### discussion（3分）
- タイムライン表示（発言+証拠公開、タイムスタンプ順、新しい順）
- 発言ボタンで推理・意見を述べる
- 証拠カードを公開できる（3pt）
- 口頭発言（1pt）
- AI は推理・質問・証拠に基づく主張
- 提出済みの証拠は除外

#### planning（2分）
- マップ（SVG）と場所一覧を表示
- 場所を1つ選択（POST /select-location）
- 発言ボタンで場所について相談可能
- 未選択者は制限時間切れ時にランダム割り当て

#### investigation（2分）
- 遷移時にバックグラウンドで discoveries 一括生成（LLM 1回/プレイヤー、並列）
- 生成完了まで「準備中...」表示
- 生成完了後、feature 一覧をタップ可能なカードで表示
- タップで調査結果を展開
- 1つだけ持ち帰れる（POST /keep-evidence）
- 同じ場所に他プレイヤーがいなければ1つ改ざん可能
- 同室プレイヤー同士でヒソヒソチャット

#### voting（5分）
- プレイヤー一覧（アバター付き）と投票ボタン
- 発言ボタンで最後の議論も可能
- 投票状況「N/M 人投票済み」を表示（AI除外）
- 遷移条件: 制限時間切れ **or** 全人間プレイヤーの投票完了
- AI は最後の主張

#### ending
- ドラマチックリビール: 「〇〇は・・・」(4秒) → 「犯人/冤罪でした」(5秒)
- 投票結果: 誰に何票。最多票に「監禁」マーク
- 第1幕（表のエンディング）: 監禁シーン、各キャラのその後
- 第2幕（犯人視点エピローグ）: 犯人の一人称で真相を語る
- スコア: ランキング形式（🥇🥈🥉）
- 個人目的: 達成/未達成
- ネタバラシ: 全キャラの秘密・役割公開
- 「もう一度見る」「ホームに戻る」

---

## シーン切り替え制御

### クライアントの状態

```
enum PhaseScreenState {
    case active(phase)      // フェーズ画面を表示中
    case transitioning      // 遷移画面を表示中（サーバー処理待ち）
}
```

### 遷移トリガーは2つだけ

| トリガー | 発生条件 | 処理 |
|---------|---------|------|
| **自分が advance** | ローカルタイマー0 or ホストが進行ボタン | POST /advance → レスポンスで遷移 |
| **他人が advance** | WS で game.state 受信 → phase_id が変わっている | 差分検出で遷移 |

### トリガー1: 自分が advance

```
1. ローカルタイマーが0になる
2. state = .transitioning（遷移画面を表示）
3. POST /advance を送信
4. レスポンスを受信:
   - "advanced" → 新フェーズ情報あり
     - discoveries_status == "generating" → 遷移画面を維持（スピナー表示）
     - それ以外 → 遷移画面を3秒表示 → state = .active(newPhase)
   - "already_advanced" → 他クライアントが先に遷移済み
     - 遷移画面を3秒表示 → state = .active(currentPhase)
   - "not_expired" → まだ早い（クロックずれ）
     - state = .active(currentPhase)（現フェーズに戻る、タイマー補正）
```

### トリガー2: 他人が advance（WS で game.state 受信）

```
1. WS で game.state を受信
2. server.current_phase.id ≠ local.current_phase.id ?
   - YES → state = .transitioning → 遷移画面3秒表示 → state = .active(newPhase)
   - NO → タイマー等の差分だけ更新
```

### 遷移画面の表示仕様

| 状態 | 表示内容 |
|------|---------|
| advance レスポンス待ち | フェーズ名 + メッセージ + スピナー |
| 次フェーズ確定（investigation 以外） | フェーズ名 + メッセージ + 制限時間 → 3秒後に自動消去 |
| 次フェーズ確定（investigation、生成中） | 「調査」+「準備中...」+ スピナー |
| discoveries 生成完了（WS で通知） | 「調査」+ メッセージ + 制限時間 → 3秒後に自動消去 |

### investigation の discoveries 待ち

```
遷移画面表示中（state = .transitioning）
  → WS で game.state 受信
  → discoveries_status == "ready"
  → 遷移画面を3秒表示 → state = .active(investigation)
  → GET /discoveries で feature 一覧取得
```

### WS 再接続時

```
新しい WS 接続が確立
  → サーバーが自動的に game.state を送信（現行通り）
  → クライアントが受信
  → local.current_phase.id と比較
  → 違っていたら遷移画面を表示 → state = .active(newPhase)
```

フォールバックではない。WS 接続確立時の正規プロトコル。

### シーケンス図: 通常のフェーズ遷移

```
Client A (タイマー切れ)        Server              Client B
    │                           │                     │
    │ state = .transitioning    │                     │
    │ 遷移画面表示              │                     │
    │                           │                     │
    │ POST /advance             │                     │
    │──────────────────────────→│                     │
    │                           │ DB: discussion.ended_at = now
    │                           │ DB: planning.started_at = now
    │                           │ DB: planning.deadline_at = now+120s
    │                           │                     │
    │  {result: "advanced",     │                     │
    │   phase: {planning, 120s}}│                     │
    │←──────────────────────────│                     │
    │                           │                     │
    │ 遷移画面: 「調査計画」    │                     │
    │ 3秒表示                   │                     │
    │ state = .active(planning) │                     │
    │                           │ WS: game.state      │
    │                           │────────────────────→│
    │                           │                     │ phase_id が違う
    │                           │                     │ state = .transitioning
    │                           │                     │ 遷移画面: 「調査計画」
    │                           │                     │ 3秒表示
    │                           │                     │ state = .active(planning)
```

### シーケンス図: investigation 遷移（LLM 生成あり）

```
Client A                       Server              Client B
    │                           │                     │
    │ POST /advance             │                     │
    │──────────────────────────→│                     │
    │                           │ DB: planning → investigation
    │                           │ DB: discoveries_status = 'generating'
    │                           │ create_task(generate_discoveries)
    │                           │                     │
    │  {result: "advanced",     │                     │
    │   phase: {investigation,  │                     │
    │   discoveries_status:     │                     │
    │   "generating"}}          │                     │
    │←──────────────────────────│                     │
    │                           │                     │
    │ 遷移画面維持（準備中）    │                     │
    │                           │ WS: game.state      │
    │                           │────────────────────→│
    │                           │                     │ 遷移画面（準備中）
    │                           │                     │
    │                           │     [LLM処理 3-5秒] │
    │                           │                     │
    │                           │ DB: discoveries保存  │
    │                           │ DB: status = 'ready' │
    │                           │                     │
    │ WS: game.state            │ WS: game.state      │
    │ (discoveries_status=ready)│ (discoveries_status=ready)
    │←──────────────────────────│────────────────────→│
    │                           │                     │
    │ 遷移画面3秒表示           │                     │
    │ state = .active           │                     │
    │ GET /discoveries          │                     │
    │──────────────────────────→│                     │
    │ [{feature, title, ...}]   │                     │
    │←──────────────────────────│                     │
    │ feature一覧表示           │                     │
```

### 排他制御: 複数クライアントが同時に advance

```sql
UPDATE phases SET ended_at = NOW()
WHERE id = :current_phase_id AND ended_at IS NULL
```

1行更新 → 遷移成功。0行更新 → 他クライアントが先に遷移済み → 現在フェーズを返す。

---

## 通信設計

### HTTP API — ユーザーアクション

| アクション | メソッド | パス |
|-----------|--------|------|
| ルーム作成 | POST | /rooms |
| ルーム参加 | POST | /rooms/{code}/join |
| キャラクター作成 | POST | /rooms/{code}/characters |
| 準備完了 | POST | /rooms/{code}/ready |
| ゲーム開始 | POST | /rooms/{code}/start |
| イントロ準備完了 | POST | /rooms/{code}/intro-ready |
| 場所選択 | POST | /rooms/{code}/select-location |
| 証拠保持 | POST | /rooms/{code}/keep-evidence |
| 証拠改ざん | POST | /rooms/{code}/tamper-evidence |
| 証拠公開 | POST | /rooms/{code}/reveal-evidence |
| 発言開始 | POST | /rooms/{code}/speech/request |
| 発言終了 | POST | /rooms/{code}/speech/release |
| 投票 | POST | /rooms/{code}/vote |
| フェーズ進行 | POST | /rooms/{code}/advance |
| フェーズ延長 | POST | /rooms/{code}/extend |
| 一時停止/再開 | POST | /rooms/{code}/pause, /resume |
| 状態取得 | GET | /rooms/{code}/state |
| discoveries 取得 | GET | /rooms/{code}/discoveries |

### WS — サーバーからの通知

| 通知 | データ | 用途 |
|------|--------|------|
| `game.state` | (フルステート) | フェーズ変更時・接続時に送信 |
| `speech` | `{player_id, character_name, transcript}` | 誰かが発言した |
| `evidence_revealed` | `{player_id, player_name, title, content}` | 誰かが証拠を公開した |
| `vote_cast` | `{voted_count, total_human}` | 誰かが投票した |

WS 接続確立時にサーバーが `game.state` を自動送信。フェーズ変更時も `game.state` を全クライアントに送信。クライアントは `game.state` の差分でシーン切り替えを判断。

### WS 接続維持

- サーバーが **20秒間隔で ping** を送信
- 切断検知 → クライアントが指数バックオフで再接続
- 再接続時 → サーバーが `game.state` を自動送信

---

## データ管理

### 廃止するメモリ内状態

| データ | v2 | v3 |
|--------|-----|-----|
| タイマー | asyncio.Task | 廃止。DB の deadline_at のみ |
| investigation_selections | PhaseManager dict | DB テーブル |
| discoveries | PhaseManager dict | DB（Evidence, source=discovery） |
| intro_ready | PhaseManager set | DB（players.is_intro_ready） |
| current_speaker | SpeechManager dict | DB（phases.current_speaker_id） |
| _advancing_rooms | handler set | DB 排他制御に置換 |
| _paused | PhaseManager dict | DB（phases.paused_remaining_sec） |

### 新テーブル: investigation_selections

```sql
CREATE TABLE investigation_selections (
    id VARCHAR PRIMARY KEY,
    game_id VARCHAR NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    phase_id VARCHAR NOT NULL REFERENCES phases(id) ON DELETE CASCADE,
    player_id VARCHAR NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    location_id VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (phase_id, player_id)
);
```

### Phase テーブル拡張

```sql
ALTER TABLE phases ADD COLUMN paused_remaining_sec INTEGER;
ALTER TABLE phases ADD COLUMN current_speaker_id VARCHAR REFERENCES players(id);
ALTER TABLE phases ADD COLUMN discoveries_status VARCHAR DEFAULT 'pending';
-- discoveries_status: 'pending' | 'generating' | 'ready'
```

### Player テーブル拡張

```sql
ALTER TABLE players ADD COLUMN is_intro_ready BOOLEAN DEFAULT FALSE;
```

### PhaseType 拡張

```python
class PhaseType(StrEnum):
    initial = "initial"
    storytelling = "storytelling"  # NEW
    opening = "opening"
    planning = "planning"
    investigation = "investigation"
    discussion = "discussion"
    voting = "voting"
```

---

## LLM 呼び出し

### 原則

LLM 呼び出しは HTTP API をブロックしない。DB セッションは LLM 呼び出し中に保持しない。

```
generate_discoveries:
  1. DB からプレイヤー・場所情報を取得 → DB セッション閉じる
  2. LLM 呼び出し（並列、DB セッション不要）
  3. 結果を DB に保存 → DB セッション閉じる
  4. Phase.discoveries_status = 'ready' に更新
  5. WS で game.state を全クライアントに送信
```

---

## 廃止対象（v2 の負債）

### 不要なフォールバック
- `_check_and_advance_expired_phase` — WS メッセージ受信時の期限チェック
- `pollGameState` — iOS のタイマー後 HTTP ポーリング
- `fetchDiscoveriesHTTP` — discoveries の HTTP ポーリング
- `Force dismissing stale transition overlay` — 30秒後の強制非表示
- `_restore_active_timers` — サーバー起動時のタイマー復元

### 不要な try-catch
- advance_phase 内の全例外握りつぶし
- discoveries 生成の `return_exceptions=True`

### 廃止するクラス
- **PhaseManager** → `GameService`（DB操作のみ）
- **SpeechManager** → `SpeechService`（DB操作のみ）

---

## 移行計画

### Phase 1: DB スキーマ拡張
- investigation_selections テーブル作成
- phases テーブル拡張（paused_remaining_sec, current_speaker_id, discoveries_status）
- players テーブル拡張（is_intro_ready）
- PhaseType に storytelling 追加
- マイグレーション作成

### Phase 2: サービス層書き換え
- GameService 作成（PhaseManager 置換、DB操作のみ）
- SpeechService 作成（SpeechManager 置換、DB操作のみ）

### Phase 3: HTTP API 追加
- POST /advance（排他制御付き）
- POST /select-location
- POST /speech/request, /speech/release
- POST /reveal-evidence
- POST /vote
- GET /state 拡充（discoveries_status 含む）

### Phase 4: WS 簡略化
- WS handler を game.state 送信 + 通知のみに縮小
- サーバー側 ping/pong 追加（20秒間隔）
- フェーズ変更時に game.state を全クライアントに自動送信

### Phase 5: iOS クライアント書き換え
- 全アクションを HTTP API に切り替え
- WS は game.state 受信 → 差分でシーン切り替え
- PhaseScreenState（active / transitioning）実装
- ポーリング・フォールバック全削除

### Phase 6: クリーンアップ
- PhaseManager, SpeechManager 削除
- フォールバック処理削除
- 不要な try-catch 削除
- テスト全面更新
