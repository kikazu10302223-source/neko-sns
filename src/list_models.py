"""使えるGeminiモデル名を一覧表示する（無料枠で使えるモデルの確認用）。

    GEMINI_API_KEY=xxx python -m src.list_models
"""
from __future__ import annotations

import os

import requests


def main() -> None:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("環境変数 GEMINI_API_KEY を設定してください。")
        print("キーの取得: https://aistudio.google.com/apikey")
        return
    r = requests.get("https://generativelanguage.googleapis.com/v1beta/models", params={"key": key}, timeout=60)
    r.raise_for_status()
    for m in r.json().get("models", []):
        methods = ",".join(m.get("supportedGenerationMethods", []))
        if "generateContent" in methods:
            print(f"{m['name'].replace('models/', ''):40s} {m.get('displayName','')}")


if __name__ == "__main__":
    main()
