# Sprint Plan: マダミヌ

**Date:** 2026-03-25
**Scrum Master:** katsut
**Project Level:** 2
**Total Stories:** 25
**Total Points:** 125
**Planned Phases:** 5
**Work Style:** 不定期開発（フェーズ制）

---

## Executive Summary

マダミヌの実装計画。個人開発・不定期稼働のため、時間ベースのスプリントではなくストーリーの依存関係と優先度に基づく5フェーズ制で進行する。Phase A〜Dの完了で友人プレイテスト可能、Phase Eで App Store 公開準備が整う。

**Key Metrics:**
- Total Stories: 25
- Total Points: 125
- Phases: 5 (A〜E)
- Must Have: 18 stories (100 points)
- Should Have: 4 stories (14 points)
- Could Have: 3 stories (11 points)

---

## Story Inventory

### EPIC-001: キャラクター＆ルーム管理

#### STORY-001: プロジェクト初期セットアップ

**Epic:** EPIC-001
**Priority:** Must Have
**Points:** 5
**Phase:** A

**User Story:**
As a 開発者
I want to FastAPI + SQLAlchemy + SQLite のプロジェクト基盤を構築する
So that 以降のストーリーをスムーズに実装できる

**Acceptance Criteria:**
- [ ] FastAPI プロジェクトが uv で初期化されている
- [ ] SQLAlchemy + aiosqlite でDB接続が動作する
- [ ] 全テーブルのスキーマが定義されマイグレーションが実行できる
- [ ] pytest + pytest-asyncio でテスト基盤が動作する
- [ ] ruff によるリント・フォーマットが設定されている
- [ ] GitHub リポジトリが作成され CI（GitHub Actions）が動作する

**Technical Notes:**
- `server/` ディレクトリにFastAPIプロジェクトを配置
- `pyproject.toml` で uv 管理
- アーキテクチャのコード構成に従う（`src/madaminu/`）
- 全エンティティ（Game, Player, Phase, SpeechLog, Evidence, Note, Vote, GameEnding, Payment）のモデル定義

---

#### STORY-024: iOS デザインシステム基盤

**Epic:** EPIC-001
**Priority:** Must Have
**Points:** 5
**Phase:** A

**User Story:**
As a 開発者
I want to 共通UIコンポーネントとデザイントークンを整備する
So that 全画面で一貫したビジュアルデザインを実現できる

**Acceptance Criteria:**
- [ ] カラーパレットが定義されている（プライマリ・セカンダリ・背景・テキスト等）
- [ ] タイポグラフィスタイルが定義されている（見出し・本文・キャプション等）
- [ ] スペーシング・角丸などのデザイントークンが定義されている
- [ ] 共通コンポーネントが実装されている（ボタン・カード・テキストフィールド・ローディング・モーダル等）
- [ ] ダークモード対応の基盤が整っている
- [ ] Xcode プロジェクト（`ios/Madaminu/`）が作成されている

**Technical Notes:**
- マーダーミステリーの雰囲気に合うダーク基調のデザイン
- SwiftUI のカスタム ViewModifier / コンポーネントとして実装
- iOS 17+ ターゲット

---

#### STORY-025: UIアセット調達・整備

**Epic:** EPIC-001
**Priority:** Must Have
**Points:** 3
**Phase:** A

**User Story:**
As a 開発者
I want to アイコン・イラスト・効果音などのアセットを調達・整備する
So that ゲーム画面に必要なビジュアル・サウンド素材が揃う

**Acceptance Criteria:**
- [ ] アイコンセットが選定・導入されている（SF Symbols ベース + 必要に応じて外部アイコン）
- [ ] ゲーム内イラスト・素材の調達方針が決定されている
- [ ] 効果音・BGM素材が調達されている（フリー音源等）
- [ ] Asset Catalog に整理されている

**Technical Notes:**
- マーダーミステリーの雰囲気に合うアセット選定
- ライセンス確認を徹底

---

#### STORY-002: ルーム作成・参加API

**Epic:** EPIC-001
**Priority:** Must Have
**Points:** 5
**Phase:** A

**User Story:**
As a ホスト
I want to ルームを作成して参加コードを発行する
So that 友人を招待してゲームを始められる

