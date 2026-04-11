# 0416Zenen-Shinsaibashi

心斎橋の会食店「Zenen Shinsaibashi」向け Instagram 運用素材のリポジトリ。

## ディレクトリ構成

```
images/                素材画像置き場（差し替え用）
scripts/
  generate_reel.py     ffmpeg ベースの Reels 動画生成スクリプト
output/
  reel_w3_hikakukentou2.mp4   第3週「比較検討②」プレースホルダ動画
```

## Reels 動画生成

### 前提

- `ffmpeg`（`drawtext` は不要、`subtitles`/`libass` を使用）
- 日本語フォント（`fonts-ipafont-gothic` など）
- Python 3.9+

`ffmpeg` が PATH にない環境では `pip install imageio-ffmpeg` で静的ビルドを利用可能です。

### 素材

各シーンの背景はリポジトリ直下に配置されている以下を参照します:

- `陽明 Youmei.JPG` — 03 陽明 Youmei / 08 CTA ヒーロー
- ` 日月 Nichigetsu02.JPG` — 04 日月 Nichigetsu
- `梨山 rizan01.JPG` — 05 梨山 rizan
- `clideo_editor_e9c04e2420fe4c5fbf9ff8c0e9ab7f6a.mp4` — 07 季節の設え（生け花）

画像/動画を差し替える場合は `scripts/generate_reel.py` の `SCENES` の
`image=` / `video=` を書き換えてください。動画には `video_logo_box=(x,y,w,h)` で
透かしを塗り潰す範囲を指定できます（ソース座標）。

### 実行

```bash
python3 scripts/generate_reel.py
# 出力: output/reel_w3_hikakukentou2.mp4
```

別の出力先に書き出す場合:

```bash
python3 scripts/generate_reel.py --out output/draft.mp4
```

## 第3週：比較検討② — v5 動画仕様

**コンセプト**: 静けさを設える。高級業態向けの落ち着いたシネマティック。
スラム・疑問詞を排除し、断定調の短文と余白で格を表現。最後に
実店舗情報をスタッガード・フェードで提示。

| 項目 | 値 |
|---|---|
| 目的 | 実際の利用シーンを想起させる |
| 訴求軸 | 接待 / 会食 / 顔合わせ / 個室 / 席間 / 静かな会話 |
| ターゲット | 30〜50代経営者の接待、40代以上の会食 |
| 最重要価値 | 失敗しない安心感 |
| 解像度 | 1080×1920 (9:16) |
| 尺 | 31.0秒 |
| カット数 | 9 カット（平均 3.4 秒 / カット） |
| フレームレート | 30fps |
| コーデック | H.264 High / yuv420p / faststart (CRF 19) |
| 音声 | AAC 48kHz ステレオ（無音トラック） |
| カメラワーク | ごく控えめな Ken Burns 1.00〜1.10 |
| フェード | 0.35 秒（前後）でクロスフェード風の繋ぎ |
| 色調整 | eq brightness -0.03 / contrast 1.02 / saturation 0.94 |
| 文字演出 | `\fad` `\fade` による静かな立ち上げ、ポップ無し |
| 透かし処理 | 動画の `clideo.com` ロゴは drawbox で黒塗り + 不透明帯で被せる |

### 構成（9 カット）

| # | 時刻 | 尺 | Kind | 内容 |
|---|---|---|---|---|
| 1 | 0.0–3.0 | 3.0s | photo_intro | 陽明（ゆるやかな引き）+ 「大切な、ひと席を。」遅れて浮上 |
| 2 | 3.0–5.5 | 2.5s | text_black | 黒 + 「すべて、完全個室。」 |
| 3 | 5.5–9.5 | 4.0s | photo_tag | 陽明 / 左下タグ「陽明 Youmei ／ 2〜6名様」 |
| 4 | 9.5–13.5 | 4.0s | photo_tag | 日月 / 左下タグ「日月 Nichigetsu ／ 2〜6名様」 |
| 5 | 13.5–17.5 | 4.0s | photo_tag | 梨山 / 左下タグ「梨山 rizan ／ 7〜10名様」 |
| 6 | 17.5–19.5 | 2.0s | bridge | 生け花 + 「細やかな、おもてなし。」 |
| 7 | 19.5–22.5 | 3.0s | brand_reveal | 黒 + 「心斎橋　禅園 / Shinsaibashi Zenen」 |
| 8 | 22.5–28.0 | 5.5s | info_card | 住所・電話・営業時間（スタッガード・フェード） |
| 9 | 28.0–31.0 | 3.0s | cta_final | 黒 + 「詳しくは、プロフィールへ。」 |

### 店舗情報カード (info_card)

以下の内容を順番にフェードインさせて表示します:

```
       心斎橋　禅園
     Shinsaibashi Zenen
     ────────────
       〒542-0086
     大阪市中央区西心斎橋 1-3-3
     オー・エム・ホテル日航ビル B2F

      TEL  06-6241-7027

     LUNCH    11:30 – 14:45  (L.O. 14:00)
     DINNER  17:00 – 22:00  (L.O. 21:00)

     定休日  不定休（施設に準ずる）

     詳しくは、プロフィールへ
```

各行には `\fade()` で 200〜2000ms の遅れを付け、行ごとに順番に立ち上げて
落ち着いた視線誘導を実現しています。

### セーフエリア

Instagram Reels の UI が被る範囲（上 220px / 下 400px）を避け、タグや
CTA は中央〜下方の安全域に配置。
