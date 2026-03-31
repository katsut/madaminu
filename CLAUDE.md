# マダミヌ プロジェクト CLAUDE.md

## セッション開始時に読むこと

作業を始める前に、以下の仕様書を必ず読み込むこと:

1. [docs/specs/architecture-v3.md](docs/specs/architecture-v3.md) — アーキテクチャ、フェーズ一覧、通信設計、シーン切り替え、データ管理
2. [docs/specs/class-design-v3.md](docs/specs/class-design-v3.md) — デザインパターン、モジュール構成、クラス設計
3. [docs/specs/message-design-v3.md](docs/specs/message-design-v3.md) — WS メッセージ定義、バリデーション、シーケンス図

## アーキテクチャ（v3）

### 設計原則
1. **全状態は DB に永続化** — メモリ内状態ゼロ
2. **WS でゲーム通信、HTTP はゲーム外操作** — 役割を明確に分離
3. **フォールバック禁止** — 根本原因を修正する
4. **不要な try-catch 禁止** — 起きるはずのない例外は握りつぶさない
5. **LLM は WS をブロックしない** — バックグラウンドジョブで実行
6. **サーバーはバリデーションを都度行う** — 同じメッセージが2回来ても安全

### サーバー (Python/FastAPI)
- WS Handler → WS Actions → Service → Repository → DB
- Jobs（LLM 呼び出し）は Service と同じ層。create_task で起動
- Alembic で DB マイグレーション
- OpenAI gpt-5.4-mini/nano (LLM), gpt-image-1 (画像生成)

### iOS (Swift/SwiftUI)
- AppStore (ObservableObject) → WS 送信 / WS 受信
- GameStateSync で game.state の差分検出 → シーン切り替え
- PhaseScreenState: active / transitioning
- ObservableObject + @Published（@Observable は使わない）
- async メソッドに @MainActor、クラスには付けない

### 通信
- **WS**: ゲーム中の全通信（アクション送信 + 通知受信）
- **HTTP**: ゲーム外操作（ルーム作成・参加・キャラ作成）と静的リソース（画像）
- WS 接続時にサーバーが game.state を自動送信
- サーバーが 20秒間隔で ping 送信

## 開発ルール

### コマンド
- サーバー: `cd server && uv run pytest -v` / `uv run ruff check src/ tests/`
- iOS: `cd ios/Madaminu && xcodebuild -project Madaminu.xcodeproj -scheme Madaminu -destination 'platform=iOS Simulator,name=iPhone 17' build`

### DBマイグレーション
```bash
cd server
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```
Dockerfile で起動時に自動実行。

### デプロイ
- サーバー: Railway (Docker, GitHub 連携で自動デプロイ)
- URL: https://murder-production.up.railway.app

### 実装ルール
- **フォールバック処理に逃げない**: 本来の処理が失敗するケースを根本から解決する
- **不要な try-catch を書かない**: 起きるはずのない例外を握りつぶさない。外部 API 呼び出し等、本当に失敗し得る箇所のみ
- **全ゲーム状態は DB に永続化**: メモリ内状態に依存しない
- **LLM 呼び出し中は DB セッションを保持しない**: 取得 → セッション閉じる → LLM → セッション開く → 保存
- **バグ修正時には必ず再現テストを追加する**

### 注意事項
- `@Observable` は使わない（Main Thread Checker でクラッシュ）
- WebSocket コールバック内は必ず `DispatchQueue.main.async`
- `create_all` は使わない（Alembic で管理）
