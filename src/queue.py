"""手動投稿モード ─ 「投稿キュー」ページを作る。

自動投稿はせず、加工済みの画像とSNS別の文面を、
スマホで開ける1枚のページ（docs/index.html）にまとめる。

使い方の流れ：
  1. スマホでキューを開く
  2. 画像を長押しして保存（または「画像を保存」ボタン）
  3. 「コピー」ボタンで文面をコピー
  4. X / Instagram / Threads のアプリに貼り付けて投稿
  5. 終わったら「投稿した」にチェック

この方式の利点：
  - X API が不要 ＝ 課金ゼロ・開発者審査ゼロ
  - 「自動投稿ツール」ではないので規約違反リスクがゼロ
  - 投稿前に人間が文面と画像を確認できる
"""
from __future__ import annotations

import hashlib
import html
import json
import pathlib
import re
from typing import Any, Dict, List

from . import store

IMG_SUBDIR = "img"


# ======================================================================
#  文面の組み立て
# ======================================================================
def _tags(cap: Dict[str, Any]) -> List[str]:
    return [str(t) for t in (cap.get("hashtags") or []) if str(t).strip()]


def x_text(cap: Dict[str, Any]) -> str:
    """X用の本文。URLは入れない（リンク付きポストは伸びにくく、単価も高い）。"""
    return (cap.get("x") or "").strip()


def x_reply(cfg: Dict[str, Any], cap: Dict[str, Any]) -> str:
    """X用のリプライ（ショップへの誘導）。本文と分けることで表示を落とされにくくする。"""
    link = (cfg.get("profile", {}).get("shop_url") or "").strip()
    hook = (cap.get("goods_hook") or "").strip()
    if not link:
        return hook
    return f"{hook}\n{link}".strip()


def ig_text(cap: Dict[str, Any]) -> str:
    """Instagram用の最終文面。ハッシュタグが本文に無ければ末尾に足す。"""
    t = (cap.get("instagram") or "").strip()
    tags = _tags(cap)
    if tags and "#" not in t:
        t = f"{t}\n\n{' '.join(tags)}"
    return t


def threads_text(cap: Dict[str, Any]) -> str:
    """Threads用の最終文面。ハッシュタグは1〜2個まで。"""
    t = (cap.get("threads") or "").strip()
    tags = _tags(cap)[:2]
    if tags and "#" not in t:
        t = f"{t}\n\n{' '.join(tags)}"
    return t


def _safe_name(source_id: str) -> str:
    """source_id から、安全で重複しない画像ファイル名を作る。"""
    h = hashlib.sha1(source_id.encode("utf-8")).hexdigest()[:12]
    stem = re.sub(r"[^A-Za-z0-9]+", "-", source_id).strip("-")[:40] or "photo"
    return f"{stem}-{h}.jpg"


# ======================================================================
#  キューへの追加
# ======================================================================
def add(cfg: Dict[str, Any], con, source_id: str, image_path: str, cap: Dict[str, Any]) -> int:
    """加工済み画像と文面をキューに登録し、docs/img/ へ画像をコピーする。"""
    docs = pathlib.Path(cfg["paths"]["docs"])
    img_dir = docs / IMG_SUBDIR
    img_dir.mkdir(parents=True, exist_ok=True)

    name = _safe_name(source_id)
    (img_dir / name).write_bytes(pathlib.Path(image_path).read_bytes())
    rel = f"{IMG_SUBDIR}/{name}"

    tags = _tags(cap)
    con.execute(
        """
        INSERT INTO queue (source_id, image_rel, scene, alt_text,
                           x_text, x_reply, ig_text, threads_text, hashtags, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(source_id) DO UPDATE SET
          image_rel=excluded.image_rel, scene=excluded.scene, alt_text=excluded.alt_text,
          x_text=excluded.x_text, x_reply=excluded.x_reply, ig_text=excluded.ig_text,
          threads_text=excluded.threads_text, hashtags=excluded.hashtags
        """,
        (
            source_id, rel,
            (cap.get("scene") or "").strip(),
            (cap.get("alt_text") or "").strip(),
            x_text(cap), x_reply(cfg, cap), ig_text(cap), threads_text(cap),
            json.dumps(tags, ensure_ascii=False),
            store.now(),
        ),
    )
    con.commit()
    row = con.execute("SELECT id FROM queue WHERE source_id=?", (source_id,)).fetchone()
    return int(row["id"]) if row else -1