**Acceptance Criteria:**
- [ ] `POST /api/v1/rooms` でルーム作成、room_code + player_id + session_token が返る
- [ ] `POST /api/v1/rooms/:code/join` で参加、player_id + session_token が返る
- [ ] `GET /api/v1/rooms/:code` でルーム情報（プレイヤー一覧・ステータス）が返る
- [ ] room_code は一意の6文字英数字
- [ ] 4〜7人の人数制限が適用される
- [ ] session_token は UUIDv4

**Technical Notes:**
- `routers/rooms.py` に実装
- Pydantic モデルでリクエスト/レスポンスを定義

---

#### STORY-003: WebSocket接続管理

**Epic:** EPIC-001
**Priority:** Must Have
**Points:** 8
**Phase:** A

**User Story:**
As a プレイヤー
I want to WebSocket でリアルタイムにゲーム状態を受信する
So that 他プレイヤーの行動やフェーズ変更が即座にわかる

**Acceptance Criteria:**
- [ ] `wss://{host}/ws/{room_code}?token={session_token}` で WebSocket 接続できる
- [ ] 接続時に session_token で認証される
- [ ] プレイヤーの接続/切断が他プレイヤーに通知される
- [ ] 切断後の再接続でフルゲーム状態が再送される
- [ ] メッセージは player_id に基づいてフィルタリングされる（秘密情報隔離）
- [ ] 全状態変更が SQLite に永続化される

**Technical Notes:**
- `ws/handler.py` に ConnectionManager クラスを実装
- インメモリでアクティブ接続を管理、SQLiteに永続化バックアップ
- `filter_for_player(player_id, message)` 関数でメッセージフィルタリング
- NFR-002 (≤500ms遅延), NFR-005 (中断耐性), NFR-006 (秘密情報隔離) を実現

---

#### STORY-004: キャラクター作成API

**Epic:** EPIC-001
**Priority:** Must Have
**Points:** 3
**Phase:** A

**User Story:**
As a プレイヤー
I want to キャラクターの名前・性格・背景を設定する
So that 自分だけのキャラクターでゲームに参加できる

**Acceptance Criteria:**
- [ ] `POST /api/v1/rooms/:code/characters` でキャラクター情報を保存できる
- [ ] キャラクター名・性格・背景のバリデーションが行われる
- [ ] 他プレイヤーにはキャラクター名と公開情報のみ表示される
- [ ] キャラクター作成完了がルーム内の他プレイヤーに通知される

**Technical Notes:**
- `routers/characters.py` に実装
- WebSocket 経由でルーム内にキャラ作成完了を通知

---

#### STORY-005: iOS ルーム作成・参加画面

**Epic:** EPIC-001
**Priority:** Must Have
**Points:** 3
**Phase:** A

**User Story:**
As a プレイヤー
I want to アプリからルームを作成したり参加コードで参加する
So that 簡単にゲームに合流できる

**Acceptance Criteria:**
- [ ] ルーム作成ボタンで新規ルームが作成され、参加コードが表示される
- [ ] 参加コード入力でルームに参加できる
- [ ] ルーム内のプレイヤー一覧がリアルタイム更新される
- [ ] ホストが「ゲーム開始」ボタンで開始できる（全員キャラ作成完了後）
- [ ] デザインシステムの共通コンポーネントを使用

**Technical Notes:**
- REST API + WebSocket を組み合わせ
- STORY-024 のデザインシステムを使用

**Dependencies:** STORY-001, STORY-002, STORY-003, STORY-024

---

### EPIC-002: シナリオ生成＆動的調整

#### STORY-007: Scenario Engine 基盤

**Epic:** EPIC-002
**Priority:** Must Have
**Points:** 5
**Phase:** B

**User Story:**
As a システム
I want to Claude API との連携基盤とプロンプトテンプレート管理を持つ
So that シナリオ生成・動的調整の各機能を実装できる

**Acceptance Criteria:**
- [ ] anthropic SDK を使った Claude API クライアントが動作する
- [ ] ストリーミングレスポンスに対応している
- [ ] プロンプトテンプレートの読み込み・変数埋め込みが動作する
- [ ] モデル選択（Sonnet / Haiku）を呼び出し元から指定できる
- [ ] API呼び出しのトークン数・コストがログに記録される

