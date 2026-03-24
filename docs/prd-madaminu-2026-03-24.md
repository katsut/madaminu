# Product Requirements Document: マダミヌ

**Date:** 2026-03-24
**Author:** katsut
**Version:** 1.0
**Project Type:** mobile-app
**Project Level:** 2
**Status:** Draft

---

## Document Overview

This Product Requirements Document (PRD) defines the functional and non-functional requirements for マダミヌ. It serves as the source of truth for what will be built and provides traceability from requirements through implementation.

**Related Documents:**
- Product Brief: docs/product-brief-madaminu-2026-03-24.md

---

## Executive Summary

マダミヌは、対面で集まった4〜7人のプレイヤーが遊ぶマーダーミステリーiOSアプリ。プレイヤーが自分のキャラクターと設定を作成し、LLMがその場でシナリオの骨格を自動生成する。ゲーム中はスマホが「個人の秘密手帳」として機能し、発言権制（トークン制）によるマイク入力でプレイヤーの行動をLLMが把握。フェーズごとにシナリオを動的に調整し、エンディングはプレイ中の展開で決まる。既存マダミスの「1回しか遊べない」「キャラが固定」という制約をAIで解消する。

---

## Product Goals

### Business Objectives

1. 自分と友達が楽しく遊べるプロダクトを作る
2. 1プレイ3〜5ドルの課金モデルで収益化する
3. 初心者でも迷わず遊べるUI/UXを実現する

### Success Metrics

- 友人とのプレイテストで「もう1回やりたい」と言われる
- 1ゲームあたりのLLM API原価が課金額の30%以下に収まる
- App Storeでの公開・初回売上の達成

---

## Functional Requirements

Functional Requirements (FRs) define **what** the system does - specific features and behaviors.

Each requirement includes:
- **ID**: Unique identifier (FR-001, FR-002, etc.)
- **Priority**: Must Have / Should Have / Could Have (MoSCoW)
- **Description**: What the system should do
- **Acceptance Criteria**: How to verify it's complete

---

### FR-001: キャラクター作成

**Priority:** Must Have

**Description:**
プレイヤーが名前・性格・背景を自由に設定してキャラクターを作成できる。

**Acceptance Criteria:**
- [ ] プレイヤーがキャラクター名を入力できる
- [ ] 性格（複数の特性から選択 or 自由記述）を設定できる
- [ ] 背景ストーリー（職業・動機など）を自由記述で設定できる
- [ ] 作成したキャラクター情報がサーバーに保存される
- [ ] 他プレイヤーにはキャラクター名と公開情報のみ表示される

---

### FR-002: ルーム作成・参加

**Priority:** Must Have

**Description:**
ホストがゲームルームを作成し、他プレイヤーが参加コードで参加できる。

**Acceptance Criteria:**
- [ ] ホストが「ルーム作成」でルームを作成できる
- [ ] ルーム作成時に一意の参加コードが発行される
- [ ] 他プレイヤーが参加コードを入力してルームに参加できる
- [ ] ルーム内のプレイヤー一覧がリアルタイムで更新される
- [ ] ホストが全員揃ったことを確認してゲームを開始できる
- [ ] 4〜7人の人数制限が適用される

---

### FR-003: ゲーム状態同期

**Priority:** Must Have

**Description:**
WebSocketでプレイヤー間のゲーム状態をリアルタイム同期する。

**Acceptance Criteria:**
- [ ] 全プレイヤーのフェーズ状態が同期される
- [ ] ホストのフェーズ進行操作が全プレイヤーに反映される
- [ ] プレイヤーの接続状態（オンライン/オフライン）が表示される
- [ ] 切断時に再接続で最新のゲーム状態を取得できる

---

### FR-004: シナリオ骨格生成

**Priority:** Must Have

**Description:**
LLMがキャラクター情報をもとにテンプレートベースでシナリオの骨格（舞台・関係性・動機の方向性）を生成する。秘密情報はGMの「操作レバー」として意図的に設計され、各プレイヤーには個人目的（Objective）が付与される。

