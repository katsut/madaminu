# アーキテクチャ v3

## 設計原則

1. **全状態は DB に永続化** — メモリ内状態ゼロ。サーバー再起動でゲームが壊れない
2. **HTTP でアクション、WS で通知** — 役割を明確に分離
3. **フォールバック禁止** — 正規の処理が確実に動く設計にする
4. **不要な try-catch 禁止** — 起きるはずのない例外は握りつぶさない
5. **LLM は API をブロックしない** — バックグラウンドで実行、結果は DB に保存

---

## 通信設計

### HTTP API — ユーザーアクション

ユーザーが意図的に行う操作はすべて HTTP。レスポンスで成否がわかる。

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

WS は「何か変わったのでUIを更新してください」という通知のみ。**WS が届かなくてもゲームは止まらない**。なぜなら：

- フェーズ遷移はクライアントの HTTP リクエストで発火する
- 自分のアクション結果は HTTP レスポンスで受け取る
- WS が届かないと遅延するのは「他プレイヤーの発言が見えるタイミング」だけ

| 通知 | データ | 用途 |
|------|--------|------|
| `phase_changed` | `{phase_type, deadline_at}` | フェーズが変わった（他プレイヤーが advance した場合） |
| `speech` | `{player_id, character_name, transcript}` | 誰かが発言した |
| `evidence_revealed` | `{player_id, player_name, title, content}` | 誰かが証拠を公開した |
| `vote_cast` | `{voted_count, total_human}` | 誰かが投票した |
| `discoveries_ready` | `{}` | discoveries 生成完了 |
| `player_joined` | `{player_id}` | プレイヤー参加/切断 |
| `game_ending` | `{}` | エンディング生成完了 |

WS メッセージにはデータを最小限含める。詳細が必要ならクライアントが HTTP で取得する。

### WS 接続維持

- サーバーが **20秒間隔で ping** を送信（Railway の10分アイドルタイムアウト対策）
- クライアントが **pong を返す**（URLSessionWebSocketTask は自動で返す）
- 切断検知 → クライアントが指数バックオフで再接続
- 再接続成功 → `GET /state` で最新状態を取得（再接続プロトコルの正規手順）

---

## フェーズ遷移

### 設計

```
クライアントのローカルタイマーが0になる
  → POST /rooms/{code}/advance
  → サーバーが deadline_at を確認
  → 期限切れなら DB を更新して次フェーズに遷移
  → レスポンスで新フェーズ情報を返す
  → 全クライアントに WS で phase_changed を通知
```

### なぜこの設計か

- サーバー側タイマー（asyncio.Task）は再起動で消える → 廃止
- WS push は切断で届かない → クライアントが HTTP で遷移をリクエスト
- 複数クライアントが同時に advance → DB の排他制御で1回だけ遷移

### 排他制御

```sql
-- 現在のフェーズを終了（他のクライアントが先に終了していたら0行更新）
UPDATE phases
SET ended_at = NOW()
WHERE id = :current_phase_id AND ended_at IS NULL
```

更新が0行 → 他のクライアントが先に遷移済み → 現在のフェーズ情報を返す。

### advance API

```
POST /rooms/{code}/advance

Request: (empty body, or {"force": true} for host)

Response (遷移成功):
{
  "result": "advanced",
  "phase": {
    "id": "...",
    "phase_type": "planning",
    "duration_sec": 120,
    "deadline_at": "2026-03-31T10:02:00Z",
    "turn_number": 1,
    "total_turns": 3
  }
}

Response (既に遷移済み):
{
  "result": "already_advanced",
  "phase": { ... current phase ... }
}

Response (まだ期限前):
{
  "result": "not_expired",
  "remaining_sec": 45
}
```

### investigation フェーズへの遷移

investigation フェーズは LLM 呼び出しが必要。遷移自体は即座に完了し、LLM はバックグラウンドで実行。

```
POST /advance
  → planning を終了、investigation を開始（DB更新、即座に返る）
  → レスポンスで「investigation 開始、discoveries は生成中」
  → バックグラウンドで LLM 呼び出し → 結果を DB に保存
  → WS で discoveries_ready を通知
  → クライアントが GET /discoveries で取得
```

クライアントは investigation フェーズに入ったら：
1. 「準備中...」を表示
2. WS の `discoveries_ready` を待つ
3. 受信したら `GET /discoveries` で取得して feature 一覧を表示

WS が切れていた場合：
- クライアントの再接続時に `GET /state` → discoveries が含まれている → 表示
- これはフォールバックではなく、再接続プロトコルの正規手順

---

## データ管理

### 廃止するメモリ内状態

| データ | 現在の保存先 | v3 |
|--------|------------|-----|
| タイマー | asyncio.Task | 廃止。deadline_at のみ |
| investigation_selections | PhaseManager dict | DB テーブル |
| discoveries | PhaseManager dict | DB（Evidence, source=discovery） |
| intro_ready | PhaseManager set | DB（players.is_intro_ready） |
| current_speaker | SpeechManager dict | DB（phases.current_speaker_id） |
| _timers | PhaseManager dict | 廃止 |
| _advancing_rooms | handler set | DB 排他制御に置換 |
| _paused | PhaseManager dict | DB（phases.paused_remaining_sec） |

### 新テーブル

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

### 廃止するクラス

- **PhaseManager** → `GameService`（DB操作のみ、メモリ状態なし）
- **SpeechManager** → `SpeechService`（DB操作のみ）