**Technical Notes:**
- `llm/client.py` に AsyncAnthropicClient ラッパー
- `llm/prompts.py` にプロンプトテンプレート管理
- NFR-004（コスト管理）のためのインストルメンテーション

**Dependencies:** STORY-001

---

#### STORY-008: シナリオ骨格生成

**Epic:** EPIC-002
**Priority:** Must Have
**Points:** 8
**Phase:** B

**User Story:**
As a GM（LLM）
I want to キャラクター情報からシナリオの骨格を生成する
So that 毎回ユニークな物語が始まる

**Acceptance Criteria:**
- [ ] 全プレイヤーのキャラクター情報を入力としてシナリオが生成される
- [ ] 舞台設定（場所・時代・状況）が生成される
- [ ] キャラクター間の関係性が設定される
- [ ] 犯人・被害者・動機の方向性が決定される
- [ ] 各プレイヤーに秘密情報が生成される（テンプレートで役割割当→LLMが具体化）
- [ ] 各プレイヤーに個人目的（Objective）が付与される
- [ ] GM内部制御情報（各秘密に紐づく展開シナリオ）が生成・保存される
- [ ] `POST /api/v1/rooms/:code/start` でゲーム開始→シナリオ生成が実行される

**Technical Notes:**
- `services/scenario_engine.py` に実装
- テンプレート（約50パターン）からランダム or 指定で選択
- Claude Sonnet で生成
- Game.scenario_skeleton, Game.gm_internal_state, Player.secret_info, Player.objective に保存
- 生成後に WebSocket で各プレイヤーに個別情報を配信

**Dependencies:** STORY-007, STORY-003

---

#### STORY-009: シナリオバリデーション

**Epic:** EPIC-002
**Priority:** Must Have
**Points:** 5
**Phase:** B

**User Story:**
As a システム
I want to 生成されたシナリオの論理的整合性を検証する
So that フェアな推理が成立するゲームが保証される

**Acceptance Criteria:**
- [ ] シナリオ生成後にバリデーションプロンプトで整合性チェックが実行される
- [ ] 犯人が推理可能か、矛盾がないかが検証される
- [ ] 矛盾検出時にLLMが再生成を試みる（最大2回リトライ）
- [ ] バリデーション結果がログに記録される

**Technical Notes:**
- `llm/validator.py` に実装
- Claude Haiku でバリデーション（コスト抑制）
- NFR-008（シナリオ整合性）を実現

**Dependencies:** STORY-008

---

#### STORY-010: フェーズ動的調整

**Epic:** EPIC-002
**Priority:** Must Have
**Points:** 8
**Phase:** C

**User Story:**
As a GM（LLM）
I want to プレイヤーの発言・行動を分析してシナリオを調整する
So that ゲームが常に面白い方向に展開する

**Acceptance Criteria:**
- [ ] フェーズ終了時にLLMがプレイヤーの発言ログを分析する
- [ ] GMが各プレイヤーの秘密・目的を考慮して情報配布を判断する
- [ ] 次フェーズの展開が調整される
- [ ] 新たな証拠が各プレイヤーの手帳に追加される（GM主導配布）
- [ ] 議論停滞時にGMが追加情報を投入する
- [ ] 調整内容がシナリオ骨格と矛盾しない

**Technical Notes:**
- `services/scenario_engine.py` に追加
- Claude Sonnet で動的調整
- 発言ログは要約してからLLMに送信（トークン節約）
- GM内部状態を更新して次フェーズの制御に使用

**Dependencies:** STORY-008, STORY-014

---

#### STORY-011: エンディング生成

**Epic:** EPIC-002
**Priority:** Must Have
**Points:** 5
**Phase:** C

**User Story:**
As a プレイヤー
I want to 投票後にゲームのエンディングを見る
So that 真相が明かされ物語が完結する

**Acceptance Criteria:**
- [ ] 投票結果＋プレイ中の行動履歴からエンディングが生成される
- [ ] 真相（犯人・動機・トリック）が明かされる
- [ ] 各プレイヤーの個人目的の達成状況が判定される
- [ ] エンディングが全プレイヤーに同時に配信される

**Technical Notes:**
- Claude Sonnet で生成
- GameEnding テーブルに保存

**Dependencies:** STORY-010, STORY-019

---

#### STORY-012: シナリオテンプレート選択UI