**Acceptance Criteria:**
- [ ] 全プレイヤーのキャラクター情報を入力としてシナリオが生成される
- [ ] 舞台設定（場所・時代・状況）が生成される
- [ ] キャラクター間の関係性が設定される
- [ ] 犯人・被害者・動機の方向性が決定される（犯人本人には犯人であることが通知される）
- [ ] 各プレイヤーに個別の秘密情報が配布される（テンプレートが役割を割当、LLMがキャラに合わせて具体化）
- [ ] 各プレイヤーに個人目的（Objective）が付与される（例:「秘密を隠し通せ」「関係を修復しろ」）
- [ ] LLMがシナリオ展開のための内部制御情報（各秘密に紐づく展開シナリオ）を保持する
- [ ] テンプレート（約50パターン）をベースに生成される
- [ ] 生成されたシナリオに論理的矛盾がないことをバリデーションする

---

### FR-005: 個人手帳UI

**Priority:** Must Have

**Description:**
各プレイヤーに秘密情報・個人目的・証拠カード・メモを表示する個人画面。

**Acceptance Criteria:**
- [ ] 自分のキャラクター情報と秘密情報が表示される
- [ ] 個人目的（Objective）が表示され、達成状況がわかる
- [ ] フェーズ進行に応じて新しい証拠カードが追加される
- [ ] GM主導で配布された情報がリアルタイムに手帳に反映される
- [ ] プレイヤーが自由にメモを記入できる
- [ ] 他プレイヤーの手帳内容は閲覧できない

---

### FR-006: フェーズ進行管理

**Priority:** Must Have

**Description:**
調査→議論→投票の各フェーズをタイマー付きで管理・進行する。

**Acceptance Criteria:**
- [ ] ゲームが複数フェーズ（調査・議論・投票）で構成される
- [ ] 各フェーズにタイマーが設定される
- [ ] タイマー終了時に次フェーズへの遷移が通知される
- [ ] ホストがフェーズを手動で進行/延長できる
- [ ] 現在のフェーズと残り時間が全プレイヤーに表示される

---

### FR-007: 発言権制マイク入力

**Priority:** Must Have

**Description:**
発言ボタンタップ→マイクON→音声認識で文字起こし→LLMに話者付きで送信。

**Acceptance Criteria:**
- [ ] プレイヤーが「発言」ボタンをタップしてマイクをONにできる
- [ ] 同時に発言できるのは1人のみ（発言権の排他制御）
- [ ] 音声がリアルタイムで文字起こしされる
- [ ] 文字起こし結果が話者情報付きでサーバーに送信される
- [ ] 発言中であることが他プレイヤーに表示される
- [ ] 発言終了操作でマイクがOFFになる

---

### FR-008: フェーズごとのシナリオ動的調整

**Priority:** Must Have

**Description:**
LLM（GM）がプレイヤーの発言・行動ログからフェーズごとにシナリオを調整・肉付けする。秘密情報を「操作レバー」として活用し、証拠の出し方やタイミングを制御する。

**Acceptance Criteria:**
- [ ] フェーズ終了時にLLMがプレイヤーの発言ログを分析する
- [ ] 分析結果に基づいて次フェーズの展開が調整される
- [ ] GMが各プレイヤーの秘密・目的を考慮して情報配布を判断する
- [ ] 新たな証拠や情報が各プレイヤーの手帳に追加される（GM主導配布）
- [ ] 議論停滞時にGMが追加情報を投入してゲームを活性化する
- [ ] 調整内容がシナリオ骨格と矛盾しない

---

### FR-009: 投票・エンディング生成

**Priority:** Must Have

**Description:**
投票結果＋行動履歴からLLMがエンディングを動的に生成する。

**Acceptance Criteria:**
- [ ] 全プレイヤーが犯人だと思う人物に投票できる
- [ ] 投票結果が全プレイヤーに公開される
- [ ] LLMが投票結果＋プレイ中の行動履歴からエンディングストーリーを生成する
- [ ] エンディングで真相（犯人・動機・トリック）が明かされる
- [ ] エンディングが全プレイヤーに同時に表示される

