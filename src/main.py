"""ねこSNS投稿パイプライン。

モードは2つ。既定は manual（手動投稿）。

  manual（おすすめ）… 投稿はせず、加工済みの画像とSNS別の文面を
                      「投稿キュー」（docs/index.html）にまとめる。
                      あとはスマホで開いて、コピー＆ペーストして自分で投稿する。
                      → XのAPI課金ゼロ・開発者審査ゼロ・規約違反リスクゼロ

  auto             … X / Instagram / Threads へ自動投稿する。

使い方：
  python -m src.main --check                    # 設定と接続の確認だけ
  python -m src.main --mode manual              # 投稿キューを作る（既定）
  python -m src.main --mode manual --limit 3    # 一度に3枚ぶん作る
  python -m src.main --mode auto --dry-run      # 自動投稿の予行演習
  python -m src.main --mode auto                # 自動投稿を実行
"""
from __future__ import annotations

import argparse
import io
import pathlib
import random
import sys
import time
from typing import Any, Dict

from PIL import Image

from . import (
    caption as caption_mod,
    cloudinary_upload,
    config,
    dedupe,
    imageprep,
    publish_ig,
    publish_threads,
    publish_x,
    queue,
    sources,
    store,
)

PLATFORMS = ["x", "instagram", "threads"]


def _log(msg: str) -> None:
    print(msg, flush=True)


def _ratio(cfg: Dict[str, Any], platform: str) -> str:
    return cfg.get("platforms", {}).get(f"{platform}_ratio", "4:5")


def resolve_mode(args: argparse.Namespace, cfg: Dict[str, Any]) -> str:
    """実行モードを決める。--prepare は manual の別名。"""
    if args.prepare:
        return "manual"
    if args.mode:
        return args.mode
    return str(cfg.get("mode", "manual"))


