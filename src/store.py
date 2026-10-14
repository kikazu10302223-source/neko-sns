"""投稿台帳（SQLite）。どの写真を、いつ、どこに出したかを記録する。"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sqlite3
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))

SCHEMA = """
CREATE TABLE IF NOT EXISTS photos (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id    TEXT UNIQUE,          -- Cloudinaryのpublic_id / ローカルの相対パス
  sha256       TEXT,                 -- 完全一致の重複検知
  dhash        TEXT,                 -- 知覚ハッシュ（似た写真の重複検知）
  status       TEXT DEFAULT 'new',   -- new / posted / skipped
  caption_json TEXT,
  posted_x     TEXT, posted_ig TEXT, posted_threads TEXT,
  created_at   TEXT, posted_at TEXT,
  note         TEXT
);
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  at TEXT, mode TEXT, platform TEXT, source_id TEXT, url TEXT, ok INTEGER, detail TEXT
);
CREATE TABLE IF NOT EXISTS queue (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id    TEXT UNIQUE,
  image_rel    TEXT,                 -- docs/ からの相対パス（例 img/xxx.jpg）
  scene        TEXT,
  alt_text     TEXT,
  x_text       TEXT,
  x_reply      TEXT,
  ig_text      TEXT,
  threads_text TEXT,
  hashtags     TEXT,
  created_at   TEXT,
  posted       INTEGER DEFAULT 0
);
"""

# platform 名 → photos テーブルの列名（manual は列を持たない）
_POST_COLS = {"x": "posted_x", "instagram": "posted_ig", "threads": "posted_threads"}


def connect(state_path: str) -> sqlite3.Connection:
    pathlib.Path(state_path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(state_path)
    con.executescript(SCHEMA)
    con.row_factory = sqlite3.Row
    return con


def now() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def upsert_photo(con, source_id: str, sha: str, dhash: str) -> sqlite3.Row:
    cur = con.execute("SELECT * FROM photos WHERE source_id=?", (source_id,))
    row = cur.fetchone()
    if row:
        return row
    con.execute(
        "INSERT INTO photos (source_id, sha256, dhash, status, created_at) VALUES (?,?,?,?,?)",
        (source_id, sha, dhash, "new", now()),
    )
    con.commit()
    return con.execute("SELECT * FROM photos WHERE source_id=?", (source_id,)).fetchone()


def seen_hashes(con, lookback_days: int) -> list[tuple[str, str]]:
    """「もう出した」写真の指紋一覧。重複判定の基準になる。"""
    since = (datetime.now(JST) - timedelta(days=lookback_days)).isoformat(timespec="seconds")
    rows = con.execute(
        "SELECT sha256, dhash FROM photos WHERE created_at >= ? AND status='posted'", (since,)
    ).fetchall()
    return [(r["sha256"], r["dhash"]) for r in rows]


def mark(con, source_id: str, platform: str, url: str, caption_json: dict, ok: bool = True, detail: str = ""):
    """1枚を「出した」状態にする。platform は x / instagram / threads / manual。"""
    col = _POST_COLS.get(platform)
    if col:
        con.execute(
            f"UPDATE photos SET {col}=?, status='posted', posted_at=?, caption_json=? WHERE source_id=?",
            (url, now(), json.dumps(caption_json, ensure_ascii=False), source_id),
        )
    else:
        # manual（手動投稿キュー）は専用の列を持たず、状態だけ進める
        con.execute(
            "UPDATE photos SET status='posted', posted_at=?, caption_json=?, note=? WHERE source_id=?",
            (now(), json.dumps(caption_json, ensure_ascii=False), f"queued:{platform}", source_id),
        )
    con.execute(
        "INSERT INTO runs (at, mode, platform, source_id, url, ok, detail) VALUES (?,?,?,?,?,?,?)",
        (now(), "post", platform, source_id, url, 1 if ok else 0, detail[:500]),
    )
    con.commit()


def log_run(con, mode: str, platform: str, source_id: str, url: str, ok: bool, detail: str = ""):
    con.execute(
        "INSERT INTO runs (at, mode, platform, source_id, url, ok, detail) VALUES (?,?,?,?,?,?,?)",
        (now(), mode, platform, source_id, url, 1 if ok else 0, detail[:500]),
    )
    con.commit()


def posted_today(con) -> int:
    """今日すでに処理した枚数（手動モードでは「キューに積んだ枚数」）。"""
    today = datetime.now(JST).date().isoformat()
    return con.execute(
        "SELECT COUNT(*) c FROM photos WHERE status='posted' AND substr(posted_at,1,10)=?", (today,)
    ).fetchone()["c"]


def queued_count(con) -> int:
    return con.execute("SELECT COUNT(*) c FROM queue").fetchone()["c"]