---

### FR-010: 1プレイ課金（IAP）

**Priority:** Should Have

**Description:**
App Store In-App Purchaseで1プレイ3〜5ドルの課金を処理する。

**Acceptance Criteria:**
- [ ] ゲーム開始前にIAPの購入フローが表示される
- [ ] Apple In-App Purchaseで決済が完了する
- [ ] 決済完了後にゲームが開始可能になる
- [ ] 購入のレシート検証がサーバーサイドで行われる
- [ ] 課金はルーム作成者（ホスト）のみが対象

---

### FR-011: 音声認識結果の確認・修正

**Priority:** Should Have

**Description:**
音声認識の文字起こし結果をプレイヤーが確認・修正できる。

**Acceptance Criteria:**
- [ ] 発言後に文字起こし結果がプレイヤーに表示される
- [ ] プレイヤーが文字起こし結果をタップして修正できる
- [ ] 修正内容がサーバーに反映される

---

### FR-012: ゲーム進行ガイド

**Priority:** Should Have

**Description:**
初心者向けに各フェーズで何をすべきか説明するチュートリアル/ガイドUI。

**Acceptance Criteria:**
- [ ] 初回プレイ時にチュートリアルが表示される
- [ ] 各フェーズ開始時にフェーズの目的と操作方法がガイドされる
- [ ] ガイドは非表示にできる（経験者向け）

---

### FR-013: プレイ履歴

**Priority:** Could Have

**Description:**
過去のゲーム（キャラ・シナリオ・エンディング）を振り返れる。

**Acceptance Criteria:**
- [ ] 過去のゲーム一覧が表示される
- [ ] 各ゲームのキャラクター情報・エンディングが閲覧できる
- [ ] プレイ日時・参加者が記録される

---

### FR-014: シナリオテンプレート選択

**Priority:** Could Have

**Description:**
50パターンの中からプレイヤーがジャンル/雰囲気を選べる。

**Acceptance Criteria:**
- [ ] テンプレートのジャンル/雰囲気一覧が表示される
- [ ] ホストがテンプレートを選択してゲームを開始できる
- [ ] 「おまかせ」でランダム選択もできる

---

### FR-015: 調査フェーズの能動的探索

**Priority:** Must Have

**Description:**
調査フェーズでプレイヤーが場所や対象を選択して調査し、LLM（GM）が状況に応じた結果を返す。

**Acceptance Criteria:**
- [ ] 調査フェーズで調査可能な場所/対象の一覧が表示される
- [ ] プレイヤーが場所/対象を選択して「調査する」操作ができる
- [ ] LLM（GM）がプレイヤーの秘密・シナリオ進行状況に基づいて調査結果を生成する
- [ ] 調査結果が証拠カードとして手帳に追加される
- [ ] 調査回数やフェーズ内の制限が設定可能

**Dependencies:** FR-004, FR-005, FR-008

---

## Non-Functional Requirements

Non-Functional Requirements (NFRs) define **how** the system performs - quality attributes and constraints.

---

### NFR-001: パフォーマンス - LLM応答速度

**Priority:** Must Have

**Description:**
シナリオ生成・動的調整のLLM応答がプレイ体験を損なわないレベルであること。

**Acceptance Criteria:**
- [ ] シナリオ骨格生成が30秒以内に完了する
- [ ] フェーズごとの動的調整が10秒以内に完了する
- [ ] エンディング生成が15秒以内に完了する
- [ ] 待機中はローディングUI（演出）が表示される

**Rationale:**
対面プレイのため、長い待ち時間はプレイヤーの没入感を大きく損なう。

---

### NFR-002: パフォーマンス - WebSocket同期遅延

**Priority:** Must Have

**Description:**
ゲーム状態の同期遅延が体感できないレベルであること。

**Acceptance Criteria:**
- [ ] ゲーム状態同期の遅延が500ms以内

