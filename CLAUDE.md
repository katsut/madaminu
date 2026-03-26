# マダミヌ プロジェクト CLAUDE.md

## アーキテクチャ

詳細: [docs/architecture-v2.md](docs/architecture-v2.md)

### サーバー (Python/FastAPI)
- Router → Service → Repository → DB
- EventBus でサービス間疎結合
- Alembic でDBマイグレーション
- WebSocket でリアルタイムイベント配信
- OpenAI gpt-5.4-mini/nano (LLM), gpt-image-1 (画像生成)

### iOS (Swift/SwiftUI)
- AppStore (ObservableObject) → dispatch(AppAction) → API/WebSocket
- Store分割: RoomStore / GamePlayStore / NotebookStore
- WSMessageAdapter でメッセージ→状態変換
- ObservableObject + @Published（@Observable は使わない）
- async メソッドに @MainActor、クラスには付けない

## 開発ルール

### コマンド
- サーバー: `cd server && uv run pytest -v` / `uv run ruff check src/ tests/`
- iOS: `cd ios/Madaminu && xcodebuild -project Madaminu.xcodeproj -scheme Madaminu -destination 'platform=iOS Simulator,name=iPhone 17' build`
- デプロイ: `railway up`

### DBマイグレーション
```bash
cd server
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```
Dockerfile で起動時に自動実行。

### デプロイ
- サーバー: Railway (Docker)
- URL: https://murder-production.up.railway.app
- 環境変数: MADAMINU_DATABASE_URL, MADAMINU_OPENAI_API_KEY

### 注意事項
- `@Observable` は使わない（Main Thread Checker でクラッシュ）
- WebSocket コールバック内は必ず `DispatchQueue.main.async`
- `create_all` は使わない（Alembic で管理）
- iOS の PlayerInfo は欠損フィールドに対応する `init(from:)` を持つ