def run(args: argparse.Namespace) -> int:
    cfg = config.load(args.config)
    con = store.connect(cfg["paths"]["state"])

    mode = resolve_mode(args, cfg)
    manual = mode == "manual"

    enabled = {p: bool(cfg.get("platforms", {}).get(p)) for p in PLATFORMS}
    if manual:
        # 手動モードでは3SNSぶんの文面を必ず作る（どれを使うかは人が選ぶ）
        enabled = {p: True for p in PLATFORMS}
    if args.platform:
        for p in PLATFORMS:
            enabled[p] = enabled[p] and (p in args.platform)
    if not any(enabled.values()):
        _log("⚠ 投稿先が1つも有効になっていません（config.yaml の platforms を確認）")
        return 1

    max_per_day = cfg.get("posting", {}).get("max_per_day", 3)
    done_today = store.posted_today(con)
    label = "キューに積んだ数" if manual else "投稿した数"

    _log("=" * 60)
    _log(f"モード       : {mode}" + ("（投稿は自分で行います）" if manual else "（自動投稿）"))
    _log(f"設定ファイル : {cfg['_config_path']}")
    _log(f"対象SNS      : {[p for p, v in enabled.items() if v]}")
    _log(f"本日の{label} : {done_today} / {max_per_day}")
    _log("=" * 60)

    if args.check:
        return check(cfg, con, enabled, manual)

    limit = args.limit or cfg.get("posting", {}).get("per_run", 1)
    if done_today >= max_per_day:
        _log("本日の上限に達しています。終了します。")
        if manual:
            queue.build_page(cfg, con)
        return 0

    # --- 写真を集める ---
    try:
        photos = sources.collect(cfg)
    except Exception as exc:  # noqa: BLE001
        _log(f"✗ 写真の取得に失敗: {exc}")
        return 1
    _log(f"写真 {len(photos)} 枚を検出")

    seen = store.seen_hashes(con, cfg.get("dedupe", {}).get("lookback_days", 365))
    done = 0

    for photo in photos:
        if done >= limit:
            break
        try:
            img = Image.open(io.BytesIO(photo.data))
        except Exception as exc:  # noqa: BLE001
            _log(f"- {photo.name}: 画像として読めません（{exc}）")
            continue

        sha = store.sha256_bytes(photo.data)
        my_dhash = dedupe.dhash_of_bytes(photo.data)
        store.upsert_photo(con, photo.source_id, sha, my_dhash)  # 未処理でも台帳に登録しておく

        dup, why = dedupe.is_duplicate(img, seen, sha, cfg.get("dedupe", {}).get("dhash_distance", 6))
        if dup:
            _log(f"- {photo.name}: 使用済みのためスキップ（{why}）")
            continue

        # --- 加工 → 文面生成 ---
        work = cfg["paths"]["work"]
        tmp = sources.save_temp(photo, work)
        out = pathlib.Path(work) / (
            f"{photo.source_id.replace(':', '_').replace('/', '_')}_"
            f"{_ratio(cfg, 'instagram').replace(':', '-')}.jpg"
        )
        img_cfg = cfg.get("image", {})
        imageprep.prepare(
            tmp, str(out), ratio=_ratio(cfg, "instagram"),
            watermark=img_cfg.get("watermark_text") if img_cfg.get("add_watermark") else None,
            watermark_opacity=img_cfg.get("watermark_opacity", 110),
            autocontrast=img_cfg.get("autocontrast", True),
            max_side=img_cfg.get("max_side", 1440),
            quality=img_cfg.get("jpeg_quality", 88),
        )
        _log(f"→ 加工完了: {out.name}")

        cap = caption_mod.generate(str(out), cfg, dry_run=args.dry_run)
        _log(f"→ 文面生成（{cap.get('_model') or cap.get('_fallback_reason', '')}）")

        if manual:
            qid = queue.add(cfg, con, photo.source_id, str(out), cap)
            store.mark(con, photo.source_id, "manual", "", cap)
            _log(f"→ 投稿キューに追加（No.{qid}）: {cap.get('scene', '')}")
            seen = store.seen_hashes(con, cfg.get("dedupe", {}).get("lookback_days", 365))
            done += 1
            continue

        # --- 公開URLを用意（Instagram / Threads はURLが必須）---
        public_url = photo.url if photo.url.startswith("http") else None
        if any(enabled[p] for p in ("instagram", "threads")) and not args.dry_run:
            if not public_url:
                public_url = cloudinary_upload.upload(str(out), cfg)
                _log(f"→ 公開URL: {public_url}")

        results = publish_all(cfg, enabled, out, cap, public_url, photo, dry_run=args.dry_run)
        for platform, r in results.items():
            mark = "✓" if r.get("ok") else "✗"
            _log(f"   {mark} {platform}: {r.get('url') or r.get('error')}")
            store.log_run(con, "post", platform, photo.source_id, r.get("url", ""), r.get("ok", False), r.get("error", ""))
        if any(r.get("ok") for r in results.values()):
            first_ok = next(p for p, r in results.items() if r.get("ok"))
            store.mark(con, photo.source_id, first_ok, results[first_ok].get("url", ""), cap)
            seen = store.seen_hashes(con, cfg.get("dedupe", {}).get("lookback_days", 365))
        done += 1

    if manual:
        page = queue.build_page(cfg, con)
        _log(f"→ 投稿キューを更新しました: {page}")
        _log(f"   キュー内の件数: {store.queued_count(con)} 件")

    _log(f"完了: {done} 件を処理しました。")
    return 0


def publish_all(cfg, enabled, image_path, cap, public_url, photo, dry_run=False) -> Dict[str, Dict[str, Any]]:
    """各SNSへ投稿。1つ失敗しても他は続ける。"""
    results: Dict[str, Dict[str, Any]] = {}
    link = (cfg["profile"].get("shop_url") or "").strip()

    if enabled["x"]:
        try:
            if dry_run:
                results["x"] = {"ok": True, "url": "(dry-run)", "text": cap["x"]}
            else:
                r = publish_x.post_with_optional_link(cfg, cap["x"], image_path, cap.get("goods_hook", ""), link)
                results["x"] = {"ok": True, "url": r["url"]}
        except Exception as exc:  # noqa: BLE001
            results["x"] = {"ok": False, "error": str(exc)}

    if enabled["instagram"]:
        try:
            ig_cap = cap["instagram"]
            if link and link not in ig_cap:
                ig_cap = f"{ig_cap}\n\n{cap.get('goods_hook', '')}\n{link}"
            if dry_run:
                results["instagram"] = {"ok": True, "url": "(dry-run)", "text": ig_cap}
            else:
                r = publish_ig.publish(cfg, public_url, ig_cap)
                results["instagram"] = {"ok": True, "url": r["url"]}
        except Exception as exc:  # noqa: BLE001
            results["instagram"] = {"ok": False, "error": str(exc)}

    if enabled["threads"]:
        try:
            if dry_run:
                results["threads"] = {"ok": True, "url": "(dry-run)", "text": cap["threads"]}
            else:
                r = publish_threads.publish(cfg, cap["threads"], public_url)
                results["threads"] = {"ok": True, "url": r["url"]}
        except Exception as exc:  # noqa: BLE001
            results["threads"] = {"ok": False, "error": str(exc)}
    return results


