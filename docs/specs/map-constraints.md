# マップ生成 原則と制約

## 原則

マップはマーダーミステリーの舞台となる建物・敷地の間取り図である。
プレイヤーが調査場所を選び、移動経路やアリバイを推理するために使う。

### 設計原則

1. **リアルな間取り**: 実在しそうな建物の構造にする。洋館なら洋館の、客船なら客船の間取り
2. **動線が推理の鍵**: 廊下・階段・玄関がボトルネックになり、「誰がどこを通ったか」がアリバイの根拠になる
3. **調査の選択肢**: 各ターンでプレイヤーが悩む程度の調査場所（最低8部屋）を用意する
4. **視認性**: SVGとしてスマートフォン画面で読めるサイズに収まる

## データ構造

```json
{
  "map": {
    "areas": [
      {
        "id": "area_id",
        "name": "エリア名",
        "area_type": "indoor|outdoor|semi_outdoor",
        "rooms": [
          {
            "id": "room_id",
            "name": "部屋名",
            "room_type": "room|corridor|entrance|stairs",
            "size": 1,
            "features": ["特徴1", "特徴2", "特徴3"]
          }
        ]
      }
    ],
    "connections": [
      {"from": "room_id_1", "to": "room_id_2", "type": "door|corridor|stairs|hidden_passage"}
    ]
  }
}
```

## room_type の定義

| room_type | 役割 | レンダリング | 調査対象 |
|-----------|------|-------------|---------|
| `room` | 普通の部屋（書斎、寝室等） | 正方形/長方形ノード | ○ |
| `corridor` | 廊下。部屋同士をつなぐハブ | 横長の薄いノード（backbone） | × |
| `entrance` | 玄関/出入口。屋内↔屋外の接続点 | 横長ノード（backbone） | × |
| `stairs` | 階段室。別フロアへの接続点 | 横長ノード + 段々模様（backbone） | × |

## connection type の定義

| type | 用途 | 制約 |
|------|------|------|
| `door` | 部屋 ↔ 廊下 | 部屋は必ず廊下経由 |
| `corridor` | 廊下 ↔ 廊下、屋外の小道 | backbone内の接続 |
| `stairs` | 階段 ↔ 別エリアの階段 | 異なるエリア間のみ |
| `hidden_passage` | 秘密の通路 | 非隣接でも可。1マップに0〜1個 |

## レンダラーの構造

SVGレンダラーは以下の構造でマップを描画する:

```
[エリア]
  backbone: entrance → corridor → corridor → stairs  (横一列)
  branches: 各corridorから上下に部屋が分岐
```

- **backbone**: corridor / entrance / stairs ノードが横一列に並ぶ
- **branch**: room ノードがbackboneノードから上下に分岐する
- row/col 座標は使用しない（LLMに指定させても無視される）

## 制約（MUST）

### 構造制約

| # | 制約 | 理由 |
|---|------|------|
| M1 | 屋内エリアには必ず1つ以上のcorridorを含める | レンダラーのbackbone構築に必須 |
| M2 | roomはcorridorにのみdoor接続する | room→room直接接続はレンダリングされない |
| M3 | 1つのcorridorに接続するroomは最大2つ | 3つ以上だと表示が重なる |
| M4 | stairsはcorridorにのみ接続する | 部屋→階段の直接接続は不可 |
| M5 | connectionは片方向のみ定義する | A→Bを定義したらB→Aは不要（双方向） |
| M6 | stairsタイプのconnectionは異なるエリア間のみ | 同エリア内のstairs接続は無効 |
| M7 | 各エリアに最低2つのroom（調査可能部屋）を含める | 調査の選択肢確保 |
| M8 | 全体で最低8つのroom（調査可能部屋） | ゲーム性の担保 |

### features 制約

| # | 制約 | 理由 |
|---|------|------|
| F1 | size=1の部屋: features 3個 | 調査ポイント数 |
| F2 | size=2の部屋: features 6個 | 調査ポイント数 |
| F3 | size=3の部屋: features 9個 | 調査ポイント数 |
| F4 | corridor/entrance/stairs: features不要 | 調査対象外 |

### 接続制約

| # | 制約 | 理由 |
|---|------|------|
| C1 | room→roomの直接接続は禁止 | 必ずcorridor経由 |
| C2 | stairs→roomの直接接続は禁止 | 必ずcorridor経由 |
| C3 | 複数階がある場合、各フロアにstairsを配置 | フロア間移動の経路確保 |
| C4 | 犯行現場は2つ以上の接続を持つ | 複数の逃走経路＝推理の余地 |

## 推奨（SHOULD）

| # | 推奨 | 理由 |
|---|------|------|
| S1 | 3〜5エリア、合計15〜20部屋 | 適度な広さ |
| S2 | 屋内エリアにはentranceを含める | 屋外への出入り口 |
| S3 | 行き止まりの部屋を1〜2個含める | 密室トリックの可能性 |
| S4 | 廊下が多い場合は複数ノードに分割 | M3制約のため |
| S5 | 各エリアのcorridor数 ≥ ceil(room数 / 2) | M3制約を満たすため |

## 現状の問題と対策

### 問題1: LLMがルールを無視する

LLMに多数のルールを文章で伝えても守られないことが多い。

**対策案**:
- サーバー側でバリデーション＋自動修正を行う
- room→room接続をroom→corridor→roomに自動変換
- 1corridorに3部屋以上接続していたらcorridorを分割
- corridorがないエリアに自動追加

### 問題2: row/colが無意味

レンダラーはrow/colを使わず、backbone→branch構造で描画する。

**対策案**:
- LLMプロンプトからrow/colの指定を削除
- 代わりにbackbone順序（entrance→corridor→stairs）を明示

### 問題3: バリデーションがない

LLM出力をそのまま使っており、制約違反がチェックされない。

**対策案**:
- `validate_map()` 関数を追加
- 制約M1〜M8をプログラムでチェック
- 違反があればLLMに修正を依頼、またはサーバー側で自動修正
