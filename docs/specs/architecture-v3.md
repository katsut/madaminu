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

全エンドポイントは `X-Device-Id` ヘッダ必須。認証が必要な操作は `X-Session-Token` も必須。

| 操作 | メソッド | パス | 備考 |
|------|--------|------|------|
| ルーム一覧 | GET | /api/v1/rooms | 公開ルーム一覧 |
| ルーム作成 | POST | /api/v1/rooms | `display_name`, `room_name?`, `password?`, `turn_count` |
| ルーム参加 | POST | /api/v1/rooms/{code}/join | デバイス ID で既存プレイヤー再認証 |
| ルーム詳細 | GET | /api/v1/rooms/{code} | プレイヤー一覧含む |
| 自分のルーム一覧 | GET | /api/v1/rooms/mine/list | デバイス ID で参加中ルーム取得 |
| ルーム削除 | DELETE | /api/v1/rooms/{code} | ホストのみ |
| 準備状態トグル | POST | /api/v1/rooms/{code}/ready | （現状 iOS UI からは未呼出。キャラ作成時に自動 ready） |
| キャラクター作成 | POST | /api/v1/rooms/{code}/characters | 完了時に `is_ready=True` を自動設定 |
| ゲーム開始 | POST | /api/v1/rooms/{code}/start | ホストのみ。4人未満なら AI 補充。タイムアウト 120s |
| 証拠保持 | POST | /api/v1/rooms/{code}/keep-evidence | WS 不通時のフォールバック |
| 発見一覧 | GET | /api/v1/rooms/{code}/discoveries | investigation 中のフォールバック |
| ゲーム状態 | GET | /api/v1/rooms/{code}/state | 任意ポーリング |
| デバッグ情報 | GET | /api/v1/rooms/{code}/debug | 開発用 |
| キャラ画像 | GET | /api/v1/images/player/{player_id} | `?size=N` でリサイズ |
| シーン画像 | GET | /api/v1/images/game/{code}/scene | 〃 |
| 被害者画像 | GET | /api/v1/images/game/{code}/victim | 〃 |
| マップ SVG | GET | /api/v1/images/game/{code}/map | 動的生成 SVG |

### WS — ゲーム中の全通信

ゲーム開始後の全操作は WS で行う。送信も受信も WS。

#### クライアント → サーバー（アクション）

v3 ハンドラは新旧の type 名を両方受け付ける（カッコ内は legacy alias）。

| メッセージ | data | フェーズ | 備考 |
|-----------|------|---------|------|
| `advance` (`phase.advance`, `phase.timer_expired`) | `{force?: bool}` | ホスト手動進行（storytelling/opening/briefing）/ タイマー期限通知 | force はホストのみ |
| `select_location` (`investigate.select`) | `{location_id}` | planning | |
| `keep_evidence` (`investigate.keep`) | `{discovery_id}` | investigation | 同フェーズで未 keep のみ |
| `reveal_evidence` (`evidence.reveal`) | `{evidence_id}` | discussion | 自分の手持ち証拠のみ |
| `speech.request` | — | opening / discussion / voting | 割り込み可 |
| `speech.release` | `{transcript}` | 同上 | current_speaker == 自分のみ |
| `vote` (`vote.submit`) | `{suspect_player_id}` | voting | 1回のみ |
| `room_message` (`room_message.send`) | `{text}` | investigation | 同室プレイヤーにのみ配信 |
| `retry_generation` | — | 任意 | ホスト：LLM 生成失敗時のリトライ |
| `intro.ready` / `intro.unready` | — | イントロ | |
| `pong` | — | ping 応答 | サーバー → クライアント ping への応答 |
| `phase.timer` / `phase.extend` / `phase.pause` / `phase.resume` | — | — | **未実装（受信されるが no-op）**。延長・一時停止は v3 では取り下げ |

#### サーバー → クライアント（通知）