**Rationale:**
フェーズ遷移や発言権の排他制御がリアルタイムに反映されないとゲーム進行に支障が出る。

---

### NFR-003: パフォーマンス - 音声認識レイテンシ

**Priority:** Must Have

**Description:**
発言終了から文字起こし結果の表示までが素早いこと。

**Acceptance Criteria:**
- [ ] 発言終了から文字起こし表示まで3秒以内

**Rationale:**
発言権制のテンポ感を維持し、ゲーム進行をスムーズにするため。

---

### NFR-004: コスト - LLM APIコスト

**Priority:** Must Have

**Description:**
1ゲームあたりのLLM APIコストが課金モデルで採算が合うレベルであること。

**Acceptance Criteria:**
- [ ] 1ゲームあたりのLLM APIコストが1.5ドル以下
- [ ] コストがモニタリングされ、ゲームごとに記録される

**Rationale:**
1プレイ3〜5ドルの課金で、APIコストが30%以下に収まらないとビジネスモデルが成立しない。

---

### NFR-005: 信頼性 - ゲーム中断耐性

**Priority:** Must Have

**Description:**
ネットワーク一時切断時にゲーム状態が失われないこと。

**Acceptance Criteria:**
- [ ] プレイヤーのネットワーク切断時にゲームが中断しない（他プレイヤーは継続可能）
- [ ] 切断プレイヤーが再接続時に最新のゲーム状態を取得できる
- [ ] サーバーサイドでゲーム状態が永続化される

**Rationale:**
30〜60分のゲーム中にネットワーク切断が発生する可能性は高く、ゲーム全体が失われるのは致命的。

---

### NFR-006: セキュリティ - 秘密情報の隔離

**Priority:** Must Have

**Description:**
他プレイヤーの秘密情報がクライアント側に漏れないこと。

**Acceptance Criteria:**
- [ ] 各プレイヤーのクライアントには自分の秘密情報のみ送信される
- [ ] APIレスポンスに他プレイヤーの秘密情報が含まれない
- [ ] WebSocket経由のメッセージがプレイヤーごとにフィルタリングされる

**Rationale:**
マーダーミステリーの根幹は秘密情報。クライアント側で他者の情報が取得可能だとゲームが成立しない。

---

### NFR-007: ユーザビリティ - 初心者操作性

**Priority:** Should Have

**Description:**
マダミス未経験者が説明なしでゲーム参加・プレイできること。

**Acceptance Criteria:**
- [ ] 初回ユーザーがアプリ起動からゲーム参加まで2分以内で到達できる
- [ ] 主要操作（発言・メモ・投票）が直感的に理解できるUI

**Rationale:**
対面プレイのため、1人が操作に詰まると全員の体験が停滞する。

---

### NFR-008: 信頼性 - シナリオ整合性

**Priority:** Should Have

**Description:**
LLM生成シナリオにフェアな推理を破綻させる論理矛盾がないこと。

**Acceptance Criteria:**
- [ ] シナリオ生成後にバリデーションレイヤーで整合性チェックが実行される
- [ ] 矛盾検出時にLLMが再生成を試みる

**Rationale:**
推理が成立しないシナリオはゲーム体験を根本から壊す。

---

### NFR-009: 互換性 - iOS対応バージョン

**Priority:** Should Have

**Description:**
iOS 17以上をサポートすること。

**Acceptance Criteria:**
- [ ] iOS 17以上のiPhoneで動作する
- [ ] 最新のiOS（iOS 19）でも正常に動作する

**Rationale:**
SwiftUIの最新機能を活用しつつ、十分なユーザーカバレッジを確保する。

---

### NFR-010: スケーラビリティ - 同時ゲームセッション

**Priority:** Could Have

**Description:**
初期は小規模で十分だが、将来的なスケールに備えた設計にすること。

**Acceptance Criteria:**
- [ ] 同時に100セッション（最大700人）を処理できるアーキテクチャ設計
- [ ] 初期は10セッション程度の規模で運用可能

**Rationale:**
個人開発の初期フェーズではコストを抑えつつ、成長時にスケール可能な設計を維持する。

