# アーキテクチャ v3

## 設計原則

1. **全状態は DB に永続化** — メモリ内状態ゼロ。サーバー再起動でゲームが壊れない
2. **WS でゲーム通信、HTTP はゲーム外操作** — 役割を明確に分離
3. **フォールバック禁止** — 根本原因を修正する。別経路で誤魔化さない
4. **不要な try-catch 禁止** — 起きるはずのない例外は握りつぶさない
5. **LLM は WS をブロックしない** — バックグラウンドで実行、結果は DB に保存
6. **サーバーはバリデーションを都度行う** — 同じメッセージが2回来ても安全

---

## 通信設計

### HTTP — ゲーム外操作

WS 接続前、またはゲーム外のリソース取得に使用。

| 操作 | メソッド | パス |
|------|--------|------|
| ルーム作成 | POST | /rooms |
| ルーム参加 | POST | /rooms/{code}/join |
| ルーム一覧 | GET | /rooms |
| ルーム詳細 | GET | /rooms/{code} |
| キャラクター作成 | POST | /rooms/{code}/characters |
| 準備完了 | POST | /rooms/{code}/ready |
| ゲーム開始 | POST | /rooms/{code}/start |
| 画像取得 | GET | /images/... |
| マップ SVG | GET | /images/game/{code}/map |
| ゲーム状態取得 | GET | /rooms/{code}/state |
| discoveries 取得 | GET | /rooms/{code}/discoveries |

### WS — ゲーム中の全通信

ゲーム開始後の全操作は WS で行う。送信も受信も WS。

#### クライアント → サーバー（アクション）

| メッセージ | データ | フェーズ |
|-----------|--------|---------|
| `intro.ready` | — | イントロ |
| `advance` | `{force?: bool}` | 全フェーズ |
| `select_location` | `{location_id}` | planning |
| `keep_evidence` | `{discovery_id}` | investigation |
| `tamper_evidence` | `{discovery_id}` | investigation |
| `reveal_evidence` | `{evidence_id}` | discussion |
| `speech.request` | — | storytelling/opening/discussion/voting |
| `speech.release` | `{transcript}` | storytelling/opening/discussion/voting |
| `vote` | `{suspect_player_id}` | voting |
| `room_message` | `{text}` | investigation（同室チャット） |

#### サーバー → クライアント（通知）

| メッセージ | データ | タイミング |
|-----------|--------|-----------|
| `game.state` | フルステート | 接続時、フェーズ変更時、状態変更時 |
| `speech` | `{player_id, character_name, transcript}` | 発言終了時 |
| `speech.granted` | `{player_id}` | 発言権付与時 |
| `speech.active` | `{player_id}` | 発言中通知 |
| `evidence_revealed` | `{player_id, player_name, title, content}` | 証拠公開時 |
| `vote_cast` | `{voted_count, total_human}` | 投票時 |
| `error` | `{message}` | バリデーションエラー時 |

### game.state の役割

`game.state` はサーバーの正のデータ。以下のタイミングで送信：

1. **WS 接続確立時** — 自動送信。再接続時もこれで最新状態に復帰
2. **フェーズ変更時** — 全クライアントに送信。差分でシーン切り替え
3. **discoveries 生成完了時** — discoveries_status が ready に変わったことを通知
4. **投票完了時** — ゲーム状態が変わったことを通知

クライアントは `game.state` を受信したら、ローカル状態と比較して差分を適用する。

### WS 接続維持

- サーバーが **20秒間隔で ping** を送信
- クライアントが pong を返す（URLSessionWebSocketTask は自動）
- 切断検知 → 指数バックオフで再接続（1s, 2s, 4s, 8s, 16s, 30s）
- 再接続成功 → サーバーが `game.state` を自動送信 → クライアントが差分適用

### サーバー側バリデーション

全 WS メッセージに対してサーバーが都度バリデーション。同じメッセージが2回来ても安全。

| メッセージ | バリデーション |
|-----------|-------------|
| `advance` | `Phase.ended_at IS NULL` で排他。既に遷移済みなら `already_advanced` を返す |
| `keep_evidence` | 同フェーズ・同プレイヤーで既に keep 済みなら reject |
| `vote` | 同ゲーム・同プレイヤーで既に投票済みなら reject |
| `speech.request` | 現在の phase_type が発言可能かチェック |
| `select_location` | 現在のフェーズが planning かチェック |

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

### generating 画面に表示するフェーズガイド

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

---

## シーン切り替え制御

### クライアントの状態

```
enum PhaseScreenState {
    case active         // フェーズ画面を表示中
    case transitioning  // 遷移画面を表示中
}
```

### 遷移トリガーは2つだけ

| トリガー | 発生条件 | 処理 |
|---------|---------|------|
| **自分が advance** | ローカルタイマー0 or ホスト進行 | WS で `advance` 送信 → レスポンスで遷移 |
| **他人が advance** | WS で `game.state` 受信 → phase_id が違う | 差分検出で遷移 |

### トリガー1: 自分が advance