**Epic:** EPIC-002
**Priority:** Could Have
**Points:** 3
**Phase:** E

**User Story:**
As a ホスト
I want to シナリオのジャンル・雰囲気を選べる
So that メンバーの好みに合ったゲームを始められる

**Acceptance Criteria:**
- [ ] テンプレートのジャンル/雰囲気一覧が表示される
- [ ] ホストが選択してゲーム開始できる
- [ ] 「おまかせ」でランダム選択もできる

**Dependencies:** STORY-005, STORY-008

---

### EPIC-003: ゲームプレイ進行

#### STORY-013: フェーズ進行管理

**Epic:** EPIC-003
**Priority:** Must Have
**Points:** 5
**Phase:** C

**User Story:**
As a プレイヤー
I want to ゲームがフェーズごとに進行する
So that 調査・議論・投票の流れでゲームを楽しめる

**Acceptance Criteria:**
- [ ] ゲームが調査→議論→投票のフェーズで構成される
- [ ] 各フェーズにタイマーが設定される
- [ ] タイマー終了時に次フェーズへの遷移が通知される
- [ ] ホストがフェーズを手動で進行/延長できる
- [ ] 現在のフェーズと残り時間が全プレイヤーに表示される

**Technical Notes:**
- `services/room_manager.py` にフェーズ管理ロジック
- サーバーサイドでタイマー管理（asyncio.Task）
- WebSocket でフェーズ遷移・タイマー情報をブロードキャスト

**Dependencies:** STORY-003, STORY-008

---

#### STORY-014: 発言権制

**Epic:** EPIC-003
**Priority:** Must Have
**Points:** 5
**Phase:** C

**User Story:**
As a プレイヤー
I want to 発言ボタンで発言権を取得して話す
So that 1人ずつ順序立てて議論できる

**Acceptance Criteria:**
- [ ] `speech.request` で発言権をリクエストできる
- [ ] 同時に発言できるのは1人のみ（排他制御）
- [ ] 発言中であることが他プレイヤーに表示される
- [ ] `speech.release` で発言権を解放、transcript が保存される
- [ ] 発言権取得失敗時に `speech.denied` が返る

**Technical Notes:**
- Room Manager 内でロック管理（asyncio.Lock）
- WebSocket メッセージで状態をブロードキャスト

**Dependencies:** STORY-003

---

#### STORY-017: 能動的探索

**Epic:** EPIC-003
**Priority:** Must Have
**Points:** 5
**Phase:** C

**User Story:**
As a プレイヤー
I want to 調査フェーズで場所や対象を選んで調べる
So that 自分の行動で手がかりを発見できる

**Acceptance Criteria:**
- [ ] 調査フェーズで調査可能な場所/対象の一覧が表示される
- [ ] `investigate` メッセージで調査リクエストを送信できる
- [ ] LLM（GM）が秘密・シナリオ進行に基づいて調査結果を生成する
- [ ] 調査結果が証拠カードとして手帳に追加される
- [ ] 調査回数の制限が機能する

**Technical Notes:**
- Phase.investigation_locations に調査可能場所リストを保持
- Claude Haiku で調査結果生成（低コスト）
- Evidence テーブルに source='investigation' で保存

**Dependencies:** STORY-008, STORY-013

---

#### STORY-019: 投票＋エンディング表示

**Epic:** EPIC-003
**Priority:** Must Have
**Points:** 5
**Phase:** C

**User Story:**
As a プレイヤー
I want to 犯人だと思う人物に投票し、結果とエンディングを見る
So that ゲームが完結する

**Acceptance Criteria:**
- [ ] 投票フェーズで全プレイヤーが犯人候補に投票できる
- [ ] `vote.submit` で投票を送信できる
- [ ] 全員投票完了後に投票結果が全員に公開される
- [ ] エンディングが生成・表示される
- [ ] 各プレイヤーの個人目的達成状況が表示される

**Technical Notes:**
- Vote テーブルに保存
- 全員投票完了をトリガーに STORY-011 のエンディング生成を呼び出し

**Dependencies:** STORY-013, STORY-011

---

### EPIC-003 (iOS UI)

#### STORY-006: iOS キャラクター作成画面

**Epic:** EPIC-001
**Priority:** Must Have
**Points:** 5
**Phase:** D

