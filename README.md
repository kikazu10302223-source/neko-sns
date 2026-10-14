# ねこSNS投稿パイプライン（X / Instagram / Threads）

愛猫の写真をためておくと、AIが写真を見て文面を作り、SNSごとに最適な形へ整える仕組みです。
「同じ写真を2回出してしまう」を防ぐ重複判定つき。

**投稿のしかたは2通り。どちらでも動きます。**

| | **手動モード（おすすめ）** | **自動投稿モード** |
|---|---|---|
| やること | 加工済み画像＋文面を「投稿キュー」に自動で用意。あとはスマホでコピペして自分で投稿 | 3つのSNSへ完全自動で投稿 |
| 手間 | 1件あたり 1〜2分 | 0分 |
| **月額** | **0円** | 月50〜300円（Xの従量課金） |
| 必要なAPIキー | Gemini と Cloudinary の **4つだけ** | さらに X・Instagram・Threads の分（計10個） |
| Xの開発者登録・審査 | **不要** | 必要 |
| トークン更新（60日ごと） | **不要** | Instagramは必要 |
| 規約違反リスク | **ゼロ**（自動投稿ツールではない） | 低いがゼロではない |
| 投稿前の人の確認 | できる | できない |

> **はじめてなら手動モードがおすすめです。**
> XのAPIは2026年2月に従量課金へ全面移行し、無料枠は新規では実質終了しました。手動モードなら**XのAPIを一切使わない**ので、課金も開発者審査も不要です。しかも投稿前に文面を確認できるので、AIの当たり外れを人の目でふるいにかけられます。

```
写真をためる → 重複チェック → 加工（比率・明るさ・透かし） → AIがSNS別に文面作成
                                                              │
        ┌─────────────────────────────────────────────────────┴──────────────┐
        ↓                                                                    ↓
【手動モード】投稿キュー（スマホ用ページ）を作成                      【自動モード】3つのSNSへ自動投稿
   → コピペして自分で投稿（1件1〜2分）                                  → 全自動（0分）
        └──────────────────────────────┬─────────────────────────────────────┘
                                       ↓
                              台帳に記録（次回の重複判定に使う）
```

---

## 目次