---

## LLM 呼び出し

### 原則

LLM 呼び出しは HTTP API をブロックしない。

```
advance API
  → DB を更新（即座）
  → asyncio.create_task(generate_discoveries(...))
  → レスポンスを返す

generate_discoveries:
  1. DB からプレイヤー・場所情報を取得 → DB セッション閉じる
  2. LLM 呼び出し（並列、DB セッション不要）
  3. 結果を DB に保存 → DB セッション閉じる
  4. Phase.discoveries_status = 'ready' に更新
  5. WS で discoveries_ready を通知
```

ポイント: **LLM 呼び出し中は DB セッションを保持しない**。

### discoveries 生成フロー（シーケンス図）

```
Client              Server                LLM
  |                    |                    |
  | POST /advance      |                    |
  |───────────────────→|                    |
  |                    | DB: phase → investigation
  |                    | DB: discoveries_status = 'generating'
  |  {phase: investigation, discoveries_status: 'generating'}
  |←───────────────────|                    |
  |                    |                    |
  | 画面: 「準備中...」 |                    |
  |                    | create_task(generate)
  |                    |───────────────────→|
  |                    |                    | LLM processing...
  |                    |                    |
  |                    |  discoveries result |
  |                    |←───────────────────|
  |                    | DB: save evidences  |
  |                    | DB: status = 'ready'|
  |                    |                    |
  | WS: discoveries_ready                   |
  |←───────────────────|                    |
  |                    |                    |
  | GET /discoveries   |                    |
  |───────────────────→|                    |
  | [{feature, title, content}, ...]        |
  |←───────────────────|                    |
  |                    |                    |
  | 画面: feature一覧  |                    |
```

---

## iOS クライアント設計

### 状態管理

```
GameStateManager (ObservableObject)
  → HTTP でアクション送信
  → HTTP レスポンスで自分の状態を更新
  → WS 通知で他プレイヤーの変更を検知
  → WS 通知受信時に必要なら GET /state で詳細取得
  → WS 再接続時に GET /state で全状態復元
```

### タイマー管理

```swift
// ローカルタイマー
// deadline_at は HTTP レスポンスまたは GET /state から取得
func startLocalTimer(deadline: Date) {
    timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { _ in
        let remaining = deadline.timeIntervalSinceNow
        localRemainingSec = max(0, Int(remaining))
        if remaining <= 0 {
            timer?.invalidate()
            advancePhase() // POST /advance
        }
    }
}

func advancePhase() {
    Task {
        let result = await api.advance(roomCode: roomCode)
        switch result {
        case .advanced(let phase):
            applyPhaseTransition(phase)
            startLocalTimer(deadline: phase.deadlineAt)
        case .alreadyAdvanced(let phase):
            applyPhaseTransition(phase)
            startLocalTimer(deadline: phase.deadlineAt)
        case .notExpired(let remaining):
            // まだ早い（サーバーとのクロックずれ）
            localRemainingSec = remaining
        }
    }
}
```

### WS 再接続

```swift
func onWebSocketReconnected() {
    // 正規手順: 最新状態を HTTP で取得
    Task {
        let state = await api.getState(roomCode: roomCode)
        applyFullState(state)
    }
}
```

これはフォールバックではない。WS は通知チャネルであり、状態のソースは常に HTTP API。

---

## 削除対象（v2 の負債）

### 不要なフォールバック
- `_check_and_advance_expired_phase` — WS メッセージ受信時の期限チェック
- `pollGameState` — iOS のタイマー後 HTTP ポーリング
- `fetchDiscoveriesHTTP` — discoveries の HTTP ポーリング
- `Force dismissing stale transition overlay` — 30秒後の強制非表示
- `_restore_active_timers` — サーバー起動時のタイマー復元

### 不要な try-catch
- advance_phase 内の `except Exception: logger.exception(...)` で全例外を握りつぶしている箇所
- `_generate_room_discoveries` の外側で `return_exceptions=True` にして例外を無視している箇所

### 廃止するクラス
- `PhaseManager` — メモリ内状態管理を全廃。DB 操作の `GameService` に置換
- `SpeechManager` — 同上。`SpeechService` に置換

---

## 移行計画

### Phase 1: DB スキーマ拡張
- investigation_selections テーブル作成
- phases テーブルに paused_remaining_sec, current_speaker_id, discoveries_status 追加
- players テーブルに is_intro_ready 追加
- マイグレーション作成

### Phase 2: サービス層書き換え
- GameService 作成（PhaseManager 置換）
- SpeechService 作成（SpeechManager 置換）
- 全操作が DB ベースに

### Phase 3: HTTP API 追加
- POST /advance（排他制御付き）
- POST /select-location
- POST /speech/request, /speech/release
- POST /reveal-evidence
- POST /vote
- GET /state 拡充

### Phase 4: WS 簡略化
- WS handler を通知送信のみに縮小
- サーバー側 ping/pong 追加
- WS メッセージからデータを最小化

### Phase 5: iOS クライアント書き換え
- 全アクションを HTTP API に切り替え
- WS は通知受信のみ
- ポーリング・フォールバック削除
- 再接続プロトコル実装

### Phase 6: クリーンアップ
- PhaseManager, SpeechManager 削除
- フォールバック処理削除
- 不要な try-catch 削除
- テスト全面更新