| メッセージ | data | タイミング |
|-----------|------|-----------|
| `game.state` | フルステート（プレイヤー個別、`my_*` フィールドは個人情報） | 接続時、フェーズ変更時、画像/discovery 生成完了時、投票完了時 |
| `game.generating` | `{room_code}` | start_game 受領直後 |
| `game.ready` | `{room_code}` | シナリオ + 画像生成完了 |
| `game.generation_failed` | `{room_code}` | シナリオ生成リトライ全滅時。status=waiting に戻す |
| `progress` | `{step, status}` | `step ∈ {scenario, scene_image, portraits}`、`status ∈ {in_progress, done}` |
| `speech` | `{player_id, character_name, transcript}` | 発言終了時（人間・AI 両方とも同一 type） |
| `speech.granted` | `{player_id}` | 発言権付与（送信元のみ） |
| `speech.active` | `{player_id}` | 発言中通知（全員） |
| `evidence_revealed` | `{player_id, player_name, title, content}` | discussion で証拠公開時 |
| `vote_cast` | `{voted_count, total_human}` | 投票時 |
| `room_message` | `{sender_id, sender_name, text}` | investigation 同室チャット |
| `location.colocated` | `{players: [...]}` | investigation 開始直後、各プレイヤーに同室者一覧 |
| `intro.ready.count` | `{count}` | イントロ ready 人数（未使用、今後追加予定） |
| `intro.all_ready` | — | 全員 ready |
| `player.connected` / `player.disconnected` | `{player_id}` | WS 接続変動 |
| `error` | `{code, message, ...}` | バリデーションエラー時。送信元のみ |
| ping | — | サーバー側で URLSession の WebSocket ping フレーム送出（アプリ層 `ping` メッセージは送らない） |

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
| 1 | storytelling | 読み合わせ | ホスト手動 (0s) | ホストが物語を読み上げ（被害者は生きている） |
| 2 | opening | 自己紹介 | タイマー (300s) | 1人ずつ順番に自己紹介（selfIntroduction セリフ）。AI も発言 |
| 3 | briefing | 事件概要 | ホスト手動 (0s) | 事件詳細確認 + 証拠・アリバイ・情報カード確認 |
| 4 | discussion | 議論 | タイマー (180s) | 議論・証拠公開。AI 発言あり |
| 5 | planning | 調査計画 | タイマー (120s) | 調査場所選択 |
| 6 | investigation | 調査 | タイマー (120s) | 調査・証拠保持。同室チャット |
| | *(4→5→6 を turn_count ターン繰り返し / 既定 3 ターン、2〜5 で可変)* | | | |
| 7 | voting | 投票 | タイマー (300s) | 最終議論 + 投票（全員投票で即遷移） |
| 8 | ending | 結果発表 | — | エンディング生成・演出・ネタバラシ |

実際の生成順序は `services/scenario_engine.py:_create_cycle_phases` を参照。`PHASE_DURATIONS` 定数が真。

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

## プレイヤー数 / 準備状態

- **最小**: 1 人（ホスト）から作成可能。4 人未満で start するとサーバー側で AI を自動補充
- **最大**: 7 人（`MAX_PLAYERS` / room_manager.py）
- **自動 ready**: ゲスト用の Ready ボタンは存在せず、`POST /characters` 完了時にサーバーが `is_ready = True` を自動設定する。`POST /rooms/{code}/ready` も互換のため残っているが iOS UI からは現状未使用

## AI プレイヤー

### 補充
- ゲーム開始時に `target=4` まで AI を補充。LLM (`gpt-5.4-nano`) が舞台設定に合わせて性別・年齢・職業・外見・性格・経歴を動的生成
- 各 AI 1 名ずつ独立に生成。一部失敗しても続行（全失敗時のみ start が `400 Need at least 4 characters` で失敗）

### AI 発言（discussion フェーズのみ）
- 10-30 秒間隔で発言（LLM 生成）
- 公開情報・既出証拠・発言履歴に基づく
- 80% の確率で kept evidence を公開
- 全 AI が公開しなかった場合、1 人が強制公開

### AI 調査
- investigation フェーズで自動的に 1 つ discovery を keep

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
- discovery 生成: 3 回自動リトライ
- 全リトライ失敗: フェーズを ready にしてゲーム続行
- ホストメニュー: 「生成をリトライ」ボタン

---

## 画像生成

`gpt-image-1` で並列生成し DB の `Game.scene_image` / `Game.victim_image` / `Player.portrait_image` に bytes 保存。HTTP `/api/v1/images/...` で配信、`?size=N` でリサイズ。

| 種類 | 生成元 | 関数 |
|------|--------|------|
| シーン画像 | `setting.location` / `situation` / `description` | `generate_scene_image` |
| 被害者画像 | `victim.name` + `description` | `generate_victim_portrait` |
| キャラ画像 | 各プレイヤーの gender / age / appearance | `generate_character_portrait` |

シナリオ生成完了 → 全画像を `asyncio.gather` で並列生成 → `game.state` で URL を再配信 → 第1フェーズ開始。失敗した画像は黙ってスキップ（ゲーム続行）。

---

## マップ生成

LLM が出力したシナリオの `map.locations` から `services/map_builder.py` + `map_renderer.py` で SVG を動的レンダリング。`/api/v1/images/game/{code}/map` で配信。サーバー側にバリデーション (`map_validator.py`) があり、最低限の接続性 (各部屋に 2 経路以上) を要求する。

---

## デプロイ

- Dockerfile: `scripts/start.sh` を使用
- `RESET_DB=true`: DB全削除→再構築（v3マイグレーション用）
- Alembic: `001_v3_initial.py`（全テーブル一括作成）