```
1. ローカルタイマーが0になる
2. state = .transitioning（遷移画面表示）
3. WS で advance を送信
4. サーバーからレスポンス:
   - game.state（フェーズが変わっている）
     → discoveries_status == "generating" → 遷移画面維持（スピナー）
     → それ以外 → 3秒表示 → state = .active
   - error（not_expired）
     → state = .active に戻る、タイマー補正
```

### トリガー2: 他人が advance

```
1. WS で game.state 受信
2. server.phase_id ≠ local.phase_id → state = .transitioning
3. 遷移画面3秒表示 → state = .active
```

### investigation の discoveries 待ち

```
state = .transitioning のまま
  → WS で game.state 受信
  → discoveries_status == "ready"
  → 3秒表示 → state = .active
  → GET /discoveries で feature 一覧取得
```

### 遷移画面の表示仕様

| 状態 | 表示 |
|------|------|
| advance 送信後、応答待ち | フェーズ名 + メッセージ + スピナー |
| 次フェーズ確定（investigation 以外） | フェーズ名 + メッセージ + 制限時間 → 3秒後に消去 |
| 次フェーズ確定（investigation、生成中） | 「調査」+「準備中...」+ スピナー |
| discoveries 生成完了 | 「調査」+ メッセージ + 制限時間 → 3秒後に消去 |

---

## データ管理

### 全状態を DB に永続化

| データ | v2（メモリ） | v3（DB） |
|--------|------------|---------|
| タイマー | asyncio.Task | 廃止。Phase.deadline_at のみ |
| 場所選択 | PhaseManager dict | investigation_selections テーブル |
| discoveries | PhaseManager dict | Evidence テーブル（source=discovery） |
| イントロ準備 | PhaseManager set | players.is_intro_ready |
| 発言者 | SpeechManager dict | phases.current_speaker_id |
| 一時停止 | PhaseManager dict | phases.paused_remaining_sec |

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

### テーブル拡張

```sql
-- Phase
ALTER TABLE phases ADD COLUMN paused_remaining_sec INTEGER;
ALTER TABLE phases ADD COLUMN current_speaker_id VARCHAR REFERENCES players(id);
ALTER TABLE phases ADD COLUMN discoveries_status VARCHAR DEFAULT 'pending';

-- Player
ALTER TABLE players ADD COLUMN is_intro_ready BOOLEAN DEFAULT FALSE;
```

### PhaseType 拡張

```python
class PhaseType(StrEnum):
    initial = "initial"
    storytelling = "storytelling"  # NEW
    opening = "opening"
    discussion = "discussion"
    planning = "planning"
    investigation = "investigation"
    voting = "voting"
```

---

## LLM 呼び出し

### 原則

LLM は WS ハンドラをブロックしない。DB セッションは LLM 呼び出し中に保持しない。

```
advance で investigation に遷移
  → DB 更新（即座）
  → game.state を全クライアントに送信（discoveries_status=generating）
  → asyncio.create_task(generate_discoveries)
  → WS のレスポンスループは即座に戻る

generate_discoveries:
  1. DB からコンテキスト取得 → セッション閉じる
  2. LLM 呼び出し（並列、DB 不要）
  3. 結果を DB に保存 → セッション閉じる
  4. discoveries_status = 'ready'
  5. game.state を全クライアントに送信
```

---

## v2 から廃止するもの

### フォールバック処理
- `_check_and_advance_expired_phase`
- `pollGameState`
- `fetchDiscoveriesHTTP`
- `Force dismissing stale transition overlay`
- `_restore_active_timers`
- `phase.timer_expired` メッセージ

### メモリ内状態管理
- PhaseManager クラス全体
- SpeechManager クラス全体
- `_timers`, `_investigation_selections`, `_discoveries`, `_intro_ready`, `_paused`
- `_advancing_rooms`

### 不要な try-catch
- advance_phase 内の全例外握りつぶし
- discoveries 生成の `return_exceptions=True`

---

## v2 から維持するもの

- WS メッセージの送受信プロトコル（メッセージ名は整理）
- game.state の自動送信（接続時・状態変更時）
- サーバー権威モデル（全バリデーションはサーバー）
- SQLAlchemy + Alembic + PostgreSQL
- FastAPI + WebSocket
- iOS: ObservableObject + @Published パターン

---

## 移行計画

### Phase 1: DB スキーマ拡張
- investigation_selections テーブル
- phases 拡張（paused_remaining_sec, current_speaker_id, discoveries_status）
- players 拡張（is_intro_ready）
- PhaseType に storytelling 追加
- マイグレーション

### Phase 2: サービス層書き換え
- GameService（DB のみ、メモリ状態なし）
- SpeechService（DB のみ）
- DiscoveryService（LLM + DB、セッション分離）

### Phase 3: WS ハンドラ書き換え
- 全アクションの WS メッセージ処理を新サービスに委譲
- サーバー側 ping/pong 追加（20秒間隔）
- game.state 送信ロジックの整理

### Phase 4: iOS 書き換え
- game.state の差分検出 → シーン切り替え（GameStateSync）
- PhaseScreenState（active / transitioning）
- フェーズ別ビュー分割
- ポーリング・フォールバック全削除

### Phase 5: クリーンアップ
- PhaseManager, SpeechManager 削除
- フォールバック処理削除
- 不要な try-catch 削除
- テスト全面更新
