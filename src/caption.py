"""写真を見て、SNSごとに“バズりやすい形”の文面をAIで作る。

X：短く、オチがある、ハッシュタグは1〜2個
Instagram：情景を丁寧に、保存したくなる一文、ハッシュタグは多め
Threads：会話の入り口になる、問いかけ型
"""
from __future__ import annotations

import base64
import json
import pathlib
import re
from typing import Any, Dict

import requests

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

PROMPT = """あなたは日本の猫アカウントのSNS運用担当です。添付の写真を見て、3つのSNS用の投稿文を日本語で作ってください。

# アカウント情報
- 猫の名前: {cat_name}
- 猫の特徴: {cat_traits}
- コンセプト: {account_concept}
- 文体の指定: {tone}
- 使ってはいけない言葉: {ng_words}
- 誘導先（グッズショップ）: {shop_name} {shop_url}

# 写真から読み取ること
1. 何をしている猫か（行動）
2. どこで（場所・状況）
3. 表情や仕草で目を引く点
4. 写真の一言説明（alt_text。目の不自由な方への説明にもなる）

# 各SNSの作り方
- x: 全角140文字以内。1行目で目を引く。オチか共感を入れる。ハッシュタグは1〜2個。**URLは入れない**。
- instagram: 3〜4行＋絵文字。情景が浮かぶ描写。最後に保存したくなる一言。ハッシュタグは8〜12個を末尾にまとめる。URLは入れない。
- threads: 2〜3行。読んだ人が返信したくなる問いかけで終える。ハッシュタグは1〜2個。

# 出力（このJSONだけを返す。前後に文章を付けない）
{{
  "scene": "写真の内容を40文字以内で",
  "alt_text": "画像の説明（80文字以内）",
  "x": "...",
  "instagram": "...",
  "threads": "...",
  "hashtags": ["#猫のいる暮らし", "..."],
  "goods_hook": "グッズへの誘導文（1文。押し売りしない）"
}}"""


def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        raise ValueError(f"JSONを抽出できませんでした: {text[:200]}")
    return json.loads(m.group(0))


def generate(image_path: str, cfg: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    p = cfg["profile"]
    prompt = PROMPT.format(
        cat_name=p.get("cat_name", "うちの猫"),
        cat_traits=p.get("cat_traits", ""),
        account_concept=p.get("account_concept", ""),
        tone=p.get("tone", "親しみやすく"),
        ng_words=", ".join(p.get("ng_words", [])) or "なし",
        shop_name=p.get("shop_name", ""),
        shop_url=p.get("shop_url", ""),
    )
    if dry_run:
        return _template_fallback(cfg, "dry-run")

    key = cfg["secrets"].get("GEMINI_API_KEY")
    if not key:
        return _template_fallback(cfg, "GEMINI_API_KEY未設定")

    data = pathlib.Path(image_path).read_bytes()
    mime = "image/png" if image_path.lower().endswith(".png") else "image/jpeg"
    body = {
        "contents": [{"parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode()}},
        ]}],
        "generationConfig": {
            "temperature": cfg.get("ai", {}).get("temperature", 1.0),
            "responseMimeType": "application/json",
        },
    }
    models = [cfg.get("ai", {}).get("model", "gemini-2.5-flash")] + cfg.get("ai", {}).get("fallback_models", [])
    last_err = ""
    for model in models:
        try:
            r = requests.post(f"{GEMINI_URL.format(model=model)}?key={key}", json=body, timeout=120)
            if r.status_code >= 400:
                last_err = f"{model}: HTTP {r.status_code} {r.text[:200]}"
                continue
            parts = r.json()["candidates"][0]["content"]["parts"]
            text = "".join(x.get("text", "") for x in parts)
            out = _extract_json(text)
            out["_model"] = model
            return out
        except Exception as exc:  # noqa: BLE001
            last_err = f"{model}: {exc}"
    return _template_fallback(cfg, last_err)


def _template_fallback(cfg: Dict[str, Any], reason: str) -> Dict[str, Any]:
    p = cfg["profile"]
    name = p.get("cat_name", "うちの猫")
    tags = ["#猫のいる暮らし", "#猫好きさんと繋がりたい", "#保護猫", "#猫のいる生活", "#ねこ部"]
    return {
        "scene": f"{name}の一枚",
        "alt_text": f"{name}の写真",
        "x": f"今日の{name}。\nこの顔だけでご飯3杯いけます。🐾\n" + " ".join(tags[:2]),
        "instagram": f"{name}の今日。\n\nなんでもない瞬間がいちばん残しておきたくなる。\n\n" + " ".join(tags),
        "threads": f"{name}、今日もマイペース。\nみんなの家の猫は今どこで寝てますか？",
        "hashtags": tags,
        "goods_hook": f"{p.get('shop_name','')}で{name}のグッズを作っています。",
        "_fallback_reason": reason,
    }
