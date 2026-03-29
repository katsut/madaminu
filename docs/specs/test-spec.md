# テスト仕様書

## 概要

サーバー側のテストは `server/tests/` に配置。全テストは `uv run pytest tests/ -v` で実行可能。

- テスト総数: 121 (+ 7 skipped)
- フレームワーク: pytest + pytest-asyncio
- DB: SQLite in-memory (aiosqlite)
- LLM: モック (unittest.mock.patch)

## テスト一覧

### test_characters.py — キャラクター作成 API

| テスト | 検証内容 |
|-------|---------|
| test_create_character | キャラクター作成が成功する |
| test_create_character_visible_in_room | 作成したキャラがルーム情報に反映される |
| test_create_character_invalid_token | 不正トークンで403 |
| test_create_character_nonexistent_room | 存在しないルームで404 |
| test_create_character_empty_name | 空の名前でバリデーションエラー |

### test_rooms.py — ルーム CRUD

| テスト | 検証内容 |
|-------|---------|
| test_create_room | ルーム作成が成功し、room_code が返る |
| test_create_room_empty_name | 空の名前で400 |
| test_join_room | ルーム参加が成功し、player_id が返る |
| test_join_nonexistent_room | 存在しないルームで400 |
| test_get_room | ルーム詳細が取得できる |
| test_get_nonexistent_room | 存在しないルームで404 |
| test_room_max_players | 最大人数超過で400 |

### test_room_name.py — ルーム名

| テスト | 検証内容 |
|-------|---------|
| test_create_room_with_name | ルーム名付きで作成、詳細に反映 |
| test_create_room_without_name | 名前なしで作成、null |
| test_room_name_in_list | ルーム一覧にルーム名が表示 |

### test_rejoin.py — device_id 再参加

| テスト | 検証内容 |
|-------|---------|
| test_rejoin_same_device_returns_existing_player | 同デバイスで再参加→既存プレイヤーを返す（session_token更新） |
| test_rejoin_different_device_creates_new_player | 別デバイスで参加→新プレイヤー作成 |
| test_rejoin_preserves_host | ホストが再参加してもホスト権限維持 |

### test_e2e.py — E2E テスト

| テスト | 検証内容 | 状態 |
|-------|---------|------|
| test_full_game_lifecycle_http | ルーム作成→参加→キャラ作成→ready→ゲーム開始 (HTTP) | ✅ |
| test_room_state_after_game_start | ゲーム開始後のルーム状態確認 | ✅ |
| test_full_game_flow_with_websocket | WS: ルーム→開始→フェーズ→投票→エンディング | skip |
| test_websocket_investigation_flow | WS: 調査フロー | skip |
| test_websocket_speech_flow | WS: 発言フロー | skip |
| test_multiplayer_websocket_interaction | WS: マルチプレイヤー | skip |
| test_voting_and_ending_flow | WS: 投票→エンディング | skip |
| test_duplicate_vote_rejected | WS: 二重投票拒否 | skip |
| test_non_host_cannot_advance_phase | WS: 非ホストのフェーズ進行拒否 | skip |

※ WS テストは Sync TestClient + aiosqlite の互換性問題でスキップ中

### test_scenario.py — シナリオ生成・ゲーム開始

| テスト | 検証内容 |
|-------|---------|
| test_start_game_endpoint | ゲーム開始 API が成功、status=generating |
| test_start_game_not_host | 非ホストからの開始要求で403 |
| test_start_game_not_ready | 未ready プレイヤーがいると400 |
| test_start_game_not_enough_characters | キャラ不足時にAI補充 |
| test_parse_scenario_json | JSON パーサーの正常系 |
| test_parse_scenario_json_with_markdown | マークダウン付きJSONのパース |

### test_investigation.py — 調査ロジック

| テスト | 検証内容 |
|-------|---------|
| test_investigate_location_success | 場所調査が成功し、title/content を返す |
| test_investigate_invalid_location | 存在しない場所で None |
| test_investigate_multiple_features | 複数 feature の調査 |
| test_investigate_wrong_phase_type | investigation 以外のフェーズで None |
| test_keep_evidence_saves_to_db | 証拠保持が DB に保存される |
| test_investigate_uses_haiku_model | 調査に nano モデルが使われる |

### test_phase_manager.py — フェーズ遷移