def mark_posted(con, queue_id: int, posted: bool = True) -> None:
    con.execute("UPDATE queue SET posted=? WHERE id=?", (1 if posted else 0, queue_id))
    con.commit()


# ======================================================================
#  ページの生成
# ======================================================================
def _esc(s: Any) -> str:
    return html.escape(str(s or ""), quote=True)


def _block(label: str, cls: str, text: str, hint: str = "") -> str:
    """コピーできる文面ブロック1つぶんのHTML。"""
    return f"""      <div class="block">
        <div class="bhead">
          <span class="badge {cls}">{_esc(label)}</span>
          <button class="copy" data-copy="{_esc(text)}">コピー</button>
        </div>
        <pre class="txt">{html.escape(text)}</pre>
        {f'<p class="hint">{html.escape(hint)}</p>' if hint else ''}
      </div>"""


def _card(row, cfg: Dict[str, Any]) -> str:
    shop_url = (cfg.get("profile", {}).get("shop_url") or "").strip()
    shop_name = (cfg.get("profile", {}).get("shop_name") or "").strip()
    when = (row["created_at"] or "")[:16].replace("T", " ")
    scene = row["scene"] or ""
    alt = row["alt_text"] or ""

    ig_hint = (
        f"Instagramは本文にリンクを貼れません。プロフィール欄か、最初のコメントに {shop_url} を置いてください。"
        if shop_url else ""
    )

    blocks = [
        _block("X 本文", "x", row["x_text"] or ""),
        _block("X リプライ", "x", row["x_reply"] or "",
               "本文のあとに自分で返信すると、リンクが本文に無い状態を保てます。"),
        _block("Instagram", "ig", row["ig_text"] or "", ig_hint),
        _block("Threads", "th", row["threads_text"] or ""),
    ]

    return f"""  <article class="card" data-id="{row['id']}">
    <div class="imgwrap">
      <img src="{_esc(row['image_rel'])}" alt="{_esc(alt or scene)}" decoding="async"
           onerror="this.closest('.imgwrap').classList.add('broken')">
      <a class="save" href="{_esc(row['image_rel'])}" download>画像を保存</a>
    </div>
    <div class="meta">
      <span class="when">{_esc(when)}</span>
      <span class="scene">{_esc(scene)}</span>
    </div>
{chr(10).join(blocks)}
    <label class="done">
      <input type="checkbox" data-key="{row['id']}">
      <span>この投稿は終わった</span>
    </label>
  </article>"""


