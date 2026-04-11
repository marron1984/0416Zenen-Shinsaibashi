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
| 尺 | 24秒 |
| フレームレート | 30fps |
| コーデック | H.264 High / yuv420p / faststart |
| 音声 | AAC 48kHz（無音トラック） |

### 構成

| # | 尺 | 役割 | テロップ |
|---|---|---|---|
| 1 | 3s | Hook | 大切な接待で／失敗したくない方へ |
| 2 | 3s | 共感 | 席が近い。声が響く。／落ち着いて話せない。 |
| 3 | 3s | 特長① | 01 完全個室／誰にも聞かれない空間 |
| 4 | 3s | 特長② | 02 ゆとりある席間／自然と距離が守られる |
| 5 | 3s | 特長③ | 03 静かな導線設計／来店から退店まで気を遣わせない |
| 6 | 3s | 特長④ | 04 会食・顔合わせに最適／格式と寛ぎを両立 |
| 7 | 6s | CTA | 大切な一席は／心斎橋の会食処で／Instagramで詳細を見る |

## 現状と今後

現在 `output/reel_w3_hikakukentou2.mp4` は **テロップのみのプレースホルダ** です。
実写素材（個室・席間・料理・導線）が揃い次第、`scripts/generate_reel.py` の
背景部分（`color=c=...` ソース）を画像/動画入力に差し替えて本番用を生成します。
