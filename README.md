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

## 第3週：比較検討② — 動画仕様

| 項目 | 値 |
|---|---|
| 目的 | 実際の利用シーンを想起させる |
| 訴求軸 | 接待 / 会食 / 顔合わせ / 個室 / 席間 / 導線 / 静かな会話 |
| ターゲット | 30〜50代経営者の接待、40代以上の会食 |
| 最重要価値 | 失敗しない安心感 |
| 解像度 | 1080×1920 (9:16) |
| 尺 | 29秒 |
| フレームレート | 30fps |
| コーデック | H.264 High / yuv420p / faststart |
| 音声 | AAC 48kHz（無音トラック） |
| カメラワーク | 静止画は Ken Burns 風ゆるやかズーム (1.00⇔1.12) / 動画はソースの動き |
| 色調整 | eq brightness -0.12 / contrast 0.96 / saturation 0.88 |
| 可読性 | libass 字幕にダーク帯オーバーレイを3枚重ね |
| 透かし処理 | 動画の `clideo.com` ロゴは drawbox で黒塗り除去 |

### 構成

| # | 尺 | 役割 | 背景 | テロップ |
|---|---|---|---|---|
| 1 | 3s | Hook | 単色 (coal) | 大切な接待で／失敗したくない方へ |
| 2 | 3s | 共感 | 単色 (navy) | 席が近い。声が響く。／落ち着かない空間は、話も進まない。 |
| 3 | 4s | 陽明 | 陽明 Youmei.JPG | 01 陽明 Youmei／畳に市松、品格の個室／2〜6名 |
| 4 | 4s | 日月 | 日月 Nichigetsu02.JPG | 02 日月 Nichigetsu／品のある和モダン／2〜6名 |
| 5 | 4s | 梨山 | 梨山 rizan01.JPG | 03 梨山 rizan／茶器が彩る禅の空間／7〜10名 |
| 6 | 3s | 共通特長 | 単色 (coal) | すべて完全個室／守られる席間、静かな会話 |
| 7 | 2s | 季節の設え | clideo 動画 | 細部まで、おもてなし／季節の設えで、あなたを迎える |
| 8 | 6s | CTA | 陽明 Youmei.JPG | 大切な一席は／心斎橋 禅園で／Instagramで詳細を見る |

### セーフエリア

Instagram Reels の UI (アカウント情報・いいね・キャプション) が被る範囲を
避けるため、テキストは y=220〜1520 の範囲にまとめています。
