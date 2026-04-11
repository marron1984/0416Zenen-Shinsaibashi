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

## 第3週：比較検討② — v4 動画仕様

**コンセプト**: Reels 感強め・テンポ重視。スラム → 実写 → スラム → 実写 のリズムで
視線を奪い続ける。写真は主役、テキストは情報の区切りとして機能。

| 項目 | 値 |
|---|---|
| 目的 | 実際の利用シーンを想起させる |
| 訴求軸 | 接待 / 会食 / 顔合わせ / 個室 / 席間 / 静かな会話 |
| ターゲット | 30〜50代経営者の接待、40代以上の会食 |
| 最重要価値 | 失敗しない安心感 |
| 解像度 | 1080×1920 (9:16) |
| 尺 | 19.3秒（Reels スイートスポット） |
| カット数 | 13 カット（平均 1.5 秒 / カット） |
| フレームレート | 30fps |
| コーデック | H.264 High / yuv420p / faststart (CRF 19) |
| 音声 | AAC 48kHz ステレオ（無音トラック） |
| カメラワーク | 大胆な Ken Burns 1.00〜1.25、in/out をシーン毎に反転 |
| 色調整 | eq brightness -0.04 / contrast 1.02 / saturation 0.95（自然寄り） |
| 文字演出 | ASS `\t` で 85%→100% ポップアップ、`\move` で下から浮上 |
| 透かし処理 | 動画の `clideo.com` ロゴは drawbox で黒塗り除去 |

### 構成（13 カット）

| # | 時刻 | 尺 | Kind | 内容 |
|---|---|---|---|---|
| 1 | 0.0–0.6 | 0.6s | slam | 「その接待、」 |
| 2 | 0.6–1.1 | 0.5s | slam | 「席、大丈夫？」 |
| 3 | 1.1–2.8 | 1.7s | photo_tag | 陽明 Youmei ワイド（01 タグ） |
| 4 | 2.8–4.1 | 1.3s | photo | 陽明 左寄せタイト（無地） |
| 5 | 4.1–5.8 | 1.7s | photo_tag | 日月 Nichigetsu ワイド（02 タグ） |
| 6 | 5.8–7.1 | 1.3s | photo | 日月 右寄せタイト |
| 7 | 7.1–8.8 | 1.7s | photo_tag | 梨山 rizan ワイド（03 タグ） |
| 8 | 8.8–10.1 | 1.3s | photo | 梨山 左寄せタイト（茶器アップ） |
| 9 | 10.1–10.9 | 0.8s | slam | 「すべて完全個室」 |
| 10 | 10.9–11.7 | 0.8s | slam | 「2〜10名 対応」 |
| 11 | 11.7–13.7 | 2.0s | bridge | 生け花 + 「細部まで、／おもてなし」 |
| 12 | 13.7–16.0 | 2.3s | cta_wide | 陽明 + 「心斎橋 禅園」下から浮上 |
| 13 | 16.0–19.3 | 3.3s | cta_text | 陽明 + 「プロフィールから／ご予約・詳細」 |

### 写真の使い回し

同じ写真を 2 カットで使うとき、以下を変えることで別ショットに見せています:

| 要素 | ワイド | タイト |
|---|---|---|
| crop_x_pct | 0.5（中央） | 0.30〜0.65（端寄せ） |
| zoom | 1.00 → 1.18（ズームイン） | 1.25 → 1.10（ズームアウト） |
| タグ | あり | なし |

### セーフエリア

Instagram Reels の UI が被る範囲（上 220px / 下 400px）を避け、小さいタグは
左下隅（y=1650–1830）、スラムは中央（y=960）に配置。
