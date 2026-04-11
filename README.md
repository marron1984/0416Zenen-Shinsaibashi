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
- 日本語 明朝フォント（`fonts-ipaexfont-mincho` 推奨）
- Python 3.9+

`ffmpeg` が PATH にない環境では `pip install imageio-ffmpeg` で静的ビルドを
利用可能です。明朝フォントが無い場合は `apt install fonts-ipaexfont-mincho`。

### 素材

全 7 枚の実写と 1 本のブリッジ動画をフルに使用します:

- `陽明 Youmei.JPG` — シーン 1/2（ワイド→タイトクロップで 2 カット）
- ` 日月 Nichigetsu01 .JPG` — シーン 3（タグ付き）
- ` 日月 Nichigetsu02.JPG` — シーン 4（クリーン）
- ` 日月 Nichigetsu03 .JPG` — シーン 5（クリーン）
- `梨山 rizan01.JPG` — シーン 6（タグ付き／茶器）
- `梨山 rizan02.JPG` — シーン 7（クリーン）
- `梨山 rizan03.JPG` — シーン 8（クリーン）
- `clideo_editor_e9c04e2420fe4c5fbf9ff8c0e9ab7f6a.mp4` — シーン 10（生け花）

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

## 第3週：比較検討② — v6 動画仕様

**コンセプト**: エディトリアル明朝。写真優位で 8 カットの実写を畳み掛け、
小さめの明朝体と広いレタースペーシングで上質感を表現。最後に店舗情報カード。

| 項目 | 値 |
|---|---|
| 目的 | 実際の利用シーンを想起させる |
| 訴求軸 | 接待 / 会食 / 顔合わせ / 個室 / 席間 / 静かな会話 |
| ターゲット | 30〜50代経営者の接待、40代以上の会食 |
| 最重要価値 | 失敗しない安心感 |
| 解像度 | 1080×1920 (9:16) |
| 尺 | 34.3 秒 |
| カット数 | 13 カット（うち実写 8、動画 1） |
| 平均カット長 | 約 2.6 秒 |
| フォント | **IPAex明朝 (IPAexMincho)** |
| 文字サイズ | 22〜84pt（editorial 寄りの小さめ） |
| レタースペーシング | `\fsp` 2〜10 で広め |
| フレームレート | 30fps |
| コーデック | H.264 High / yuv420p / faststart (CRF 19) |
| カメラワーク | ごく控えめな Ken Burns 1.00〜1.08、in/out 交互 |
| フェード | 0.35 秒（前後） |

### 構成（13 カット）

| # | 時刻 | 尺 | Kind | 内容 |
|---|---|---|---|---|
|  1 |  0.0– 3.3 | 3.3s | photo_tag    | 陽明 Youmei ワイド + タグ「陽明  Youmei ／ 2〜6名様」 |
|  2 |  3.3– 5.5 | 2.2s | photo        | 陽明 タイト（左寄せクロップ、丸窓） |
|  3 |  5.5– 8.5 | 3.0s | photo_tag    | 日月 Nichigetsu01 + タグ「日月  Nichigetsu ／ 2〜6名様」 |
|  4 |  8.5–10.5 | 2.0s | photo        | 日月 Nichigetsu02（別アングル） |
|  5 | 10.5–12.5 | 2.0s | photo        | 日月 Nichigetsu03（別アングル） |
|  6 | 12.5–15.5 | 3.0s | photo_tag    | 梨山 rizan01 + タグ「梨山  rizan ／ 7〜10名様」 |
|  7 | 15.5–17.5 | 2.0s | photo        | 梨山 rizan02（別アングル） |
|  8 | 17.5–19.5 | 2.0s | photo        | 梨山 rizan03（別アングル） |
|  9 | 19.5–21.8 | 2.3s | text_black   | 黒 + 明朝「すべて、完全個室。」 |
| 10 | 21.8–23.8 | 2.0s | bridge       | 生け花 + 「細やかな、おもてなし。」 |
| 11 | 23.8–26.3 | 2.5s | brand_reveal | 黒 + 「心斎橋　禅園 / Shinsaibashi Zenen」 |
| 12 | 26.3–31.8 | 5.5s | info_card    | 住所・電話・営業時間（スタッガード・フェード） |
| 13 | 31.8–34.3 | 2.5s | cta_final    | 黒 + 「詳しくは、プロフィールへ。」 |

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
