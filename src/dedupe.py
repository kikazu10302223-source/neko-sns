"""「この写真、もう投稿したっけ？」を判定する。

2段構え：
  1) sha256（完全一致）… まったく同じファイルなら一発で分かる
  2) dhash（知覚ハッシュ）… リサイズ・再保存・軽いトリミングされた「ほぼ同じ写真」を拾う
"""
from __future__ import annotations

import io

from PIL import Image


def dhash(image: Image.Image, size: int = 8) -> int:
    """差分ハッシュ（Difference Hash）。横方向の明暗差を64bitに圧縮する。

    人間でいうと「輪郭のガタつき方」だけをメモするイメージ。
    画素数や色味が変わっても、同じ構図なら近い値になる。
    """
    img = image.convert("L").resize((size + 1, size), Image.LANCZOS)
    px = list(img.getdata())
    bits = 0
    for row in range(size):
        for col in range(size):
            left = px[row * (size + 1) + col]
            right = px[row * (size + 1) + col + 1]
            bits = (bits << 1) | (1 if left > right else 0)
    return bits


def hamming(a: int, b: int) -> int:
    """2つのハッシュが何ビット違うか（0なら同一、小さいほど似ている）。"""
    return bin(a ^ b).count("1")


def to_hex(value: int) -> str:
    return f"{value:016x}"


def from_hex(text: str) -> int:
    return int(text, 16)


def is_duplicate(image: Image.Image, seen: list[tuple[str, str]], sha: str, distance: int = 6) -> tuple[bool, str]:
    """投稿済みリストと照合する。戻り値=(重複か, 理由)。"""
    for prev_sha, prev_dhash in seen:
        if prev_sha and prev_sha == sha:
            return True, "完全に同一のファイル（sha256一致）"
    mine = dhash(image)
    for prev_sha, prev_dhash in seen:
        if not prev_dhash:
            continue
        d = hamming(mine, from_hex(prev_dhash))
        if d <= distance:
            return True, f"似た写真（知覚ハッシュ差 {d}）"
    return False, ""


def dhash_of_bytes(data: bytes) -> str:
    return to_hex(dhash(Image.open(io.BytesIO(data))))