---

## Epics

Epics are logical groupings of related functionality that will be broken down into user stories during sprint planning (Phase 4).

Each epic maps to multiple functional requirements and will generate 2-10 stories.

---

### EPIC-001: キャラクター＆ルーム管理

**Description:**
プレイ開始前の準備フェーズ全体。キャラクター作成からルーム作成・参加・ゲーム状態同期まで。

**Functional Requirements:**
- FR-001: キャラクター作成
- FR-002: ルーム作成・参加
- FR-003: ゲーム状態同期

**Story Count Estimate:** 5〜7

**Priority:** Must Have

**Business Value:**
ゲームを開始するための基盤。プレイヤーが集まってキャラを作り、ゲームを始められなければ何も始まらない。

---

### EPIC-002: シナリオ生成＆動的調整

**Description:**
LLMによるシナリオの骨格生成、フェーズごとの動的調整、エンディング生成。マダミヌの核心的価値を提供するエピック。

**Functional Requirements:**
- FR-004: シナリオ骨格生成
- FR-008: フェーズごとのシナリオ動的調整
- FR-009: 投票・エンディング生成
- FR-014: シナリオテンプレート選択

**Story Count Estimate:** 6〜8

**Priority:** Must Have

**Business Value:**
「毎回違うシナリオ、毎回予測できないエンディング」というマダミヌの核心価値。このエピックがアプリの差別化要因。

---

### EPIC-003: ゲームプレイ進行

**Description:**
フェーズ管理、発言権制マイク入力、個人手帳、音声認識修正。プレイ中の体験全体。

**Functional Requirements:**
- FR-005: 個人手帳UI
- FR-006: フェーズ進行管理
- FR-007: 発言権制マイク入力
- FR-011: 音声認識結果の確認・修正
- FR-015: 調査フェーズの能動的探索

**Story Count Estimate:** 7〜10

**Priority:** Must Have

**Business Value:**
プレイヤーが実際にゲームを遊ぶためのインタラクション全体。操作性と没入感がリプレイ意欲を左右する。

---

### EPIC-004: 課金＆周辺機能

**Description:**
IAP課金、ゲーム進行ガイド、プレイ履歴。収益化とユーザー体験の補完機能。

**Functional Requirements:**
- FR-010: 1プレイ課金（IAP）
- FR-012: ゲーム進行ガイド
- FR-013: プレイ履歴

**Story Count Estimate:** 3〜5

**Priority:** Should Have

**Business Value:**
収益化の基盤と、初心者の定着・リピートを促す補完機能。

---

## User Stories (High-Level)

Detailed user stories will be created during sprint planning (Phase 4).

---

## User Personas

### Primary: マダミス初心者

マダミスに興味はあるが、固定シナリオの購入やルールの複雑さに敷居の高さを感じている層。スマホネイティブ世代が中心。友人同士で対面で集まって遊ぶシチュエーション。

**ニーズ:**
- 自分だけのキャラクターで物語に没入したい
- 難しいルールを覚えなくてもアプリがガイドしてほしい
- 同じメンバーで何度でも新鮮な体験をしたい

### Secondary: 配信者

マダミスの対面プレイを配信するエンターテイナー。毎回異なるシナリオが生成されるため、視聴者も飽きない。

### Secondary: マダミス経験者

固定シナリオを消費しきった層が、リプレイ可能な新しい体験を求めて利用。

---

## User Flows

### 1. ゲーム開始フロー（ホスト）
アプリ起動 → ルーム作成 → 参加コード共有 → プレイヤー集合確認 → キャラクター作成完了確認 → （課金） → ゲーム開始

### 2. ゲーム参加フロー（参加者）
アプリ起動 → 参加コード入力 → ルーム参加 → キャラクター作成 → ゲーム開始待ち

### 3. ゲームプレイフロー
シナリオ骨格生成（待機） → 秘密情報確認 → 調査フェーズ（証拠発見・発言） → 議論フェーズ（発言権制で議論） → 投票 → エンディング表示

