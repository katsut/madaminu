"""Burn title text onto logo image."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = Path(__file__).parent.parent / "assets"
IOS_RESOURCES = Path(__file__).parent.parent / "ios" / "Madaminu" / "Sources" / "Resources"


def burn_title():
    logo = Image.open(ASSETS_DIR / "logo.png")
    draw = ImageDraw.Draw(logo)

    w, h = logo.size

    # Title: マダ見ヌ
    title_size = 96
    sub_size = 28

    # Try to use a nice serif/mincho font
    font_paths = [
        "/System/Library/Fonts/ヒラギノ明朝 ProN.ttc",
        "/System/Library/Fonts/HiraginoSerif.ttc",
        "/System/Library/Fonts/Supplemental/Hiragino Mincho ProN.ttc",
    ]

    title_font = None
    for fp in font_paths:
        if Path(fp).exists():
            title_font = ImageFont.truetype(fp, title_size)
            break

    if title_font is None:
        print("Mincho font not found, trying system fonts...")
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc", title_size)
        except OSError:
            title_font = ImageFont.load_default()

    sub_font_paths = [
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/System/Library/Fonts/Supplemental/Hiragino Kaku Gothic ProN.ttc",
    ]
    sub_font = None
    for fp in sub_font_paths:
        if Path(fp).exists():
            sub_font = ImageFont.truetype(fp, sub_size)
            break
    if sub_font is None:
        sub_font = ImageFont.load_default()

    # Dark overlay for readability
    overlay = Image.new("RGBA", logo.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle([(0, 0), (w, h)], fill=(0, 0, 0, 120))
    logo = Image.alpha_composite(logo.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(logo)

    # Title text with shadow
    title = "マダ見ヌ"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]
    title_h = title_bbox[3] - title_bbox[1]
    title_x = (w - title_w) // 2
    title_y = (h - title_h) // 2 - 30

    # Shadow layers
    for dx, dy, alpha in [(4, 4, 100), (2, 2, 140), (0, 0, 255)]:
        color = (200, 170, 100, alpha) if dx == 0 else (0, 0, 0, alpha)
        draw.text((title_x + dx, title_y + dy), title, font=title_font, fill=color)

    # Subtitle
    subtitle = "AI マーダーミステリー"
    sub_bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
    sub_w = sub_bbox[2] - sub_bbox[0]
    sub_x = (w - sub_w) // 2
    sub_y = title_y + title_h + 20

    draw.text((sub_x + 1, sub_y + 1), subtitle, font=sub_font, fill=(0, 0, 0, 180))
    draw.text((sub_x, sub_y), subtitle, font=sub_font, fill=(180, 180, 180, 220))

    # Save
    output = logo.convert("RGB")
    output.save(ASSETS_DIR / "logo_title.png", quality=95)
    output.save(IOS_RESOURCES / "logo.png", quality=95)
    print(f"Saved: {ASSETS_DIR / 'logo_title.png'}")
    print(f"Saved: {IOS_RESOURCES / 'logo.png'}")


if __name__ == "__main__":
    burn_title()