| テスト | 検証内容 |
|-------|---------|
| test_start_first_phase | 最初のフェーズ開始、current_phase_id 設定 |
| test_advance_phase | 次フェーズへの進行 |
| test_advance_to_voting_updates_game_status | 投票フェーズで game.status = voting |
| test_advance_past_last_phase_ends_game | 最後のフェーズ後に game.status = ended |
| test_extend_phase | フェーズ延長 (+60秒) |
| test_cleanup_cancels_timer | cleanup でタイマーキャンセル |
| test_advance_cancels_previous_timer | advance でタイマー再設定 |
| test_get_current_phase_dict | フェーズ情報の dict 取得 |
| test_get_current_phase_dict_not_found | フェーズ未設定時 None |
| test_no_phases_raises | フェーズ0件で ValueError |

### test_phase_adjustment.py — フェーズ調整

| テスト | 検証内容 |
|-------|---------|
| test_adjust_phase_distributes_evidence | 追加証拠の配布 |
| test_adjust_phase_no_evidence | 証拠なしの場合 |
| test_adjust_phase_speech_logs_included | 発言ログがプロンプトに含まれる |
| test_adjust_phase_updates_gm_state | GM 状態の更新 |
| test_adjust_phase_invalid_player_id_skipped | 不正プレイヤーID スキップ |

### test_timer_resilience.py — タイマー耐障害性

| テスト | 検証内容 |
|-------|---------|
| test_timer_advances_after_broadcast_failure | broadcast 失敗後もタイマー継続→advance_phase 呼出 |
| test_voting_timer_does_not_auto_advance | 投票フェーズはタイマーで自動進行しない |

### test_speech_manager.py — 発言権管理

| テスト | 検証内容 |
|-------|---------|
| test_request_speech_granted | 発言権取得成功 |
| test_request_speech_preempts_current_speaker | 割り込みで前の発言者をキャンセル |
| test_release_speech | 発言終了 |
| test_release_by_wrong_player_fails | 別プレイヤーの release 失敗 |
| test_release_saves_transcript | release 時に SpeechLog 保存 |
| test_release_empty_transcript_skips_save | 空文字の transcript は保存しない |
| test_second_player_can_speak_after_release | release 後に別プレイヤーが発言可 |
| test_force_release | 強制 release |
| test_cleanup_room | ルーム cleanup |
| test_get_current_speaker_no_room | 未存在ルームで None |

### test_speech_preempt.py — 発言割り込み

| テスト | 検証内容 |
|-------|---------|
| test_preempt_releases_current_speaker | B のリクエストで A が自動 release、broadcast_speech_released 呼出 |
| test_same_player_request_returns_true | 同一プレイヤーの再リクエストは True |

### test_voting_ending.py — 投票・エンディング

| テスト | 検証内容 |
|-------|---------|
| test_generate_ending | エンディング生成が成功、ending_text/true_criminal_id 取得 |
| test_generate_ending_includes_votes_in_prompt | 投票結果がプロンプトに含まれる |
| test_generate_ending_includes_speech_in_prompt | 発言ログがプロンプトに含まれる |
| test_vote_duplicate_prevention | 二重投票が拒否される |
| test_format_votes | 投票結果フォーマットの正しさ |

### test_map_builder.py — マップグラフ構築

| テスト | 検証内容 |
|-------|---------|
| test_indoor_adds_entrance_corridor_stairs | 屋内エリアに玄関・廊下・階段が追加される |
| test_single_area_no_stairs | 単一エリアでは階段なし |
| test_max_2_rooms_per_corridor | 1廊下あたり最大2部屋 |
| test_corridor_count_matches_rooms | 廊下数 ≥ ceil(部屋数/2) |
| test_outdoor_no_corridor | 屋外エリアに廊下なし |
| test_floor_connections | フロア間の階段接続 |
| test_crime_scene_from_victim | victim.crime_scene_room_id から犯行現場設定 |
| test_crime_scene_fallback | 未設定時の自動割当 |
| test_indoor_outdoor_connection | 屋内玄関→屋外の接続 |
| test_basic_output | ルートテキストに部屋名・動線・犯行現場 |
| test_player_positions | ルートテキストにキャラ居場所 |
| test_generates_narrative | 移動ナラティブ生成 |
| test_companions_mentioned | 同行者の言及 |

### test_map_renderer.py — SVG マップレンダリング

| テスト | 検証内容 |
|-------|---------|
| test_render_produces_svg | SVG が生成される |
| test_render_contains_area_names | エリア名が含まれる |
| test_render_contains_room_names | 部屋名が含まれる |
| test_render_no_features_on_map | features はマップに表示されない |
| test_render_contains_stairs | 階段が含まれる |
| test_render_contains_legend | 凡例が含まれる |
| test_render_has_aria_label | アクセシビリティ属性 |
| test_render_highlight_has_glow | ハイライト時のグロー効果 |
| test_render_area_icons | エリアアイコン (🏠🌳⛺) |
| test_render_svg_title | SVG title 要素 |
| test_render_area_aria_group | エリアの aria-label グループ |
| test_render_flat_map_fallback | フラットマップのフォールバック |
| test_render_empty_map | 空マップ |
| test_render_outdoor_area_has_dashed_border | 屋外エリアの破線枠 |