**User Story:**
As a プレイヤー
I want to ステップバイステップでキャラクターを作成する
So that 迷わずキャラ設定を完了できる

**Acceptance Criteria:**
- [ ] 名前→性格→背景のステップバイステップ入力
- [ ] 各ステップでヒントやガイドが表示される
- [ ] 入力内容のプレビューが表示される
- [ ] 完了時にサーバーに送信される
- [ ] デザインシステムの共通コンポーネントを使用

**Dependencies:** STORY-004, STORY-024

---

#### STORY-015: 音声認識連携

**Epic:** EPIC-003
**Priority:** Must Have
**Points:** 5
**Phase:** D

**User Story:**
As a プレイヤー
I want to 発言ボタンを押して話すと自動で文字起こしされる
So that 手入力なしで発言をゲームに反映できる

**Acceptance Criteria:**
- [ ] 発言ボタンタップでマイクがONになる
- [ ] Apple Speech Framework でリアルタイム文字起こしされる
- [ ] 文字起こし結果が画面に表示される
- [ ] 発言終了操作で transcript がサーバーに送信される
- [ ] マイク権限のリクエストが適切に処理される

**Technical Notes:**
- Apple Speech Framework（iOS端末側処理）
- NFR-003（≤3秒レイテンシ）

**Dependencies:** STORY-014, STORY-024

---

#### STORY-016: iOS 個人手帳UI

**Epic:** EPIC-003
**Priority:** Must Have
**Points:** 5
**Phase:** D

**User Story:**
As a プレイヤー
I want to 自分の秘密情報・目的・証拠・メモを手帳で管理する
So that ゲーム中に必要な情報を確認しながら推理できる

**Acceptance Criteria:**
- [ ] 自分のキャラクター情報・秘密情報が表示される
- [ ] 個人目的（Objective）が表示される
- [ ] 証拠カードの一覧が表示され、新規追加時にアニメーションされる
- [ ] 自由にメモを記入・編集できる
- [ ] GM主導配布の情報がリアルタイムに反映される

**Dependencies:** STORY-003, STORY-024

---

#### STORY-018: iOS ゲームプレイ画面

**Epic:** EPIC-003
**Priority:** Must Have
**Points:** 8
**Phase:** D

**User Story:**
As a プレイヤー
I want to ゲーム中の操作（発言・調査・投票）を1つの画面で行う
So that スムーズにゲームに参加できる

**Acceptance Criteria:**
- [ ] 現在のフェーズとタイマーが表示される
- [ ] 発言ボタンが目立つ位置にある
- [ ] 誰が発言中かが表示される
- [ ] 調査フェーズで場所/対象の選択UIが表示される
- [ ] 投票フェーズで候補者選択UIが表示される
- [ ] エンディング表示画面がある
- [ ] 個人手帳へのアクセスが常に可能

**Technical Notes:**
- フェーズごとに表示内容が切り替わるメイン画面
- WebSocket からのメッセージでUIをリアクティブに更新

**Dependencies:** STORY-013, STORY-014, STORY-015, STORY-016, STORY-017, STORY-024

---

#### STORY-020: 音声認識結果の確認・修正UI

**Epic:** EPIC-003
**Priority:** Should Have
**Points:** 3
**Phase:** D

**User Story:**
As a プレイヤー
I want to 音声認識の文字起こしを確認・修正できる
So that 誤認識があっても正しい内容を記録できる

**Acceptance Criteria:**
- [ ] 発言後に文字起こし結果が表示される
- [ ] タップして修正できる
- [ ] 修正内容がサーバーに反映される

**Dependencies:** STORY-015

---

### EPIC-004: 課金＆周辺機能

#### STORY-021: IAP課金

**Epic:** EPIC-004
**Priority:** Should Have
**Points:** 5
**Phase:** E

**User Story:**
As a ホスト
I want to ゲーム開始前に1プレイ分の課金を完了する
So that ゲームをプレイできる

**Acceptance Criteria:**
- [ ] ゲーム開始前にIAP購入フローが表示される
- [ ] StoreKit 2 で決済が完了する
- [ ] `POST /api/v1/payments/verify` でレシート検証される
- [ ] 決済完了後にゲーム開始可能になる
- [ ] 課金はホストのみ対象

