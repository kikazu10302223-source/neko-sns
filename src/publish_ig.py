"""Instagram（プロアカウント）への投稿。

Instagramは「1回で投稿」ではなく、必ず2段階：
  1) コンテナ作成  POST /<IG_ID>/media      … 「この画像を出す準備をして」と予約
  2) 公開          POST /<IG_ID>/media_publish … 「はい、出して」
Metaのサーバーが image_url を取りに行くので、URLは公開されている必要がある。
"""
from __future__ import annotations

import time
from typing import Any, Dict

import requests

HOST = "https://graph.instagram.com"
VERSION = "v26.0"


def _creds(cfg: Dict[str, Any]) -> tuple[str, str]:
    s = cfg["secrets"]
    ig_id, token = s.get("IG_USER_ID"), s.get("IG_ACCESS_TOKEN")
    if not (ig_id and token):
        raise RuntimeError("IG_USER_ID / IG_ACCESS_TOKEN が未設定です")
    return ig_id, token


def publish(cfg: Dict[str, Any], image_url: str, caption: str, is_ai_generated: bool = False) -> Dict[str, Any]:
    ig_id, token = _creds(cfg)
    base = f"{HOST}/{VERSION}/{ig_id}"

    payload = {"image_url": image_url, "caption": caption}
    if is_ai_generated:
        payload["is_ai_generated"] = "true"

    r = requests.post(f"{base}/media", data=payload, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError(f"IG container failed {r.status_code}: {r.text[:300]}")
    container = r.json()["id"]

    # 画像の取り込みが終わるまで待つ（すぐ叩くと「まだ準備中」で失敗することがある）
    for _ in range(10):
        st = requests.get(f"{HOST}/{VERSION}/{container}",
                          params={"fields": "status_code", "access_token": token}, timeout=60)
        code = st.json().get("status_code")
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise RuntimeError(f"IG container error: {st.text[:300]}")
        time.sleep(5)

    r = requests.post(f"{base}/media_publish", data={"creation_id": container}, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError(f"IG publish failed {r.status_code}: {r.text[:300]}")
    media_id = r.json()["id"]
    return {"id": media_id, "url": f"https://www.instagram.com/p/{media_id}"}


def publishing_limit(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """残り投稿枠（24時間で100件まで）を確認する。"""
    ig_id, token = _creds(cfg)
    r = requests.get(f"{HOST}/{VERSION}/{ig_id}/content_publishing_limit",
                     params={"fields": "quota_usage,config", "access_token": token}, timeout=60)
    r.raise_for_status()
    return r.json()