### test_map_validation.py — マップバリデーション

| テスト | 検証内容 |
|-------|---------|
| test_valid_scenario | 正常なシナリオが通る |
| test_missing_map | map なしでエラー |
| test_unknown_connection_from | 不正な from でエラー |
| test_unknown_connection_to | 不正な to でエラー |
| test_invalid_connection_type | 不正な接続タイプでエラー |
| test_isolated_room | 孤立部屋でエラー |
| test_duplicate_room_id | 重複 ID でエラー |
| test_room_without_features | features なしでエラー |
| test_empty_area | 空エリアでエラー |
| test_invalid_area_type | 不正な area_type でエラー |
| test_too_few_rooms | 部屋不足でエラー |
| test_phase_references_unknown_room | フェーズが不明部屋を参照でエラー |
| test_resolve_from_dict | dict 形式の解決 |
| test_resolve_from_hierarchical | 階層形式の解決 |
| test_resolve_skips_unknown | 不明 ID のスキップ |

### test_models.py — DB モデル

| テスト | 検証内容 |
|-------|---------|
| test_create_game | Game レコード作成 |
| test_create_player | Player レコード作成 |

### test_llm.py — LLM・テンプレート

| テスト | 検証内容 |
|-------|---------|
| test_llm_usage_cost_mini | mini モデルのコスト計算 |
| test_llm_usage_cost_nano | nano モデルのコスト計算 |
| test_render_template | テンプレートレンダリング |
| test_format_characters | キャラクター情報フォーマット |
| test_template_files_exist | テンプレートファイルの存在確認 |

### test_health.py — ヘルスチェック

| テスト | 検証内容 |
|-------|---------|
| test_health_check | /health が 200 を返す |

### test_websocket.py — WS 接続

| テスト | 検証内容 |
|-------|---------|
| test_websocket_connect_and_receive_state | WS 接続→game.state 受信 |
| test_websocket_invalid_token | 不正トークンで WS 切断 |
| test_websocket_no_token | トークンなしで WS 切断 |
| test_websocket_player_connect_notification | 接続通知ブロードキャスト |
| test_websocket_secret_info_isolation | 秘密情報が他プレイヤーに漏れない |

## テストカバレッジ マトリクス

| 機能領域 | テストファイル | テスト数 | カバー状況 |
|---------|-------------|---------|-----------|
| ルーム管理 | test_rooms, test_room_name, test_rejoin | 13 | ○ |
| キャラクター | test_characters | 5 | ○ |
| シナリオ生成 | test_scenario | 6 | ○ |
| 調査ロジック | test_investigation | 6 | ○ |
| フェーズ管理 | test_phase_manager | 10 | ○ |
| フェーズ調整 | test_phase_adjustment | 5 | ○ |
| タイマー | test_timer_resilience | 2 | ○ |
| 発言権 | test_speech_manager, test_speech_preempt | 12 | ○ |
| 投票・エンディング | test_voting_ending | 5 | ○ |
| マップ構築 | test_map_builder | 13 | ○ |
| マップ描画 | test_map_renderer | 14 | ○ |
| マップ検証 | test_map_validation | 15 | ○ |
| WebSocket | test_websocket | 5 | ○ |
| E2E (HTTP) | test_e2e | 2 | ○ |
| E2E (WS) | test_e2e | 7 | skip |
| DB モデル | test_models | 2 | ○ |
| LLM | test_llm | 5 | ○ |
| ヘルス | test_health | 1 | ○ |
| **合計** | **18ファイル** | **128** | |

## 未カバー領域

| 機能 | 理由 |
|------|------|
| iOS クライアント | Swift テスト未実装 |
| WS E2E (投票→エンディング等) | aiosqlite 互換性問題でスキップ |
| AIキャラクター動的生成 | LLM呼び出しのモック必要 |
| 画像生成 | OpenAI API のモック必要 |
| game.generation_failed → ロビー復帰 | E2E WS テスト内で検証予定 |

## テスト実行方法

```bash
cd server

# 全テスト
uv run pytest tests/ -v

# 特定ファイル
uv run pytest tests/test_map_builder.py -v

# 特定テスト
uv run pytest tests/test_map_builder.py::TestBuildMapStructure::test_max_2_rooms_per_corridor -v

# カバレッジ付き
uv run pytest tests/ --cov=madaminu --cov-report=term-missing

# lint
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```