**Technical Notes:**
- iOS: StoreKit 2
- Server: `services/payment_service.py` + App Store Server API

---

#### STORY-022: ゲーム進行ガイド

**Epic:** EPIC-004
**Priority:** Should Have
**Points:** 3
**Phase:** E

**User Story:**
As a マダミス初心者
I want to 各フェーズで何をすべきか教えてもらう
So that ルールを知らなくてもゲームに参加できる

**Acceptance Criteria:**
- [ ] 初回プレイ時にチュートリアルが表示される
- [ ] 各フェーズ開始時に目的と操作方法がガイドされる
- [ ] ガイドを非表示にできる

---

#### STORY-012: シナリオテンプレート選択UI

**Epic:** EPIC-002
**Priority:** Could Have
**Points:** 3
**Phase:** E

*(前述の通り)*

---

#### STORY-023: プレイ履歴

**Epic:** EPIC-004
**Priority:** Could Have
**Points:** 3
**Phase:** E

**User Story:**
As a プレイヤー
I want to 過去のゲームを振り返る
So that 思い出を楽しめる

**Acceptance Criteria:**
- [ ] 過去ゲーム一覧が表示される
- [ ] 各ゲームのキャラ・エンディングが閲覧できる
- [ ] プレイ日時・参加者が表示される

**Technical Notes:**
- `GET /api/v1/history`, `GET /api/v1/games/:id/history`

---

## Phase Allocation

### Phase A: 基盤構築 — 32 points

**Goal:** サーバー基盤＋iOS基盤＋ルーム管理が動作し、WebSocket接続でリアルタイム同期できる状態

| Story | Title | Points | Priority |
|-------|-------|--------|----------|
| STORY-001 | プロジェクト初期セットアップ | 5 | Must |
| STORY-024 | デザインシステム基盤 | 5 | Must |
| STORY-025 | UIアセット調達・整備 | 3 | Must |
| STORY-002 | ルーム作成・参加API | 5 | Must |
| STORY-003 | WebSocket接続管理 | 8 | Must |
| STORY-004 | キャラクター作成API | 3 | Must |
| STORY-005 | iOS: ルーム作成・参加画面 | 3 | Must |

**Milestone:** ルーム作成→参加→キャラ作成→WebSocket接続がE2Eで動作

---

### Phase B: シナリオ生成コア — 18 points

**Goal:** LLMによるシナリオ骨格生成が動作し、キャラ情報から秘密・目的・GM内部状態が生成される

| Story | Title | Points | Priority |
|-------|-------|--------|----------|
| STORY-007 | Scenario Engine基盤 | 5 | Must |
| STORY-008 | シナリオ骨格生成 | 8 | Must |
| STORY-009 | シナリオバリデーション | 5 | Must |

**Milestone:** キャラ作成→ゲーム開始→シナリオ生成→個別情報配信が動作（CLIテスト可能）

---

### Phase C: ゲームプレイループ — 33 points

**Goal:** サーバーサイドで1ゲーム（調査→議論→投票→エンディング）が通しで動作

| Story | Title | Points | Priority |
|-------|-------|--------|----------|
| STORY-013 | フェーズ進行管理 | 5 | Must |
| STORY-014 | 発言権制 | 5 | Must |
| STORY-010 | フェーズ動的調整 | 8 | Must |
| STORY-017 | 能動的探索 | 5 | Must |
| STORY-011 | エンディング生成 | 5 | Must |
| STORY-019 | 投票＋エンディング表示 | 5 | Must |

**Milestone:** バックエンドで完全な1ゲームループが動作

---

### Phase D: iOS UI — 28 points

**Goal:** iOSアプリで1ゲーム通しプレイ可能。友人プレイテスト実施可能

| Story | Title | Points | Priority |
|-------|-------|--------|----------|
| STORY-006 | キャラクター作成画面 | 5 | Must |
| STORY-015 | 音声認識連携 | 5 | Must |
| STORY-016 | 個人手帳UI | 5 | Must |
| STORY-018 | ゲームプレイ画面 | 8 | Must |
| STORY-020 | 音声認識修正UI | 3 | Should |

**Milestone:** 友人とのプレイテスト可能（プロダクトブリーフの最優先目標）

---

### Phase E: ポリッシュ — 14 points