1. [手動モードのしくみと毎日の使い方](#1-手動モードのしくみと毎日の使い方)
2. [料金比較（無料でどこまでできるか）](#2-料金比較無料でどこまでできるか)
3. [全体の設計と、なぜこの構成なのか](#3-全体の設計となぜこの構成なのか)
4. [セットアップ手順](#4-セットアップ手順)
5. [二人で使うための運用ルール](#5-二人で使うための運用ルール)
6. [コマンド一覧](#6-コマンド一覧)
7. [つまずきやすいポイント](#7-つまずきやすいポイント)
8. [発展：さらに賢くする](#8-発展さらに賢くする)

---

## 1. 手動モードのしくみと毎日の使い方

### しくみ

1. **写真をためる**（スマホからCloudinaryの`neko`フォルダへアップロードするだけ）
2. **1日3回（8:00 / 12:30 / 20:00）**、GitHubが自動で動いて、
   - まだ使っていない写真を1枚えらぶ（重複判定つき）
   - 4:5にトリミング・明るさ補正・透かしを入れる
   - AIが「X用」「Instagram用」「Threads用」の3種類の文面を書く
   - それらを**「投稿キュー」ページ**にまとめる
3. **あなたがスマホでキューを開いて投稿する**（コピペ）

出来上がるのは、こんなページです（スマホで開きます）。

```
┌─────────────────────────────────┐
│  投稿キュー                      │
│  むぎの投稿ストック               │
│                                  │
│  ┌───────────────────────────┐  │
│  │      （加工済みの写真）      │  │
│  │            [画像を保存]      │  │
│  └───────────────────────────┘  │
│  10/14 20:00  ソファで丸くなって寝て… │
│                                  │
│  [X 本文]            [コピー]     │
│  ┌───────────────────────────┐  │
│  │ 今日のむぎ。この顔だけで…    │  │
│  └───────────────────────────┘  │
│  [X リプライ]        [コピー]     │
│  [Instagram]         [コピー]     │
│  [Threads]           [コピー]     │
│                                  │
│  ☐ この投稿は終わった             │
│                                  │
│  ┌─ 次の写真 ──────────────┐    │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

### 毎日の使い方（1件あたり1〜2分）

| 手順 | やること |
|---|---|
| 1 | スマホで投稿キューのURLを開く（ホーム画面に追加しておくと一発です） |
| 2 | 写真を**長押し**して「写真に追加」で保存（「画像を保存」ボタンでもOK） |
| 3 | 「コピー」を押して文面をコピー → X / Instagram / Threads のアプリで貼り付け、画像を選んで投稿 |
| 4 | 終わったら「この投稿は終わった」にチェック（その端末にだけ記録されます） |

**Xでのコツ：** 本文にはURLを入れず、**投稿したあとに自分でリプライ**してショップURLを貼ります。Xはリンク付きの投稿を表示で不利に扱うためです。キューには「X リプライ」用の文面も別に用意してあります。

**Instagramでのコツ：** Instagramは本文にリンクを貼れません。プロフィール欄か、**最初のコメント**にショップURLを置いてください。

### 「投稿したかどうか」の管理

- キューは**最新12件**を残します（`manual.queue_size` で変更可）。古いものから自動で消えます。
- チェックしたかどうかは**あなたのスマホの中にだけ**記録されます（サーバーには送りません）。
- 一度キューに出た写真は「使用済み」として台帳に記録されるので、**次回以降は二度と出てきません**。

---

## 2. 料金比較（無料でどこまでできるか）

### 2-1. 手動モードのランニングコスト

| 使うもの | 役割 | 無料枠 | 実費 |
|---|---|---|---|
| **GitHub Actions** | 定時実行する「目覚まし時計」 | パブリックは無料。プライベートでも月2,000分（Freeプラン） | **0円**（1日3回×2分＝月180分程度） |
| **GitHub Pages** | 投稿キューをスマホに配信 | 無料（パブリック／プライベートどちらでも） | **0円** |
| **Gemini API** | 写真を見て文面を作る | 無料枠あり（モデルごとにRPM/RPDの上限。数値は変動するため [AI Studioのレート制限画面](https://aistudio.google.com/rate-limit) で確認） | **0円**（1日3回の利用なら余裕） |
| **Cloudinary** | 写真の置き場（スマホからの投入口） | 無料枠 月25クレジット（過去30日で計測）。1クレジット＝変換1,000回 or ストレージ1GiB or 帯域1GiB | **0円** |
| **X / Instagram / Threads のAPI** | — | **使いません** | **0円** |
| **合計** | | | **0円** |

> **手動モードなら、ランニングコストは文字どおり0円です。** Xの従量課金は「API経由で投稿したとき」だけ発生するので、自分でアプリから投稿する分には1円もかかりません。

### 2-2. 自動投稿モードにした場合の追加コスト

| 使うもの | 無料枠 | 実費 |
|---|---|---|
| Instagram API | 無料（24時間100投稿まで） | **0円** |
| Threads API | 無料（1日250投稿） | **0円** |
| **X API** | 無料枠は新規では実質終了 | **月50〜300円**（従量課金） |
| **合計** | | **月50〜300円** |

### 2-3. X APIの料金（2026年2月に全面改定）

| 項目 | 単価 |
|---|---|
| ポスト作成（通常） | **$0.015 / 件**（約2.3円） |
| ポスト作成（**URL入り**） | **$0.20 / 件**（約30円）※2026年4月改定 |
| ポスト読み取り | $0.005 / 件（自分のデータは$0.001） |
| 月額固定費 | $0（最低$5からクレジット購入） |
| Basic $200/月・Pro $5,000/月 | **既存契約者のみ**。新規申込不可 |

- 出典：[X API料金 2026年版](https://postproxy.dev/blog/x-api-pricing-2026/) ／ [Pay-Per-UseとBasicの比較](https://a1026302.hatenablog.com/entry/2026/06/12/092249) ／ [X公式発表の報道](https://gigazine.net/news/20260209-x-api-pay-per-use/)
- 参考：1日3件を自動投稿した場合、1日3件×$0.015＝月約$1.35（**約200円**）。URLを本文に入れると1件$0.20になるため、**リンクはリプライに逃がす**のが定石です。

### 2-4. 「ノーコード」と「自作」の比較

| 方式 | 初期工数 | 月額 | 重複判定 | SNS別の文面自動変換 | 画像加工 |
|---|---|---|---|---|---|
| **本リポジトリ（自作）** | 30分〜半日 | **0円**（手動モード） | ◎ | ◎ | ◎ |
| Make（無料プラン） | 1〜2時間 | 0円（月1,000オペレーション・2シナリオまで） | △（自作が必要） | △ | △ |
| n8n（セルフホスト） | 1日 | 0円＋サーバ代（月500〜1,500円程度） | △ | ○ | △ |
| Zapier | 30分 | 無料枠は少なめ／有料は月$20〜 | × | △ | × |
| Buffer・SocialDog等の予約投稿ツール | 15分 | 月1,000〜3,000円 | ×（手動管理） | × | △ |

- Makeの無料枠は「月1,000オペレーション・2シナリオ」（[比較記事](https://www.cipherprojects.com/blog/posts/n8n-vs-make-automation-platform-comparison/)）
- n8nはセルフホストなら無料、クラウドは有料（[n8n公式](https://n8n.io/pricing/)）

**結論：** 「重複判定」と「SNSごとの文面変換」と「画像加工」を全部自動でやるなら、既製ツールでは足りません。**自作（このリポジトリ）が一番安くて一番高機能**です。設定は初回だけなので、そこだけ頑張る価値があります。

---

## 3. 全体の設計と、なぜこの構成なのか

### なぜ「手動モード」を既定にしているのか

| 観点 | 手動モード | 自動投稿モード |
|---|---|---|
| コスト | 0円 | Xの分だけ課金 |
| セットアップ | 鍵4つ。Xの開発者登録なし | 鍵10個。Xの審査・課金設定・Metaの審査 |
| 継続のしきい値 | 60日ごとのトークン更新が不要 | Instagramの長期トークン（60日）を更新し続ける必要 |
| リスク | 規約上「自動投稿ツール」ではないので停止リスクがゼロ | 自動化ルールに触れる可能性が残る |
| 品質 | 投稿前に人がチェックできる | AIの出力がそのまま公開される |

自動投稿は「楽」ですが、**維持コスト（トークン更新・課金・規約）**がじわじわ効いてきます。
まず手動モードで「AIの文面が自分のアカウントに合うか」を確かめてから、自動化に進むのが安全です。
`config.yaml` の `mode` を書き換えるだけでいつでも切り替えられます。

### なぜ「Cloudinary」を挟むのか

スマホから写真を入れる「投入口」として使います。スマホのブラウザでCloudinaryを開いて`neko`フォルダにアップロードするだけなので、夫婦二人での運用に向いています。

（自動投稿モードでは、もう一つ役割が増えます。InstagramのAPIは**Metaのサーバーが画像を自分で取りに行く方式**なので、「あなたのパソコンの中のファイル」は渡せません。誰でも見られる公開URLが必要になり、それをCloudinaryが担当します。）

### なぜ「GitHub Actions」で動かすのか

- パソコンの電源が入っていなくても、決まった時刻に自動で動く
- サーバを借りる必要がない（＝月0円）
- 実行履歴とエラーが画面で見られる（何が起きたか分かる）

### なぜ「GitHub Pages」でキューを配信するのか

スマホから見るには「どこかから配信」が必要です。GitHub Pagesは無料でHTTPS配信でき、**コピーボタン（クリップボード）がスマホでも動く**のが決め手です。ファイルをメールで送る運用にすると毎回の手間が増えて続きません。

> ⚠️ **公開範囲について（正直な話）**
> GitHub Pages のURLは、リポジトリが非公開でも**URLを知っている人は見られます**（推測は難しいですが、厳密な非公開にはできません）。
> 猫の写真はどのみちSNSで公開するものなので実害は少ないですが、**顔写真や住所が写った写真を入れるのは避けてください**。気になる場合は、キューをPagesではなく**Artifact（Actionsの実行結果に添付されるZIP）**から取り出す運用にもできます（README末尾の「発展」参照）。

### 重複判定のしくみ

2段構えです。

1. **sha256（完全一致）** … まったく同じファイルかどうか。指紋のようなもの。
2. **dhash（知覚ハッシュ）** … 画像を64個の「明暗のガタつき」に圧縮し、その差（ハミング距離）で比べる。**リサイズ・再保存・軽いトリミングをされても「同じ写真」と判定できます。**

```
しきい値 dhash_distance: 6   ← 数字を小さくすると厳しく、大きくすると緩くなる
 ・誤って別の写真を「同じ」と言われるのが嫌 → 4
 ・同じ写真を出してしまうのが嫌            → 8
```

> **正直な限界：** 大幅にトリミングした写真や、別の日に撮ったよく似た構図は「別物」と判定されることがあります。逆に、よく似た構図の別写真を「同じ」と誤判定することもあります。完璧な判定は原理的に難しいため、`--dry-run` で確認できるようにしています。

---

## 4. セットアップ手順

### 4-A. 手動モード（かんたんコース・約30分・無料）

#### ステップ0：このフォルダをGitHubに置く

1. GitHubで **Private リポジトリ**を新規作成（名前例：`neko-sns`）
2. このフォルダの中身をアップロード（`git push` でも、GitHubの「Add file → Upload files」でも可）

> Private にしても GitHub Actions は月2,000分まで無料です。写真はリポジトリに入れないので容量は増えません。

#### ステップ1：Gemini APIキーを取る（無料・3分）

1. https://aistudio.google.com/apikey を開く
2. 「APIキーを作成」→ 表示された文字列をコピー（これが `GEMINI_API_KEY`）
3. 使えるモデル名を確認したい場合：
   ```bash
   GEMINI_API_KEY=取得したキー python -m src.list_models
   ```
   `config.yaml` の `ai.model` に、出てきた中から速くて安いFlash系を書きます（例：`gemini-2.5-flash`）。

> ⚠️ **無料枠の注意：** 無料枠で入力した画像・文章は、Googleのサービス改善に使われる可能性があります。気になる場合は有料枠（Tier 1）に切り替えると使われません。詳細は[公式の料金ページ](https://ai.google.dev/gemini-api/docs/pricing)の注記を確認してください。

#### ステップ2：Cloudinary（写真の置き場）を作る（無料・5分）

1. https://cloudinary.com/ で無料登録
2. ダッシュボードの **Cloud name / API Key / API Secret** をメモ
3. **Settings → Upload → Add upload preset** で、`Signing Mode` を **Unsigned** にしたプリセットを作り、名前をメモ（例：`neko_upload`）
4. Media Library で **`neko` というフォルダ**を作る（`config.yaml` の `source.cloudinary_folder` と合わせる）

**写真の入れ方（二人で使う場合）：** スマホのブラウザで Cloudinary にログイン → Media Library → `neko` フォルダを開く → アップロード。Google Drive にためておいて、まとめてアップロードでもOKです。

#### ステップ3：GitHubに秘密情報を登録する（4つだけ）

リポジトリ → **Settings → Secrets and variables → Actions → New repository secret** で、以下を1つずつ登録します。

| Secret名 | 中身 |
|---|---|
| `GEMINI_API_KEY` | ステップ1のキー |
| `CLOUDINARY_CLOUD_NAME` | ステップ2 |
| `CLOUDINARY_API_KEY` | ステップ2 |
| `CLOUDINARY_API_SECRET` | ステップ2 |
| `CLOUDINARY_UPLOAD_PRESET` | ステップ2のプリセット名（例：`neko_upload`） |

> **手動モードでは X / Instagram / Threads の鍵は一切不要です。** 自動投稿モードに切り替えるときだけ、4-B の手順を追加してください。
>
> **秘密情報は絶対に `config.yaml` に書かないでください。** この設計では、コードに鍵を一切埋め込みません。

#### ステップ4：設定を自分の猫に合わせる

**GitHub上で `config.example.yaml` を直接編集します**（ワークフローがこれを `config.yaml` としてコピーして使うためです）。上部の `profile` を書き換えてください。

```yaml
mode: "manual"          # ← これが手動モードの指定

profile:
  cat_name: "むぎ"
  cat_traits: "キジトラ、甘えん坊、食いしん坊、昼寝が得意"
  account_concept: "愛猫の日常と、その写真から生まれたグッズのお店"
  shop_name: "むぎ屋"
  shop_url: "https://suzuri.jp/あなたのショップID"
  tone: "親しみやすく、少しユーモア。絵文字は1〜2個まで。売り込み感は弱め"
  ng_words: ["かわいいだけ", "拡散希望"]
```

**ここが一番大事です。** AIはこの情報を見て文面を作るので、`cat_traits` と `tone` が具体的なほど「その猫らしい」投稿になります。

#### ステップ5：GitHub Pages を有効にする

1. リポジトリ → **Settings → Pages**
2. **Source** を **「GitHub Actions」** にする

> ワークフロー側でも自動有効化を試みますが、うまくいかない場合はここで手動設定してください。これが最初のつまずきポイントです。

#### ステップ6：動かして確認する

1. **Actions タブ → neko-post-queue → Run workflow** を押す
2. 1〜2分待つと緑のチェックが付きます
3. **投稿キューのURL**を開く：
   ```
   https://あなたのユーザー名.github.io/リポジトリ名/
   ```
   例：ユーザー名が `mugi`、リポジトリ名が `neko-sns` なら `https://mugi.github.io/neko-sns/`
4. 写真が1件、X / Instagram / Threads の文面つきで並んでいれば成功です

**スマホのホーム画面に追加しておきましょう。** Safari／Chromeで開いて「ホーム画面に追加」を選ぶと、アプリのように一発で開けます。

> キューが空のときは、Cloudinaryの`neko`フォルダに写真が入っているか確認してください。

#### ステップ7：PCで試したいとき（任意）

```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml     # config.yaml を編集
python -m src.main --check             # 設定と接続の確認
python -m src.main --mode manual --limit 1   # キューを1件作る
```

`docs/index.html` をブラウザで開けば、スマホで見るのと同じページを確認できます。

---

### 4-B. 自動投稿モードに切り替える（追加でやること）

手動モードに慣れて「これは任せられる」と思えたら、ここから先を追加します。

1. **X（Twitter）のAPIキーを取る**
   1. https://developer.x.com/ で開発者登録（無料。クレジットは後から$5〜チャージ）
   2. **Project を作成**し、その中に **App** を作る
      - ⚠️ Project の外に作った App では v2 の API が失敗します
   3. App の **User authentication settings** で OAuth 2.0 を有効化
      - App permissions：**Read and write** ／ Type of App：**Web App / Automated App or Bot**
      - Callback URI：`http://localhost:8080/callback`（ダミーでOK）
   4. **Keys and tokens** から **Access Token** を取得
   5. **Spending Limit（支出上限）** を必ず設定（例：月$5）
2. **Instagram をプロアカウントにする**
   1. Instagramアプリ → 設定 → アカウントの種類 → **プロアカウントに切り替える**
   2. https://developers.facebook.com/ でアプリ作成 → ユースケースで **Instagram** を追加
   3. **Instagram API setup with Instagram login** を選ぶ（Facebookページが不要な方式）
   4. 権限 `instagram_business_basic` / `instagram_business_content_publish` を付与してトークン発行
   5. 短期トークン（1時間）→ **長期トークン（60日）に交換**
3. **Threads のAPIキーを取る** … 同じMetaアプリに **Threads API** を追加し、`threads_basic` / `threads_content_publish` を付与
4. **Secrets を追加** … `X_ACCESS_TOKEN` / `IG_USER_ID` / `IG_ACCESS_TOKEN` / `THREADS_USER_ID` / `THREADS_ACCESS_TOKEN`
5. **設定を切り替える**
   - `config.example.yaml` の `mode:` を `"auto"` に
   - `.github/workflows/post.yml` の実行行を `python -m src.main --mode manual --limit 1` → `python -m src.main --mode auto --limit 1` に

> **審査は必要？** 自分・自社のアカウントに投稿するだけなら **Standard Access のままでOK、App Review は不要**です（[Meta公式](https://developers.facebook.com/docs/instagram-platform/overview)）。
>
> ⚠️ **Instagramの長期トークンは60日で切れます。** カレンダーに更新リマインダーを入れてください（`--check` で確認できます）。

---

## 5. 二人で使うための運用ルール

| 場面 | おすすめのやり方 |
|---|---|
| 写真をためる | スマホから Cloudinary の `neko` フォルダにアップロード（二人とも同じアカウントでOK） |
| キューが更新されるタイミング | 1日3回（8:00 / 12:30 / 20:00 JST）。`posting.max_per_day: 3` で1日の件数を管理 |
| 「今日はこの写真を出したい」 | その写真だけをフォルダに入れておく（ファイル名順に処理されます） |
| 「この文面はイヤだ」 | `profile.tone` と `profile.ng_words` に追記する。AIは次回から避けます |
| 急いで1件ほしい | Actions タブ → Run workflow を押せば、その場でキューが1件増えます |
| 一時停止したい | Actions タブからワークフローを Disable にする |
| 投稿の記録を消したい | `data/state.sqlite3` を削除（＝全写真が「未使用」に戻ります） |

**喧嘩にならないコツ：** 「投稿の決定権は人間、作業はAI」にすること。AIは提案するだけにして、月に一度二人で `profile.tone` を見直す時間を取ると、だんだん「自分たちの言葉」になっていきます。

---

## 6. コマンド一覧

```bash
# ── 手動モード（既定）──────────────────────────
python -m src.main --check                     # 設定と接続の確認
python -m src.main --mode manual --limit 1     # 投稿キューを1件作る
python -m src.main --mode manual --limit 3     # まとめて3件作る
python -m src.main --dry-run                   # AIを使わず定型文で試す（鍵が無くても動きます）

# ── 自動投稿モード ─────────────────────────────
python -m src.main --mode auto --dry-run       # 投稿せずに内容だけ確認
python -m src.main --mode auto --limit 1       # 1枚だけ実際に投稿
python -m src.main --mode auto --platform x    # Xだけに投稿

# ── その他 ─────────────────────────────────────
python -m src.main --prepare                   # --mode manual と同じ
GEMINI_API_KEY=xxx python -m src.list_models   # 使えるGeminiモデル一覧
```

| ファイル | 役割 |
|---|---|
| `src/main.py` | 全体の進行役（モードの切り替えはここ） |
| `src/sources.py` | 写真の取り込み（Cloudinary / ローカルフォルダ） |
| `src/dedupe.py` | 重複判定（sha256＋知覚ハッシュ） |
| `src/imageprep.py` | 比率変換・明るさ補正・透かし・縮小 |
| `src/caption.py` | AIによるSNS別の文面作成 |
| `src/queue.py` | **投稿キュー（スマホ用ページ）の生成** |
| `src/cloudinary_upload.py` | 加工済み画像を公開URL化（自動投稿モード用） |
| `src/publish_x.py` / `publish_ig.py` / `publish_threads.py` | 各SNSへの投稿（自動投稿モード用） |
| `src/store.py` | 台帳（SQLite）。重複判定とキューの管理 |
| `docs/index.html` | 生成される投稿キューページ |
| `.github/workflows/post.yml` | 定時実行とPages公開の設定 |

---

## 7. つまずきやすいポイント

| 症状 | 原因と対処 |
|---|---|
| キューのURLを開いても404 | **Settings → Pages** の Source が「GitHub Actions」になっていない。設定後にワークフローをもう一度実行する |
| キューが空のまま | Cloudinaryの`neko`フォルダに写真が入っていない、または全部「使用済み」。Actionsのログで `写真 0 枚を検出` を確認 |
| 文面が定型文になる | `GEMINI_API_KEY` が未設定。Secretsを登録して再実行 |
| 同じ写真が2回出た | `dedupe.dhash_distance` を小さくする（4など） |
| 別の写真なのに「使用済み」と言われる | `dedupe.dhash_distance` を大きくする（8〜10） |
| 「画像を保存」が出ない | スマホで画像を**長押し**すれば保存メニューが出ます。それでもダメな場合はスクリーンショットで代用 |
| コピーボタンが効かない | HTTPSでないとクリップボードが使えない場合があります。GitHub PagesのURL（`https://…`）から開いているか確認 |
| Actionsが動かない | スケジュール実行は**デフォルトブランチ**でのみ動きます。またcronは数分〜十数分遅れることがあります（仕様） |
| 投稿文が日本語として変 | `profile.tone` を具体的にする。`ai.temperature` を 0.8 程度に下げると安定します |
| **自動投稿モードで** Instagramが `Only photo or video can be accepted` | 画像がJPEG以外、または公開URLにMetaがアクセスできていない |
| **自動投稿モードで** Instagramが `The access token could not be decrypted` | 長期トークン（60日）が切れた。再発行する |
| **自動投稿モードで** Xが `403 Forbidden` | AppがProjectの外にある／権限がRead only。App permissionsを `Read and write` に |
| **自動投稿モードで** Xが `429 Too Many Requests` | レート制限。`posting.jitter_minutes` を増やす |

---

## 8. 発展：さらに賢くする

- **キューをPages以外で受け取る** … GitHub Pagesを公開したくない場合は、Actionsの実行結果に添付される `post-queue` というZIP（Artifact）をダウンロードして開く運用にもできます。毎回の手間は増えますが、公開URLを作らずに済みます。
- **通知を足す** … キューが更新されたらLINEやメールに通知するステップを足すと、投稿を忘れにくくなります。
- **Xのコスト削減**（自動投稿モード）… URLは本文に入れず、リプライに逃がす設定（`posting.link_in_reply: true`）が既定です。プロフィールの固定ポストにショップURLを置くのが最も安上がりです。
- **SUZURIへの誘致** … 投稿→リプライ／プロフィール／固定ポストの3点でリンクを置くのが基本の型。APIでは「ストーリーズのリンクステッカー」は扱えないため、そこは手動で補うのが現実的です。
- **動画・リール対応** … `media_type=REELS` と動画アップロード（resumable）を足せば拡張できます。
- **分析の自動化** … `insights` エンドポイントを使えば、どの投稿が伸びたかを毎週スプレッドシートに貯められます。
- **Threadsを主軸にする** … 無料・1日250投稿・審査が軽いので、Xの課金を抑えたいときの受け皿になります。

---

## 参考リンク

- [X API料金 2026年版（postproxy）](https://postproxy.dev/blog/x-api-pricing-2026/)
- [X API Pay-Per-Use と Basic の比較（2026年6月）](https://a1026302.hatenablog.com/entry/2026/06/12/092249)
- [X公式 自動化ルール（日本語で読むならブラウザ翻訳推奨）](https://help.x.com/en/rules-and-policies/x-automation)
- [Meta公式 Instagram コンテンツ公開API](https://developers.facebook.com/docs/instagram-platform/content-publishing)
- [Meta公式 Instagram Platform 概要（審査の要否）](https://developers.facebook.com/docs/instagram-platform/overview)
- [Meta公式 Threads API](https://developers.facebook.com/docs/threads)
- [Gemini API 料金（無料枠の注記）](https://ai.google.dev/gemini-api/docs/pricing)
- [Cloudinary の料金体系（クレジットの仕組み）](https://dev.classmethod.jp/articles/cloudinary-pricing-and-usage-monitoring-guide/)
- [GitHub Actions の無料枠](https://docs.github.com/ja/billing/concepts/product-billing/github-actions)
- [GitHub Pages の公開範囲](https://docs.github.com/ja/pages/getting-started-with-github-pages/what-is-github-pages)
