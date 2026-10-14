"""画像の自動加工（比率変換・明るさ補正・透かし・縮小）。

「スマホで撮った縦長の1枚」を、Xでは16:9、Instagramでは4:5…と
SNSごとに最適な形へ整えるのが役割。
"""
from __future__ import annotations

import pathlib
from typing import Tuple

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

RATIOS = {
    "1:1": (1, 1),
    "4:5": (4, 5),
    "16:9": (16, 9),
    "9:16": (9, 16),
}


def _font(size: int):
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    ):
        if pathlib.Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def prepare(
    src: str,
    dst: str,
    ratio: str = "4:5",
    watermark: str | None = None,
    watermark_opacity: int = 110,
    autocontrast: bool = True,
    max_side: int = 1440,
    quality: int = 88,
) -> Tuple[str, Tuple[int, int]]:
    """1枚を指定比率のJPEGに整えて保存する。戻り値=(保存先, サイズ)。"""
    img = Image.open(src)
    img = ImageOps.exif_transpose(img)          # スマホ写真の回転情報を反映
    if img.mode != "RGB":
        img = img.convert("RGB")

    # --- 比率合わせ（中央基準で切り出す。猫はたいてい中央にいる）---
    rw, rh = RATIOS.get(ratio, (4, 5))
    w, h = img.size
    target = rw / rh
    if w / h > target:                          # 横に広すぎる → 左右を詰める
        new_w = int(h * target)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    else:                                       # 縦に長すぎる → 上下を詰める（やや上寄り）
        new_h = int(w / target)
        top = int((h - new_h) * 0.35)
        img = img.crop((0, top, w, top + new_h))

    # --- 明るさ・コントラストの自動補正 ---
    if autocontrast:
        img = ImageOps.autocontrast(img, cutoff=1)
        img = ImageEnhance.Color(img).enhance(1.06)
        img = ImageEnhance.Brightness(img).enhance(1.02)

    # --- 縮小（Instagramの上限対策。長辺 max_side に収める）---
    if max(img.size) > max_side:
        scale = max_side / max(img.size)
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)

    # --- 透かし（右下に薄くアカウント名）---
    if watermark:
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        size = max(16, img.width // 28)
        font = _font(size)
        box = draw.textbbox((0, 0), watermark, font=font)
        tw, th = box[2] - box[0], box[3] - box[1]
        pad = size // 2
        x, y = img.width - tw - pad * 2, img.height - th - pad * 2
        draw.rectangle([x - pad, y - pad, x + tw + pad, y + th + pad], fill=(0, 0, 0, 70))
        draw.text((x, y), watermark, font=font, fill=(255, 255, 255, watermark_opacity))
        img = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")

    pathlib.Path(dst).parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, "JPEG", quality=quality, optimize=True, progressive=True)
    return dst, img.size