**Goal:** 課金・ガイド・履歴機能を追加し、App Store 公開準備完了

| Story | Title | Points | Priority |
|-------|-------|--------|----------|
| STORY-021 | IAP課金 | 5 | Should |
| STORY-022 | ゲーム進行ガイド | 3 | Should |
| STORY-012 | テンプレート選択UI | 3 | Could |
| STORY-023 | プレイ履歴 | 3 | Could |

**Milestone:** App Store 公開準備完了

---

## Epic Traceability

| Epic ID | Epic Name | Stories | Total Points | Phase |
|---------|-----------|---------|--------------|-------|
| EPIC-001 | キャラクター＆ルーム管理 | STORY-001, 002, 003, 004, 005, 006, 024, 025 | 37 | A, D |
| EPIC-002 | シナリオ生成＆動的調整 | STORY-007, 008, 009, 010, 011, 012 | 34 | B, C, E |
| EPIC-003 | ゲームプレイ進行 | STORY-013, 014, 015, 016, 017, 018, 019, 020 | 41 | C, D |
| EPIC-004 | 課金＆周辺機能 | STORY-021, 022, 023 | 11 | E |

---

## Functional Requirements Coverage

| FR ID | FR Name | Story | Phase |
|-------|---------|-------|-------|
| FR-001 | キャラクター作成 | STORY-004, STORY-006 | A, D |
| FR-002 | ルーム作成・参加 | STORY-002, STORY-005 | A |
| FR-003 | ゲーム状態同期 | STORY-003 | A |
| FR-004 | シナリオ骨格生成 | STORY-008, STORY-009 | B |
| FR-005 | 個人手帳UI | STORY-016 | D |
| FR-006 | フェーズ進行管理 | STORY-013 | C |
| FR-007 | 発言権制マイク入力 | STORY-014, STORY-015 | C, D |
| FR-008 | 動的調整 | STORY-010 | C |
| FR-009 | 投票・エンディング | STORY-011, STORY-019 | C |
| FR-010 | IAP課金 | STORY-021 | E |
| FR-011 | 音声認識修正 | STORY-020 | D |
| FR-012 | ゲーム進行ガイド | STORY-022 | E |
| FR-013 | プレイ履歴 | STORY-023 | E |
| FR-014 | テンプレート選択 | STORY-012 | E |
| FR-015 | 能動的探索 | STORY-017 | C |

**Coverage: 15/15 FRs (100%)**

---

## Risks and Mitigation

**High:**
- LLMシナリオ整合性: テンプレート制約＋バリデーション（STORY-009）で対応。Phase Bで早期検証
- LLM APIコスト: Phase Bでコスト計測開始。モデル使い分けで最適化

**Medium:**
- 発言権制のUX: Phase Cで動作検証、Phase Dで実機テスト
- Apple Speech精度: Phase Dで実機テスト。不十分ならWhisper APIに切り替え検討

**Low:**
- SQLiteの同時接続制限: 初期フェーズでは問題なし。監視対象

---

## Dependencies

**External:**
- Claude API (Anthropic) — Phase B以降
- Apple Developer Program — Phase D以降（TestFlight配信）
- App Store審査 — Phase E

**Internal:**
- シナリオテンプレート（50パターン）の設計 — Phase B開始前に方針決定

---

## Definition of Done

For a story to be considered complete:
- [ ] コード実装・コミット済み
- [ ] ユニットテスト作成・パス（カバレッジ80%目標）
- [ ] 統合テストパス（該当する場合）
- [ ] ruff lint / format パス
- [ ] 受入基準を全て満たしている
- [ ] 関連ドキュメントが更新されている

---

## Next Steps

**Immediate:** Phase A 開始

Run `/dev-story STORY-001` to begin implementation.

**Implementation order within Phase A:**
1. STORY-001: プロジェクト初期セットアップ
2. STORY-024 + STORY-025: デザインシステム＋アセット（並行可能）
3. STORY-002: ルーム作成・参加API
4. STORY-003: WebSocket接続管理
5. STORY-004: キャラクター作成API
6. STORY-005: iOS ルーム作成・参加画面

---

**This plan was created using BMAD Method v6 - Phase 4 (Implementation Planning)**

*To continue: Run `/workflow-status` to see your progress and next recommended workflow.*
