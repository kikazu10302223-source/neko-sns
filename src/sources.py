"""写真の取り込み口。

- local      : パソコンのフォルダ（手元で実行するとき）
- cloudinary : Cloudinaryのフォルダ（おすすめ。スマホからも放り込めて、公開URLも同時に手に入る）
"""
from __future__ import annotations

import pathlib
import tempfile
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List

import requests

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}


@dataclass
class Photo:
    source_id: str      # 台帳に記録する一意な名前
    name: str
    url: str            # 公開URL（Instagramがここに取りに来る）
    data: bytes         # 画像の中身


def _download(url: str) -> bytes:
    r = requests.get(url, timeout=90)
    r.raise_for_status()
    return r.content


def iter_local(cfg: Dict[str, Any]) -> Iterator[Photo]:
    folder = pathlib.Path(cfg["source"].get("local_dir") or "")
    if not folder.exists():
        return
    for p in sorted(folder.rglob("*")):
        if p.suffix.lower() in IMAGE_EXT and p.is_file():
            yield Photo(source_id=f"local:{p.relative_to(folder).as_posix()}",
                        name=p.name, url=str(p), data=p.read_bytes())


def iter_cloudinary(cfg: Dict[str, Any], limit: int = 200) -> Iterator[Photo]:
    s = cfg["secrets"]
    cloud = s.get("CLOUDINARY_CLOUD_NAME")
    key, secret = s.get("CLOUDINARY_API_KEY"), s.get("CLOUDINARY_API_SECRET")
    prefix = cfg["source"].get("cloudinary_folder", "")
    if not (cloud and key and secret):
        raise RuntimeError("Cloudinaryの環境変数（CLOUDINARY_CLOUD_NAME / API_KEY / API_SECRET）が未設定です")
    r = requests.get(
        f"https://api.cloudinary.com/v1_1/{cloud}/resources/image",
        params={"max_results": min(limit, 500), "prefix": prefix, "type": "upload"},
        auth=(key, secret), timeout=60,
    )
    r.raise_for_status()
    for res in r.json().get("resources", []):
        yield Photo(source_id=f"cloudinary:{res['public_id']}",
                    name=res["public_id"], url=res["secure_url"], data=_download(res["secure_url"]))


def collect(cfg: Dict[str, Any]) -> List[Photo]:
    kind = cfg["source"].get("type", "cloudinary")
    photos = list(iter_cloudinary(cfg) if kind == "cloudinary" else iter_local(cfg))
    photos.sort(key=lambda p: p.name)
    return photos


def save_temp(photo: Photo, folder: str) -> str:
    pathlib.Path(folder).mkdir(parents=True, exist_ok=True)
    suffix = pathlib.Path(photo.name).suffix.lower() or ".jpg"
    if suffix not in IMAGE_EXT:
        suffix = ".jpg"
    out = pathlib.Path(tempfile.mkstemp(suffix=suffix, dir=folder)[1])
    out.write_bytes(photo.data)
    return str(out)
