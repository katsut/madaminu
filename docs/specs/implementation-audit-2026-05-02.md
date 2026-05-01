# 実装監査レポート 2026-05-02

PRD (`docs/prd-madaminu-2026-03-24.md`) と実装の差分。**仕様の側を直すか実装の側を直すかの判断材料**。

---

## A. PRD に書かれているが未実装 / 実装意図が変わったもの

| ID | 要件 | 現状 | 推奨アクション |
|----|------|------|---------------|
| FR-002 | 4〜7 人の人数制限 | サーバーは MIN_PLAYERS=4 / MAX_PLAYERS=7。実態は **4 人未満なら AI 補充**で運用。1 人ホストでも開始可能 | **PRD 更新**: 「人間 1 人でも AI 補充で開始可能。最大 7 人」 |
| FR-006 | ホストがフェーズを手動で **進行 / 延長** できる | `phase.extend` / `phase.pause` / `phase.resume` は v3 で **no-op**。`advance(force=True)` のみ | **PRD 更新**: 延長・一時停止は取り下げ。または実装側で復活 |
| FR-007 | 「同時に発言できるのは 1 人のみ（**排他制御**）」 | 実装は **割り込み可**（`speech.request` が来ると即座に speaker 切替） | 設計判断が必要：割り込みを残すなら PRD を修正 |
| FR-010 | 1 プレイ課金（IAP） | **未実装** | MVP 範囲外として PRD を Could Have に降格、または実装計画化 |
| FR-011 | 音声認識結果の確認・修正 | iOS `TranscriptEditView` あり。サーバーに修正反映は **未実装** | サーバー API 追加 or PRD のサーバー反映要件を削除 |
| FR-012 | 初心者向けチュートリアル / ガイド UI | **未実装** | Could Have に降格、または実装計画化 |
| FR-013 | プレイ履歴 | **未実装**（DB スキーマには Game.ended_at だけ残る） | Could Have のまま（PRD 通り） |
| FR-014 | シナリオテンプレート選択（50 パターン） | **未実装**。AI が動的生成しているのでテンプレートの概念がない | **PRD 更新**: 「テンプレートではなく完全動的生成」に変更 |
| NFR-005 | ゲーム中断耐性（再接続で復帰） | 実装あり（DB 永続化 + game.state 再送） | OK |
| NFR-008 | シナリオ整合性のバリデーション | 部分実装。`map_validator.py` のみ。シナリオ全体のロジック検証は **未実装** | バリデーション層追加 or 要件を緩和 |

---

## B. 実装にあるが PRD に書かれていないもの

| 機能 | 実装場所 | 推奨アクション |
|------|---------|---------------|
| AI プレイヤー動的補充（性別・年齢・職業・外見・性格・経歴を LLM 生成） | `services/ai_player.py` | **PRD に FR 追加**: 「AI 自動補充とキャラ動的生成」 |
| シーン画像 / 被害者画像 / キャラポートレート画像生成（gpt-image-1） | `services/image_generator.py` | **PRD に FR 追加**: 「LLM 生成画像によるイマージョン強化」 |
| マップ SVG 動的生成 + バリデーション | `services/map_builder.py`, `map_renderer.py`, `map_validator.py` | **PRD に FR 追加**: 「ゲームごとに固有のマップを生成」 |
| 同室チャット（投資 investigation のみ） | `ws/actions.py:handle_room_message` | **PRD に AC 追加**: FR-015 に「同室プレイヤーとのチャット」 |
| 個人目的（Objective）の達成判定 + ランキング表示 | `services/scenario_engine.py:generate_ending` | FR-009 の AC を更新 |
| 2 段階フェーズ遷移（preparing → ready） | `ws/actions.py:_finalize_phase_start` | **アーキ仕様**で吸収済み（architecture-v3.md 参照）|
| デバイス ID ベースの再認証（X-Device-Id ヘッダ） | `routers/rooms.py` | **PRD に AC 追加**: FR-002 / FR-003 「端末交換せず再参加可能」 |
| 自動 ready（キャラ作成完了で is_ready=True） | `routers/characters.py` | NFR-007 の操作性 AC に明記 |
| ターン数指定（2〜5、既定 3） | `routers/rooms.py:create_room` | FR-002 の AC に追加 |
| LLM コスト上限（$2.00 / ゲーム） | `routers/game.py:LLM_COST_LIMIT_USD` | NFR-004 の AC に明記済み（$2 上限） |
| 証拠公開時のスコア計算（発言 ×1pt + 証拠 ×3pt） | `services/scenario_engine.py:generate_ending` | FR-009 の AC に明記 |

---

## C. 仕様間の不整合（実装と無関係に直す）

| 場所 | 問題 | 対応 |
|------|------|------|
| `architecture-v3.md` フェーズ表 | opening のタイマー値が抜け（実装は 300s） | 修正済み |
| `architecture-v3.md` HTTP 表 | `mine/list`, `delete`, `keep-evidence`, `discoveries`, `state`, `debug`, `ready` が抜け | 修正済み |
| `message-design-v3.md` | `phase.extend/pause/resume` が「ホスト権限チェック」として記述。実態は no-op | 修正済み |
| `message-design-v3.md` | `tamper_evidence` がバリデーション付きで記述。実態は handler 未登録 | 修正済み |
| `game-flow.md` | 旧 `phase.started/ended` イベント前提で全フローが書かれていた。v3 は `game.state` 駆動 | 全面書き換え済み |
| `game-flow.md` | `intro.start_game`（クライアント送信）がフローに登場するが未実装 | 削除済み |
| `game-flow.md` | フェーズ表で「opening = ホスト手動」と書かれていた。実装はタイマー 300s | 修正済み |

---

## D. 推奨される PRD 改訂方針

1. **FR-014（テンプレート選択）を「完全動的生成」に書き換える** — マダミヌのコアバリュー（"AI で 1 回しか遊べない問題を解消"）と一致
2. **FR-002 の人数を「1〜7 人（4 人未満は AI 補充）」に変更** — テストプレイ実態に合わせる
3. **新規 FR を追加**: AI プレイヤー自動補充 / 画像生成 / マップ動的生成 / 個人目的達成判定 — どれもコアな差別化機能
4. **FR-006 / FR-007 / FR-010 / FR-012 を一旦 Could Have に降格** — MVP 範囲を絞る
5. **FR-011（音声認識修正）を Must Have の AC を「ローカル UI で修正」に縮小** — サーバー反映は次バージョン

これらを反映した PRD v2 を別ファイルで作成するのが望ましい（`docs/prd-madaminu-v2.md`）。
