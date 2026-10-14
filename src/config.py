"""設定と環境変数の読み込み。"""
from __future__ import annotations

import os
import pathlib
from typing import Any, Dict

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent

# 環境変数 → 設定キーの対応（GitHub Secrets に入れる名前）
SECRETS = {
    "X_ACCESS_TOKEN": "x_access_token",
    "IG_USER_ID": "ig_user_id",
    "IG_ACCESS_TOKEN": "ig_access_token",
    "THREADS_USER_ID": "threads_user_id",
    "THREADS_ACCESS_TOKEN": "threads_access_token",
    "GEMINI_API_KEY": "gemini_api_key",
    "CLOUDINARY_CLOUD_NAME": "cloudinary_cloud_name",
    "CLOUDINARY_API_KEY": "cloudinary_api_key",
    "CLOUDINARY_API_SECRET": "cloudinary_api_secret",
    "CLOUDINARY_UPLOAD_PRESET": "cloudinary_upload_preset",
}


def load(path: str | None = None) -> Dict[str, Any]:
    """config.yaml と環境変数をまとめて1つの辞書で返す。"""
    p = pathlib.Path(path or os.environ.get("CONFIG_PATH") or ROOT / "config.yaml")
    cfg: Dict[str, Any] = {}
    if p.exists():
        cfg = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    else:
        example = ROOT / "config.example.yaml"
        if example.exists():
            cfg = yaml.safe_load(example.read_text(encoding="utf-8")) or {}

    cfg.setdefault("paths", {})
    cfg["paths"]["root"] = str(ROOT)
    cfg["paths"]["state"] = str(ROOT / "data" / "state.sqlite3")
    cfg["paths"]["outbox"] = str(ROOT / "data" / "outbox")
    cfg["paths"]["work"] = str(ROOT / "data" / "work")
    cfg["paths"]["docs"] = str(ROOT / "docs")          # 手動モードの投稿キュー（GitHub Pages で配信）
    for d in ("outbox", "work", "docs"):
        pathlib.Path(cfg["paths"][d]).mkdir(parents=True, exist_ok=True)

    cfg["secrets"] = {k: os.environ.get(k, "") for k in SECRETS}
    cfg["_config_path"] = str(p)
    return cfg


def has(cfg: Dict[str, Any], key: str) -> bool:
    return bool(cfg.get("secrets", {}).get(key))
