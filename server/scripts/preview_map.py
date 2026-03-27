"""Generate map SVG previews for visual testing.

Usage:
    cd server && uv run python scripts/preview_map.py
    open /tmp/map_preview.html
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from madaminu.services.map_renderer import render_map_svg

# Graph-based map: nodes + edges, sugoroku style
# Passage nodes form backbone, room nodes branch off
# size: 1=small, 2=medium, 4=large

MANSION_MAP = {
    "areas": [
        {
            "id": "main_1f", "name": "本館1階", "area_type": "indoor",
            "nodes": [
                {"id": "entrance", "name": "玄関", "type": "entrance", "features": ["大きな鏡"]},
                {"id": "c1f_1", "name": "廊下", "type": "passage"},
                {"id": "c1f_2", "name": "廊下", "type": "passage"},
                {"id": "c1f_3", "name": "廊下", "type": "passage"},
                {"id": "c1f_4", "name": "廊下", "type": "passage"},
                {"id": "c1f_5", "name": "廊下", "type": "passage"},
                {"id": "stairs_1f", "name": "階段", "type": "stairs"},
                {"id": "living", "name": "リビング", "type": "room", "size": 4, "features": ["暖炉", "ソファ", "グランドピアノ", "絵画"]},
                {"id": "cloakroom", "name": "クローク", "type": "room", "size": 1, "features": ["コート掛け"]},
                {"id": "dining", "name": "ダイニング", "type": "room", "size": 2, "features": ["大テーブル", "食器棚"]},
                {"id": "toilet_1f", "name": "トイレ", "type": "room", "size": 1, "features": ["手洗い場"]},
                {"id": "kitchen", "name": "台所", "type": "room", "size": 1, "features": ["包丁セット"]},
                {"id": "bathroom", "name": "浴室", "type": "room", "size": 1, "features": ["浴槽"]},
                {"id": "study", "name": "書斎", "type": "room", "size": 2, "features": ["デスク", "金庫", "本棚"]},
                {"id": "storage", "name": "物置", "type": "room", "size": 1, "features": ["工具箱", "ロープ"]},
                {"id": "laundry", "name": "洗濯室", "type": "room", "size": 1, "features": ["洗濯機"]},
            ],
            "edges": [
                ["entrance", "c1f_1"],
                ["c1f_1", "c1f_2"],
                ["c1f_2", "c1f_3"],
                ["c1f_3", "c1f_4"],
                ["c1f_4", "c1f_5"],
                ["c1f_5", "stairs_1f"],
                ["c1f_1", "living"],
                ["c1f_1", "cloakroom"],
                ["c1f_2", "dining"],
                ["c1f_2", "toilet_1f"],
                ["c1f_3", "kitchen"],
                ["c1f_3", "bathroom"],
                ["c1f_4", "study"],
                ["c1f_4", "storage"],
                ["c1f_5", "laundry"],
            ],
        },
        {
            "id": "main_2f", "name": "本館2階", "area_type": "indoor",
            "nodes": [
                {"id": "c2f_1", "name": "廊下", "type": "passage"},
                {"id": "c2f_2", "name": "廊下", "type": "passage"},
                {"id": "c2f_3", "name": "廊下", "type": "passage"},
                {"id": "c2f_4", "name": "廊下", "type": "passage"},
                {"id": "stairs_2f", "name": "階段", "type": "stairs"},
                {"id": "master_bed", "name": "主寝室", "type": "room", "size": 4, "features": ["キングベッド", "日記", "クローゼット"]},
                {"id": "dressing", "name": "化粧室", "type": "room", "size": 1, "features": ["鏡台"]},
                {"id": "guest_a", "name": "客室A", "type": "room", "size": 2, "features": ["旅行鞄", "シングルベッド"]},
                {"id": "toilet_2f", "name": "トイレ", "type": "room", "size": 1, "features": ["手洗い場"]},
                {"id": "guest_b", "name": "客室B", "type": "room", "size": 1, "features": ["化粧台"]},
                {"id": "guest_c", "name": "客室C", "type": "room", "size": 1, "features": ["旅行鞄"]},
                {"id": "balcony", "name": "バルコニー", "type": "room", "size": 2, "features": ["手すり", "望遠鏡"]},
                {"id": "linen", "name": "リネン室", "type": "room", "size": 1, "features": ["タオル", "シーツ"]},
            ],
            "edges": [
                ["c2f_1", "c2f_2"],
                ["c2f_2", "c2f_3"],
                ["c2f_3", "c2f_4"],
                ["c2f_4", "stairs_2f"],
                ["c2f_1", "master_bed"],
                ["c2f_1", "dressing"],
                ["c2f_2", "guest_a"],
                ["c2f_2", "toilet_2f"],
                ["c2f_3", "guest_b"],
                ["c2f_3", "guest_c"],
                ["c2f_4", "balcony"],
                ["c2f_4", "linen"],
            ],
        },
        {
            "id": "basement", "name": "地下室", "area_type": "indoor",
            "nodes": [
                {"id": "c_b1", "name": "廊下", "type": "passage"},
                {"id": "stairs_b1", "name": "階段", "type": "stairs"},
                {"id": "wine_cellar", "name": "ワインセラー", "type": "room", "size": 2, "features": ["ワイン棚", "温度計"]},
                {"id": "boiler", "name": "ボイラー室", "type": "room", "size": 1, "features": ["ボイラー", "配管"]},
            ],
            "edges": [
                ["c_b1", "stairs_b1"],
                ["c_b1", "wine_cellar"],
                ["c_b1", "boiler"],
            ],
        },
        {
            "id": "garden", "name": "庭園", "area_type": "outdoor",
            "nodes": [
                {"id": "front_garden", "name": "前庭", "type": "room", "size": 4, "features": ["噴水", "バラ園"]},
                {"id": "greenhouse", "name": "温室", "type": "room", "size": 2, "features": ["熱帯植物", "園芸道具"]},
                {"id": "gazebo", "name": "東屋", "type": "room", "size": 1, "features": ["ベンチ"]},
                {"id": "shed", "name": "離れ小屋", "type": "room", "size": 1, "features": ["古新聞", "錆びた鍵"]},
            ],
            "edges": [
                ["front_garden", "greenhouse"],
                ["greenhouse", "gazebo"],
                ["front_garden", "shed"],
            ],
        },
    ],
    "floor_connections": [
        ["stairs_1f", "stairs_2f"],
        ["stairs_1f", "stairs_b1"],
        ["entrance", "front_garden"],
    ],
}

SCHOOL_MAP = {
    "areas": [
        {
            "id": "school_1f", "name": "校舎1階", "area_type": "indoor",
            "nodes": [
                {"id": "s_entrance", "name": "昇降口", "type": "entrance", "features": ["下駄箱"]},
                {"id": "sc1_1", "name": "廊下", "type": "passage"},
                {"id": "sc1_2", "name": "廊下", "type": "passage"},
                {"id": "sc1_3", "name": "廊下", "type": "passage"},
                {"id": "sc1_4", "name": "廊下", "type": "passage"},
                {"id": "stairs_s1f", "name": "階段", "type": "stairs"},
                {"id": "staff_room", "name": "職員室", "type": "room", "size": 2, "features": ["鍵付きロッカー", "コピー機"]},
                {"id": "nurse", "name": "保健室", "type": "room", "size": 1, "features": ["薬品棚"]},
                {"id": "science", "name": "理科室", "type": "room", "size": 2, "features": ["実験器具", "人体模型"]},
                {"id": "art_room", "name": "美術室", "type": "room", "size": 2, "features": ["イーゼル", "石膏像"]},
                {"id": "toilet_1f", "name": "トイレ", "type": "room", "size": 1, "features": ["手洗い場"]},
            ],
            "edges": [
                ["s_entrance", "sc1_1"],
                ["sc1_1", "sc1_2"],
                ["sc1_2", "sc1_3"],
                ["sc1_3", "sc1_4"],
                ["sc1_4", "stairs_s1f"],
                ["sc1_1", "staff_room"],
                ["sc1_2", "nurse"],
                ["sc1_2", "toilet_1f"],
                ["sc1_3", "science"],
                ["sc1_4", "art_room"],
            ],
        },
        {
            "id": "school_2f", "name": "校舎2階", "area_type": "indoor",
            "nodes": [
                {"id": "sc2_1", "name": "廊下", "type": "passage"},
                {"id": "sc2_2", "name": "廊下", "type": "passage"},
                {"id": "sc2_3", "name": "廊下", "type": "passage"},
                {"id": "sc2_4", "name": "廊下", "type": "passage"},
                {"id": "stairs_s2f", "name": "階段", "type": "stairs"},
                {"id": "class_a", "name": "2年A組", "type": "room", "size": 2, "features": ["黒板", "掃除ロッカー"]},
                {"id": "class_b", "name": "2年B組", "type": "room", "size": 2, "features": ["黒板"]},
                {"id": "music", "name": "音楽室", "type": "room", "size": 2, "features": ["グランドピアノ", "防音壁"]},
                {"id": "library", "name": "図書室", "type": "room", "size": 4, "features": ["書架", "閲覧席", "司書デスク"]},
                {"id": "prep_room", "name": "準備室", "type": "room", "size": 1, "features": ["薬品棚", "鍵"]},
            ],
            "edges": [
                ["sc2_1", "sc2_2"],
                ["sc2_2", "sc2_3"],
                ["sc2_3", "sc2_4"],
                ["sc2_4", "stairs_s2f"],
                ["sc2_1", "class_a"],
                ["sc2_2", "class_b"],
                ["sc2_2", "prep_room"],
                ["sc2_3", "music"],
                ["sc2_4", "library"],
            ],
        },
        {
            "id": "school_ground", "name": "校庭", "area_type": "outdoor",
            "nodes": [
                {"id": "ground", "name": "運動場", "type": "room", "size": 4, "features": ["ゴール", "砂場"]},
                {"id": "pool", "name": "プール", "type": "room", "size": 2, "features": ["塩素タンク", "更衣室"]},
                {"id": "gym", "name": "体育館", "type": "room", "size": 4, "features": ["バスケットゴール", "ステージ"]},
                {"id": "incinerator", "name": "焼却炉", "type": "room", "size": 1, "features": ["灰"]},
            ],
            "edges": [
                ["ground", "pool"],
                ["ground", "gym"],
                ["pool", "incinerator"],
            ],
        },
    ],
    "floor_connections": [
        ["stairs_s1f", "stairs_s2f"],
        ["s_entrance", "ground"],
    ],
}

SCENARIOS = [
    ("洋館シナリオ", MANSION_MAP, "living"),
    ("学園シナリオ", SCHOOL_MAP, "science"),
]

OUTPUT_PATH = Path("/tmp/map_preview.html")


def main():
    sections = []
    for title, map_data, highlight_id in SCENARIOS:
        svg_normal = render_map_svg(map_data)
        svg_highlight = render_map_svg(map_data, highlight_room=highlight_id)

        sections.append(f"""
        <section>
            <h2>{title}</h2>
            <h3>通常表示</h3>
            <div class="map-container">{svg_normal}</div>
            <h3>ハイライト（{highlight_id}）</h3>
            <div class="map-container">{svg_highlight}</div>
        </section>
        """)

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>マダミヌ MAP プレビュー</title>
<style>
    body {{ font-family: -apple-system, sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }}
    h1 {{ text-align: center; color: #cc9944; }}
    h2 {{ color: #8888cc; border-bottom: 1px solid #333; padding-bottom: 8px; }}
    h3 {{ color: #999; font-size: 14px; }}
    .map-container {{
        background: #111118; border: 1px solid #333; border-radius: 8px;
        padding: 10px; margin: 10px 0 30px; overflow-x: auto;
    }}
    .map-container svg {{ display: block; max-width: 100%; height: auto; }}
</style>
</head>
<body>
<h1>マダミヌ MAP プレビュー</h1>
{"".join(sections)}
</body>
</html>"""

    OUTPUT_PATH.write_text(html)
    print(f"Preview: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