---

## Dependencies

### Internal Dependencies

- バックエンドAPI（WebSocket + REST）
- LLM連携サービス（シナリオ生成・動的調整・エンディング生成）
- シナリオテンプレートデータ（約50パターン）

### External Dependencies

- LLM API（Claude / GPT等）
- 音声認識API（Apple Speech Framework / Whisper）
- Apple In-App Purchase API
- WebSocketサーバーインフラ

---

## Assumptions

- プレイヤーはiPhoneを持っている
- プレイヤーは対面で4〜7人集まれる環境がある
- LLM（Claude / GPT等）のAPIが安定して利用可能
- 音声認識の精度が対面会話で十分に機能する
- 1ゲーム30〜60分程度のプレイ時間を想定
- 発言権制がプレイ体験を損なわず、むしろ進行をスムーズにする

---

## Out of Scope

- Android版
- オンライン通話機能（対面プレイ前提）
- ユーザー作成シナリオの共有マーケットプレイス
- マッチング機能（知り合い同士で遊ぶ前提）
- 多言語対応（v1は日本語のみ）
- 配信者向け観戦モード

---

## Open Questions

1. LLM APIの選定（Claude vs GPT vs 併用）— コスト・品質のバランスで決定
2. 音声認識の実装方式（Apple Speech Framework vs Whisper API）— レイテンシとコストのトレードオフ
3. シナリオテンプレート50パターンの具体的な分類・構造
4. 発言権制と自由議論のハイブリッド進行の具体的なルール設計
5. バックエンドのインフラ選定（AWS / Railway等）

---

## Approval & Sign-off

### Stakeholders

- **katsut (開発者・オーナー)** - High. プロダクト全体の設計・開発・運営を担当。

### Approval Status

- [ ] Product Owner (katsut)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-24 | katsut | Initial PRD |

---

## Next Steps

### Phase 3: Architecture

Run `/architecture` to create system architecture based on these requirements.

The architecture will address:
- All functional requirements (FRs)
- All non-functional requirements (NFRs)
- Technical stack decisions
- Data models and APIs
- System components

### Phase 4: Sprint Planning

After architecture is complete, run `/sprint-planning` to:
- Break epics into detailed user stories
- Estimate story complexity
- Plan sprint iterations
- Begin implementation

---

**This document was created using BMAD Method v6 - Phase 2 (Planning)**

*To continue: Run `/workflow-status` to see your progress and next recommended workflow.*

---

## Appendix A: Requirements Traceability Matrix

| Epic ID | Epic Name | Functional Requirements | Story Count (Est.) |
|---------|-----------|-------------------------|-------------------|
| EPIC-001 | キャラクター＆ルーム管理 | FR-001, FR-002, FR-003 | 5〜7 |
| EPIC-002 | シナリオ生成＆動的調整 | FR-004, FR-008, FR-009, FR-014 | 6〜8 |
| EPIC-003 | ゲームプレイ進行 | FR-005, FR-006, FR-007, FR-011, FR-015 | 7〜10 |
| EPIC-004 | 課金＆周辺機能 | FR-010, FR-012, FR-013 | 3〜5 |

**Total Estimated Stories:** 21〜30

---

## Appendix B: Prioritization Details

### Functional Requirements

| Priority | Count | FRs |
|----------|-------|-----|
| Must Have | 10 | FR-001〜FR-009, FR-015 |
| Should Have | 3 | FR-010, FR-011, FR-012 |
| Could Have | 2 | FR-013, FR-014 |

### Non-Functional Requirements

| Priority | Count | NFRs |
|----------|-------|------|
| Must Have | 6 | NFR-001〜NFR-006 |
| Should Have | 3 | NFR-007, NFR-008, NFR-009 |
| Could Have | 1 | NFR-010 |

### Summary

- **Must Have:** FR 10件 + NFR 6件 = 16件
- **Should Have:** FR 3件 + NFR 3件 = 6件
- **Could Have:** FR 2件 + NFR 1件 = 3件