PAGE_CSS = """
:root{
  --bg:#f5f4f1; --card:#ffffff; --fg:#1b1a18; --muted:#6b6a66; --line:#e4e2dc;
  --accent:#c2632a; --ok:#2f7d52; --chip:#f0eee9;
}
@media (prefers-color-scheme:dark){
  :root{--bg:#131312;--card:#1d1d1b;--fg:#f1f0ed;--muted:#a4a29d;--line:#33322e;
        --accent:#e5934f;--ok:#63cf92;--chip:#262624;}
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  margin:0;background:var(--bg);color:var(--fg);font-size:15px;line-height:1.75;
  font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans","Noto Sans JP","Yu Gothic UI",sans-serif;
  padding:0 0 env(safe-area-inset-bottom);
}
.wrap{max-width:720px;margin:0 auto;padding:20px 14px 60px}
header h1{font-size:21px;margin:0 0 4px;letter-spacing:.01em}
header .sub{margin:0;color:var(--muted);font-size:13px}
.howto{
  background:var(--card);border:1px solid var(--line);border-radius:14px;
  padding:14px 16px;margin:16px 0 22px;font-size:13.5px;color:var(--muted)
}
.howto b{color:var(--fg)}
.howto ol{margin:6px 0 0;padding-left:1.2em}
.howto li{margin:3px 0}
.card{
  background:var(--card);border:1px solid var(--line);border-radius:18px;
  padding:14px;margin:0 0 20px;box-shadow:0 1px 2px rgba(0,0,0,.04)
}
.card.done{opacity:.5}
.imgwrap{position:relative;border-radius:12px;overflow:hidden;background:var(--chip);min-height:220px}
.imgwrap img{display:block;width:100%;height:auto;min-height:220px;object-fit:cover}
/* 画像が読み込めなかったときもレイアウトを崩さない */
.imgwrap.broken img{display:none}
.imgwrap.broken::after{
  content:"画像を読み込めませんでした。GitHub Actionsの実行結果（Artifact）から取得してください。";
  position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
  text-align:center;padding:28px;font-size:13px;color:var(--muted);line-height:1.7
}
.save{
  position:absolute;right:10px;bottom:10px;background:rgba(0,0,0,.7);color:#fff;
  text-decoration:none;font-size:13px;padding:11px 17px;border-radius:999px;
  backdrop-filter:blur(6px);box-shadow:0 2px 10px rgba(0,0,0,.28)
}
.meta{display:flex;gap:10px;align-items:baseline;margin:11px 2px 4px;flex-wrap:wrap}
.when{font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums}
.scene{font-size:13.5px}
.block{margin:12px 0 0}
.bhead{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:6px}
.badge{font-size:11.5px;font-weight:700;letter-spacing:.04em;padding:3px 9px;border-radius:999px;background:var(--chip)}
.badge.x{color:#fff;background:#15181c}
.badge.ig{color:#fff;background:linear-gradient(95deg,#f9a03f,#d5317c,#7b3fd4)}
.badge.th{color:#fff;background:#2a2a2a}
@media (prefers-color-scheme:dark){.badge.x{background:#3a3d42}.badge.th{background:#4a4a4a}}
.copy{
  font:inherit;font-size:13px;padding:10px 18px;min-height:42px;border-radius:999px;cursor:pointer;
  border:1px solid var(--line);background:var(--chip);color:var(--fg);white-space:nowrap;
  display:inline-flex;align-items:center;justify-content:center
}
.copy:active{transform:scale(.97)}
.copy.ok{background:var(--ok);border-color:var(--ok);color:#fff}
.txt{
  margin:0;white-space:pre-wrap;word-break:break-word;font:inherit;font-size:14.5px;
  background:var(--chip);border-radius:10px;padding:11px 12px
}
.hint{margin:6px 2px 0;font-size:12px;color:var(--muted)}
.done{
  display:flex;align-items:center;gap:10px;margin-top:16px;padding:14px 2px 4px;
  min-height:48px;border-top:1px solid var(--line);font-size:13.5px;color:var(--muted);cursor:pointer
}
.done input{width:22px;height:22px;accent-color:var(--ok);flex:none}
.empty{color:var(--muted);text-align:center;padding:50px 0}
footer{margin-top:34px;text-align:center;color:var(--muted);font-size:12px}
footer code{background:var(--chip);padding:2px 6px;border-radius:5px}
"""

PAGE_JS = """
(function(){
  var KEY='neko-posted-v1';
  var saved={};
  try{saved=JSON.parse(localStorage.getItem(KEY)||'{}')||{};}catch(e){saved={};}

  document.addEventListener('click',function(ev){
    var btn=ev.target.closest('.copy');
    if(!btn) return;
    var text=btn.getAttribute('data-copy')||'';
    var done=function(){
      var old=btn.textContent;
      btn.classList.add('ok'); btn.textContent='コピーしました ✓';
      setTimeout(function(){btn.classList.remove('ok'); btn.textContent=old;},1500);
    };
    if(navigator.clipboard && navigator.clipboard.writeText){
      navigator.clipboard.writeText(text).then(done,function(){fallback(text,done);});
    }else{ fallback(text,done); }
  });

  function fallback(text,cb){
    var ta=document.createElement('textarea');
    ta.value=text; ta.setAttribute('readonly','');
    ta.style.position='fixed'; ta.style.top='-1000px';
    document.body.appendChild(ta); ta.select();
    try{document.execCommand('copy');}catch(e){}
    document.body.removeChild(ta); cb();
  }

  var boxes=document.querySelectorAll('input[type=checkbox][data-key]');
  Array.prototype.forEach.call(boxes,function(cb){
    var card=cb.closest('.card');
    if(saved[cb.getAttribute('data-key')]){cb.checked=true; card.classList.add('done');}
    cb.addEventListener('change',function(){
      saved[cb.getAttribute('data-key')]=cb.checked;
      try{localStorage.setItem(KEY,JSON.stringify(saved));}catch(e){}
      card.classList.toggle('done',cb.checked);
    });
  });
})();
"""

