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
| ゲーム開始 | POST | /rooms/{code}/start |
| 画像取得 | GET | /images/... |
| マップ SVG | GET | /images/game/{code}/map |

### WS — ゲーム中の全通信

ゲーム開始後の全操作は WS で行う。送信も受信も WS。

#### クライアント → サーバー（アクション）

| メッセージ | データ | フェーズ |
|-----------|--------|---------|
| `advance` | `{force?: bool}` | ホスト手動進行（storytelling/opening/briefing）|
| `select_location` | `{location_id}` | planning |
| `keep_evidence` | `{discovery_id}` | investigation |
| `reveal_evidence` | `{evidence_id}` | discussion |
| `speech.request` | — | opening/discussion/voting |
| `speech.release` | `{transcript}` | opening/discussion/voting |
| `vote` | `{suspect_player_id}` | voting |
| `room_message` | `{text}` | investigation（同室チャット） |
| `retry_generation` | — | ホスト：LLM生成リトライ |
| `intro.ready` / `intro.unready` | — | イントロ |
| `pong` | — | ping応答 |

#### サーバー → クライアント（通知）

| メッセージ | データ | タイミング |
|-----------|--------|-----------|
| `game.state` | フルステート | 接続時、フェーズ変更時、状態変更時 |
| `speech` | `{player_id, character_name, transcript}` | 発言終了時（人間・AI両方） |
| `speech.granted` | `{player_id}` | 発言権付与時 |
| `speech.active` | `{player_id}` | 発言中通知 |
| `evidence_revealed` | `{player_id, player_name, title, content}` | 証拠公開時 |
| `vote_cast` | `{voted_count, total_human}` | 投票時 |
| `location.colocated` | `{players: [...]}` | investigation で同室プレイヤー通知 |
| `progress` | `{step, status}` | シナリオ/画像生成進捗 |
| `ping` | — | 20秒間隔のキープアライブ |
| `error` | `{code, message}` | バリデーションエラー時 |

### game.state の役割

`game.state` はサーバーの正のデータ。以下のタイミングで送信：

1. **WS 接続確立時** — 自動送信。再接続時もこれで最新状態に復帰
2. **フェーズ変更時（preparing）** — 遷移パネル表示
3. **フェーズ準備完了時（ready）** — 遷移パネル消去、フェーズ画面表示、タイマー開始
4. **状態変更時** — keep_evidence, discoveries完了 等

### 2段階フェーズ遷移プロトコル

| # | サーバー処理 | broadcast | クライアント表示 |
|---|------------|-----------|--------------|
| 1 | advance: 旧フェーズ終了 → 新フェーズ開始 (discoveries_status=preparing) | 1st game.state | phase_id変化検知 → 遷移パネル表示 |
| 2 | 3秒後 (investigation は+LLM完了): discoveries_status=ready | 2nd game.state | ready検知 → 遷移パネル消去 → フェーズ画面 |
| 3 | schedule_phase_timer(duration_sec) | — | remaining_secでタイマー開始 |

### WS 接続維持

- サーバーが **20秒間隔で ping** を送信
- クライアントが pong を返す
- 切断検知 → 指数バックオフで再接続（1s, 2s, 4s, 8s, 16s, 30s）
- 再接続成功 → サーバーが `game.state` を自動送信 → 差分適用（遷移パネルなし）

---

## ゲームフロー

### フェーズ一覧

| # | phase_type | 表示名 | 進行方式 | 内容 |
|---|-----------|--------|---------|------|
| 1 | storytelling | 読み合わせ | ホスト手動 | ホストが物語を読み上げ（被害者は生きている） |
| 2 | opening | 自己紹介 | ホスト手動 | 1人ずつ順番に自己紹介（selfIntroduction セリフ） |
| 3 | briefing | 事件概要 | ホスト手動 | 事件詳細確認 + 証拠・アリバイ・情報カード確認 |
| 4 | discussion | 議論 | タイマー(180s) | 議論・証拠公開。AI発言あり |
| 5 | planning | 調査計画 | タイマー(120s) | 調査場所選択 |
| 6 | investigation | 調査 | タイマー(120s) | 調査・証拠保持。同室チャット |
| | *(4→5→6 を N ターン)* | | | |
| 7 | voting | 投票 | タイマー(300s) | 最終議論 + 投票 |
| 8 | ending | 結果発表 | — | エンディング生成・演出・ネタバラシ |

