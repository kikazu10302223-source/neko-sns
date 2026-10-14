"""Threads（スレッズ）への投稿。無料で、1日250投稿まで。いま最も自動投稿の壁が低い。"""
from __future__ import annotations

import time
from typing import Any, Dict

import requests

HOST = "https://graph.threads.net/v1.0"


def _creds(cfg: Dict[str, Any]) -> tuple[str, str]:
    s = cfg["secrets"]
    uid, token = s.get("THREADS_USER_ID"), s.get("THREADS_ACCESS_TOKEN")
    if not (uid and token):
        raise RuntimeError("THREADS_USER_ID / THREADS_ACCESS_TOKEN が未設定です")
    return uid, token


def publish(cfg: Dict[str, Any], text: str, image_url: str | None = None) -> Dict[str, Any]:
    uid, token = _creds(cfg)
    data = {"text": text, "access_token": token}
    if image_url:
        data.update({"media_type": "IMAGE", "image_url": image_url})
    else:
        data["media_type"] = "TEXT"

    r = requests.post(f"{HOST}/{uid}/threads", data=data, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError(f"Threads container failed {r.status_code}: {r.text[:300]}")
    container = r.json()["id"]
    time.sleep(3)   # 取り込み待ち（Threadsは数十秒必要な場合あり）

    r = requests.post(f"{HOST}/{uid}/threads_publish",
                      data={"creation_id": container, "access_token": token}, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError(f"Threads publish failed {r.status_code}: {r.text[:300]}")
    tid = r.json()["id"]
    return {"id": tid, "url": f"https://www.threads.net/@{uid}/post/{tid}"}