PAGE_TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow,noarchive">
<meta name="color-scheme" content="light dark">
<title>{{TITLE}}</title>
<style>{{CSS}}</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>{{TITLE}}</h1>
    <p class="sub">{{SUB}}</p>
  </header>

  <section class="howto">
    <b>使い方（1件あたり1〜2分）</b>
    <ol>
      <li>画像を<b>長押し</b>して「写真に追加」で保存（「画像を保存」ボタンでもOK）</li>
      <li>「コピー」を押して文面をコピー</li>
      <li>X / Instagram / Threads を開いて、画像を選んで貼り付け、投稿</li>
      <li>終わったら下の「この投稿は終わった」にチェック（この端末にだけ記録されます）</li>
    </ol>
  </section>

  <main>
{{CARDS}}
  </main>

  <footer>
    {{COUNT}} 件 ／ 最終更新 {{UPDATED}}<br>
    このページは <code>docs/</code> から自動生成されています。手で編集しても次の実行で上書きされます。
  </footer>
</div>
<script>{{JS}}</script>
</body>
</html>
"""


def _page_html(cfg: Dict[str, Any], rows: List[Any]) -> str:
    title = cfg.get("manual", {}).get("page_title") or "投稿キュー"
    cat = (cfg.get("profile", {}).get("cat_name") or "").strip()
    sub = f"{cat}の投稿ストック" if cat else "投稿ストック"

    if rows:
        cards = "\n".join(_card(r, cfg) for r in rows)
    else:
        cards = '<p class="empty">まだキューが空です。写真を追加してから実行してください。</p>'

    return (
        PAGE_TEMPLATE
        .replace("{{TITLE}}", html.escape(str(title)))
        .replace("{{SUB}}", html.escape(sub))
        .replace("{{CSS}}", PAGE_CSS)
        .replace("{{CARDS}}", cards)
        .replace("{{COUNT}}", str(len(rows)))
        .replace("{{UPDATED}}", store.now().replace("T", " ")[:16])
        .replace("{{JS}}", PAGE_JS)
    )


def build_page(cfg: Dict[str, Any], con) -> str:
    """docs/index.html と docs/queue.json を書き出し、不要になった画像を掃除する。"""
    docs = pathlib.Path(cfg["paths"]["docs"])
    docs.mkdir(parents=True, exist_ok=True)

    size = int(cfg.get("manual", {}).get("queue_size", 12) or 12)
    rows = con.execute("SELECT * FROM queue ORDER BY id DESC LIMIT ?", (size,)).fetchall()

    # キューから外れた画像は削除して、リポジトリを太らせない
    keep = {pathlib.Path(r["image_rel"]).name for r in rows}
    img_dir = docs / IMG_SUBDIR
    if img_dir.exists():
        for f in img_dir.iterdir():
            if f.is_file() and f.name not in keep:
                try:
                    f.unlink()
                except OSError:
                    pass

    (docs / "index.html").write_text(_page_html(cfg, rows), encoding="utf-8")
    (docs / "queue.json").write_text(
        json.dumps(
            [
                {
                    "id": r["id"],
                    "created_at": r["created_at"],
                    "image": r["image_rel"],
                    "scene": r["scene"],
                    "x": r["x_text"],
                    "x_reply": r["x_reply"],
                    "instagram": r["ig_text"],
                    "threads": r["threads_text"],
                    "hashtags": json.loads(r["hashtags"] or "[]"),
                }
                for r in rows
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return str(docs / "index.html")
