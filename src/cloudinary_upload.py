"""加工済み画像をCloudinaryへ上げて、公開URLを手に入れる。

InstagramのAPIは「Metaのサーバーが画像を取りに行く」方式なので、
画像はどこかしら「誰でも見られるURL」に置かれている必要がある。
その置き場をCloudinaryが担う（無料枠あり）。
"""
from __future__ import annotations

import hashlib
import time
from typing import Any, Dict

import requests


def upload(path: str, cfg: Dict[str, Any], folder: str | None = None) -> str:
    s = cfg["secrets"]
    cloud = s.get("CLOUDINARY_CLOUD_NAME")
    if not cloud:
        raise RuntimeError("CLOUDINARY_CLOUD_NAME が未設定です")
    endpoint = f"https://api.cloudinary.com/v1_1/{cloud}/image/upload"
    folder = folder or cfg["source"].get("cloudinary_folder", "")

    # 署名なしプリセット（いちばん簡単な方式）
    preset = s.get("CLOUDINARY_UPLOAD_PRESET")
    if preset:
        with open(path, "rb") as f:
            r = requests.post(endpoint, data={"upload_preset": preset, "folder": folder},
                              files={"file": f}, timeout=180)
        r.raise_for_status()
        return r.json()["secure_url"]

    # 署名あり（api_key + api_secret）
    key, secret = s.get("CLOUDINARY_API_KEY"), s.get("CLOUDINARY_API_SECRET")
    if not (key and secret):
        raise RuntimeError("CLOUDINARY_UPLOAD_PRESET か、API_KEY+API_SECRET のどちらかが必要です")
    ts = str(int(time.time()))
    params = {"folder": folder, "timestamp": ts}
    sign_src = "&".join(f"{k}={v}" for k, v in sorted(params.items())) + secret
    params.update({"api_key": key, "signature": hashlib.sha1(sign_src.encode()).hexdigest()})
    with open(path, "rb") as f:
        r = requests.post(endpoint, data=params, files={"file": f}, timeout=180)
    if r.status_code >= 400:
        raise RuntimeError(f"Cloudinary upload failed {r.status_code}: {r.text[:300]}")
    return r.json()["secure_url"]