### フロー

```
storytelling → opening → briefing → [discussion → planning → investigation] × N → voting → ending
```

### 物語の流れ

1. **読み合わせ（storytelling）**: ホストがNovelTextView（サウンドノベル風）で物語を読み上げ。被害者は生きている。最後に被害者が参加者に自己紹介を促す
2. **自己紹介（opening）**: ホストが1人ずつ指名。selfIntroductionセリフを参考に自己紹介。職業は自己紹介で名乗る（嘘あり）
3. **遷移演出: 事件発生**: murder_discoveryテキストで事件発覚を演出
4. **事件概要（briefing）**: 被害者情報、発見状況、事件詳細(murder_detail)、カード確認、秘密・目的確認
5. **捜査サイクル**: discussion → planning → investigation を N 回繰り返し
6. **投票（voting）**: 最終議論 + 犯人投票
7. **エンディング**:
   - 演出: 「私たちは○○を犯人として拘束しました」→「○○は…」→「犯人でした/冤罪でした」
   - Page 1: エピローグ（ホスト読み上げ、NovelTextView）
   - Page 2: 犯人の告白（犯人読み上げ）→ 1人ずつネタバラシ（下位から）→ ランキング

---

## カードシステム

事件発生時（briefingフェーズ）に配布。

| 種類 | 枚数 | アイコン | 内容 |
|------|------|---------|------|
| 証拠 | 3枚 | 🔍 赤 | 物的証拠（誰のものか不明） |
| アリバイ | 参加人数分 | 🕐 青 | 自分のアリバイ + 他人の行動目撃 |
| 情報 | 参加人数分 | 💬 黄 | 「○○に関する情報」。目撃/噂/行動/物的。半分ミスリード |

### 情報カードの種類
- 目撃:「○○が△△を通りかかるのを見た」
- 噂:「○○は以前トラブルを起こしたらしい」
- 行動:「○○が不審な電話をしていた」
- 物的:「○○のカバンに見慣れないものがあった」

---

## AI プレイヤー

### 補充
- 4人未満の場合、ゲーム開始時にAIプレイヤーを補充（最大4人まで）

### AI 発言（discussion フェーズのみ）
- 10-30秒間隔で発言（LLM生成）
- 公開情報・既出証拠・発言履歴に基づく
- 80%の確率で kept evidence を公開
- 全AIが公開しなかった場合、1人が強制公開

### AI 調査
- investigation フェーズで自動的に1つ discovery を keep

---

## サーバー構成

### モジュール構成

```
ws/handler_v3.py  — WS エンドポイント（認証、メッセージディスパッチ）
ws/actions.py     — アクションハンドラ（advance, vote, speech等）
ws/manager_v3.py  — WSManager（接続管理、broadcast、ping）
services/         — ビジネスロジック（GameService, SpeechService, DiscoveryService）
repositories/     — DB操作（phase_repo, selection_repo）
schemas/game.py   — build_game_state（game.stateの構築）
```

### サーバーサイドタイマー
- `schedule_phase_timer`: フェーズ ready 後に `asyncio.Task` でタイマースケジュール
- `duration_sec == 0`: 手動進行（タイマーなし）
- タイマー期限 → 自動 `handle_advance(force=True)` → 次フェーズへ

### LLM エラーリカバリ
- discovery 生成: 3回自動リトライ
- 全リトライ失敗: フェーズを ready にしてゲーム続行
- ホストメニュー: 「生成をリトライ」ボタン

---

## デプロイ

- Dockerfile: `scripts/start.sh` を使用
- `RESET_DB=true`: DB全削除→再構築（v3マイグレーション用）
- Alembic: `001_v3_initial.py`（全テーブル一括作成）