def check(cfg, con, enabled, manual: bool) -> int:
    """設定・鍵・接続の確認。手動モードではSNSの鍵は不要。"""
    ok = True
    s = cfg["secrets"]

    if manual:
        _log("手動モード：X / Instagram / Threads のAPIキーは不要です。")
    else:
        need = {
            "x": ["X_ACCESS_TOKEN"],
            "instagram": ["IG_USER_ID", "IG_ACCESS_TOKEN"],
            "threads": ["THREADS_USER_ID", "THREADS_ACCESS_TOKEN"],
        }
        for platform, keys in need.items():
            if not enabled.get(platform):
                continue
            missing = [k for k in keys if not s.get(k)]
            if missing:
                _log(f"✗ {platform}: 未設定 {missing}")
                ok = False
            else:
                _log(f"✓ {platform}: 鍵あり")

    if not s.get("GEMINI_API_KEY"):
        _log("△ GEMINI_API_KEY 未設定 → AI文面は作れず、定型文になります")
    else:
        _log("✓ GEMINI_API_KEY: あり（AI文面が使えます）")

    src = cfg.get("source", {}).get("type")
    if src == "cloudinary" and not s.get("CLOUDINARY_CLOUD_NAME"):
        _log("✗ 写真の取り込み元が Cloudinary なのに CLOUDINARY_CLOUD_NAME が未設定です")
        ok = False

    try:
        n = len(sources.collect(cfg))
        _log(f"✓ 写真の取得: {n} 枚")
    except Exception as exc:  # noqa: BLE001
        _log(f"✗ 写真の取得: {exc}")
        ok = False

    if not manual and enabled.get("instagram") and s.get("IG_USER_ID"):
        try:
            _log(f"✓ Instagram 残り投稿枠: {publish_ig.publishing_limit(cfg)}")
        except Exception as exc:  # noqa: BLE001
            _log(f"△ Instagram 残枠の確認に失敗: {exc}")

    _log(f"台帳の記録: {con.execute('SELECT COUNT(*) c FROM photos').fetchone()['c']} 枚")
    if manual:
        _log(f"投稿キュー : {store.queued_count(con)} 件")
    return 0 if ok else 1


def main() -> None:
    ap = argparse.ArgumentParser(description="ねこSNS投稿パイプライン")
    ap.add_argument("--config", help="config.yaml のパス")
    ap.add_argument("--mode", choices=["manual", "auto"], help="manual=投稿キュー作成のみ / auto=自動投稿")
    ap.add_argument("--limit", type=int, help="この実行で処理する枚数")
    ap.add_argument("--platform", help="カンマ区切りで対象を限定（例: x,instagram）")
    ap.add_argument("--dry-run", action="store_true", help="AIを使わず定型文で試す（投稿もしない）")
    ap.add_argument("--prepare", action="store_true", help="--mode manual と同じ")
    ap.add_argument("--check", action="store_true", help="設定と接続の確認だけ行う")
    args = ap.parse_args()

    if args.platform:
        args.platform = [p.strip() for p in args.platform.split(",") if p.strip()]

    # スパム判定を避けるための待機は自動投稿のときだけ意味がある
    mode = args.mode
    if args.prepare:
        mode = "manual"
    if mode is None:
        try:
            mode = config.load(args.config).get("mode", "manual")
        except Exception:  # noqa: BLE001
            mode = "manual"

    if mode == "auto" and not args.dry_run and not args.check:
        try:
            j = int(config.load(args.config).get("posting", {}).get("jitter_minutes", 0) or 0)
        except Exception:  # noqa: BLE001
            j = 0
        if j:
            wait = random.randint(0, j * 60)
            _log(f"スパム判定を避けるため {wait // 60}分{wait % 60}秒 待機します…")
            time.sleep(wait)

    sys.exit(run(args))


if __name__ == "__main__":
    main()
