"""X（旧Twitter）への投稿。2026年2月以降は従量課金（Pay-Per-Use）が既定。"""
from __future__ import annotations

from typing import Any, Dict

import requests

API = "https://api.x.com/2"


def _auth(cfg: Dict[str, Any]) -> Dict[str, str]:
    token = cfg["secrets"].get("X_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("X_ACCESS_TOKEN が未設定です")
    return {"Authorization": f"Bearer {token}"}


def upload_media(cfg: Dict[str, Any], image_path: str) -> str:
    with open(image_path, "rb") as f:
        r = requests.post(
            f"{API}/media/upload",
            headers=_auth(cfg),
            files={"media": f},
            data={"media_category": "tweet_image"},
            timeout=120,
        )
    if r.status_code >= 400:
        raise RuntimeError(f"X media upload failed {r.status_code}: {r.text[:300]}")
    return r.json()["data"]["id"]


def post(cfg: Dict[str, Any], text: str, image_path: str | None = None, reply_to: str | None = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"text": text}
    if image_path:
        payload["media"] = {"media_ids": [upload_media(cfg, image_path)]}
    if reply_to:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to}
    r = requests.post(
        f"{API}/tweets",
        headers={**_auth(cfg), "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"X post failed {r.status_code}: {r.text[:300]}")
    data = r.json()["data"]
    return {"id": data["id"], "url": f"https://x.com/i/status/{data['id']}"}


def post_with_optional_link(cfg: Dict[str, Any], text: str, image_path: str | None, hook: str, url: str) -> Dict[str, Any]:
    """本文はURLなしで投稿し、誘導リンクはリプライに逃がす（本文にURLを入れると単価が高いため）。"""
    main = post(cfg, text, image_path)
    if cfg.get("posting", {}).get("link_in_reply", True) and url:
        try:
            post(cfg, f"{hook}\n{url}".strip(), reply_to=main["id"])
        except Exception as exc:  # noqa: BLE001
            main["reply_error"] = str(exc)
    return main
