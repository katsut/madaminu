# マダ見ヌ — AI マーダーミステリー

AIが生成するオリジナルシナリオで遊ぶ、対面型マーダーミステリーゲームアプリ。

## 概要

プレイヤーがキャラクターを作成すると、AIがシナリオ・マップ・関係性・秘密情報をすべて自動生成。
調査→議論→投票の3フェーズで犯人を推理します。

## 技術スタック

### サーバー
- Python 3.13 / FastAPI / SQLAlchemy (async)
- PostgreSQL (Railway)
- WebSocket (リアルタイム通信)
- OpenAI API (gpt-5.4-mini / gpt-image-1-mini)
- Alembic (DBマイグレーション)

### iOS
- Swift 6 / SwiftUI
- ObservableObject + @Published
- WebSocket + REST API
- Speech Framework (音声認識)

### インフラ
- Railway (サーバーデプロイ)

## ゲームの流れ

1. ルーム作成 → 参加者がキャラクターを作成
2. 全員「準備完了」→ ホストがゲーム開始
3. AIがシナリオ・マップ・画像を生成
4. **調査フェーズ**: 場所を選んで手がかりを収集
5. **議論フェーズ**: 発言ボタンで推理を議論
6. **投票フェーズ**: 犯人を投票
7. **エンディング**: 真相と個人目的の達成状況を発表

## 開発

```bash
# サーバー
cd server
uv run pytest -v
uv run ruff check src/ tests/

# iOS
cd ios/Madaminu
xcodebuild -project Madaminu.xcodeproj -scheme Madaminu \
  -destination 'platform=iOS Simulator,name=iPhone 17' build
```

## ライセンス

All Rights Reserved. 詳細は [LICENSE](LICENSE) を参照。
