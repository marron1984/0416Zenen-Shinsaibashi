#!/usr/bin/env python3
"""
generate_reel.py — v4 tempo-focused Reels generator.

第3週「比較検討②」向け Instagram Reels。
- 19.5 秒 / 13 カット / 平均 1.5 秒で切り替わるテンポ感
- 実写は主役、テキストは黒背景のスラムカードか小さなタグで演出
- Ken Burns は 1.00→1.20 程度の大きめのズームを in/out 交互に
- ASS (\\t, \\fad, \\move) で "ポン" と出るテキストアニメーション

使い方:
    python3 scripts/generate_reel.py
    python3 scripts/generate_reel.py --out output/draft.mp4
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# ---------- 設定 ----------
WIDTH = 1080
HEIGHT = 1920
FPS = 30

BLACK = "#000000"
COAL = "#0c0a09"
CREAM = "#efe6d3"
GOLD = "#c8a96a"
WHITE = "#f6f3ec"
SUB_GRAY = "#b8b0a2"

REPO_ROOT = Path(__file__).resolve().parent.parent
BRAND = "Zenen Shinsaibashi"

# ---------- Scene ----------


@dataclass
class Scene:
    kind: str                # "slam" | "photo" | "photo_tag" | "cta_wide" | "cta_text" | "bridge"
    duration: float
    text: str = ""
    sub: str = ""
    tag_num: str = ""        # "01" 等の番号タグ
    bg_hex: str = BLACK
    image: str | None = None
    video: str | None = None
    video_logo_box: tuple[int, int, int, int] | None = None
    crop_x_pct: float = 0.5  # 9:16 キャンバスの水平クロップ中心 (0.0–1.0)
    zoom_start: float = 1.00
    zoom_end: float = 1.20


SCENES: list[Scene] = [
    # 1. HOOK スラム
    Scene("slam", 0.6, text="その接待、"),

    # 2. PROBLEM スラム
    Scene("slam", 0.5, text="席、大丈夫？"),

    # 3. 陽明 ワイド
    Scene("photo_tag", 1.7, text="陽明 Youmei", tag_num="01",
          image="陽明 Youmei.JPG", crop_x_pct=0.5,
          zoom_start=1.00, zoom_end=1.18),

    # 4. 陽明 タイト (左寄せクロップ、逆ズーム)
    Scene("photo", 1.3,
          image="陽明 Youmei.JPG", crop_x_pct=0.30,
          zoom_start=1.25, zoom_end=1.10),

    # 5. 日月 ワイド
    Scene("photo_tag", 1.7, text="日月 Nichigetsu", tag_num="02",
          image=" 日月 Nichigetsu02.JPG", crop_x_pct=0.5,
          zoom_start=1.00, zoom_end=1.18),

    # 6. 日月 タイト (右寄せ)
    Scene("photo", 1.3,
          image=" 日月 Nichigetsu02.JPG", crop_x_pct=0.65,
          zoom_start=1.25, zoom_end=1.10),

    # 7. 梨山 ワイド (茶器側)
    Scene("photo_tag", 1.7, text="梨山 rizan", tag_num="03",
          image="梨山 rizan01.JPG", crop_x_pct=0.5,
          zoom_start=1.00, zoom_end=1.18),

    # 8. 梨山 タイト
    Scene("photo", 1.3,
          image="梨山 rizan01.JPG", crop_x_pct=0.35,
          zoom_start=1.22, zoom_end=1.08),

    # 9. Spec スラム 1
    Scene("slam", 0.8, text="すべて完全個室"),

    # 10. Spec スラム 2
    Scene("slam", 0.8, text="2〜10名 対応"),

    # 11. 生け花ブリッジ
    Scene("bridge", 2.0, text="細部まで、", sub="おもてなし",
          video="clideo_editor_e9c04e2420fe4c5fbf9ff8c0e9ab7f6a.mp4",
          video_logo_box=(400, 1185, 320, 85)),

    # 12. CTA ワイド
    Scene("cta_wide", 2.3, text="心斎橋 禅園",
          image="陽明 Youmei.JPG", crop_x_pct=0.5,
          zoom_start=1.05, zoom_end=1.20),

    # 13. CTA クロージング
    Scene("cta_text", 3.3,
          text="プロフィールから", sub="ご予約・詳細",
          image="陽明 Youmei.JPG", crop_x_pct=0.55,
          zoom_start=1.25, zoom_end=1.08),
]


# ---------- ユーティリティ ----------


def find_ffmpeg() -> str:
    p = shutil.which("ffmpeg")
    if p:
        return p
    try:
        import imageio_ffmpeg  # type: ignore
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit("ERROR: ffmpeg not found. Install ffmpeg or 'pip install imageio-ffmpeg'.")


def find_font() -> tuple[str, str]:
    candidates = [
        ("/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf", "IPAGothic"),
        ("/usr/share/fonts/truetype/fonts-japanese-gothic.ttf", "IPAGothic"),
        ("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc", "Noto Sans CJK JP"),
    ]
    for path, name in candidates:
        if Path(path).exists():
            return path, name
    sys.exit("ERROR: Japanese font not found. Install fonts-ipafont-gothic.")


def hex_to_ass_color(hex_rgb: str) -> str:
    h = hex_rgb.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H00{b}{g}{r}".upper()


def hex_to_ffmpeg_color(hex_rgb: str) -> str:
    return "0x" + hex_rgb.lstrip("#").upper()


def ass_ts(seconds: float) -> str:
    cs_total = int(round(seconds * 100))
    h, rem = divmod(cs_total, 360000)
    m, rem = divmod(rem, 6000)
    s, cs = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


# ---------- ASS 生成 ----------


def build_scene_ass(scene: Scene, font_name: str) -> str:
    dur = scene.duration
    start = ass_ts(0.0)
    end = ass_ts(dur)

    # スタイル定義 (name, size, color, bold, alignment, marginV)
    styles = [
        ("Slam",     200, hex_to_ass_color(WHITE),  -1, 5, 0),
        ("SlamAcc",  200, hex_to_ass_color(GOLD),   -1, 5, 0),
        ("Tag",       56, hex_to_ass_color(CREAM),  -1, 1, 180),
        ("TagNum",    38, hex_to_ass_color(GOLD),   -1, 1, 260),
        ("Brand",     32, hex_to_ass_color(CREAM),   0, 9, 120),
        ("CtaBig",   140, hex_to_ass_color(CREAM),  -1, 5, 0),
        ("CtaSub",    56, hex_to_ass_color(SUB_GRAY), 0, 5, 0),
        ("BridgeTitle", 96, hex_to_ass_color(CREAM), -1, 5, 0),
        ("BridgeSub",   70, hex_to_ass_color(GOLD),  -1, 5, 0),
        ("Overlay",    10, "&H00000000",              0, 7, 0),  # for shape drawing
    ]
    style_lines = [
        f"Style: {name},{font_name},{size},{color},&H000000FF,"
        f"&H00000000,&H64000000,{bold},0,0,0,100,100,0,0,1,0,0,"
        f"{align},40,40,{marginv},1"
        for (name, size, color, bold, align, marginv) in styles
    ]

    events: list[str] = []

    def dialogue(style: str, text: str) -> str:
        return f"Dialogue: 0,{start},{end},{style},,0,0,0,,{text}"

    def rect(color: str, alpha_hex: str, x: int, y: int, w: int, h: int) -> str:
        """半透明塗りつぶし矩形 (ASS ベクター描画)。"""
        return (
            f"Dialogue: 0,{start},{end},Overlay,,0,0,0,,"
            f"{{\\an7\\pos({x},{y})\\p4\\bord0\\shad0\\1c{color}\\1a{alpha_hex}}}"
            f"m 0 0 l {w*16} 0 l {w*16} {h*16} l 0 {h*16}"
            f"{{\\p0}}"
        )

    if scene.kind == "slam":
        # 真っ黒背景 + 巨大テキスト + ポップアップアニメーション
        # 文字数が多いほどフォントを縮める (画面幅 1080 に収めるため)
        n = len(scene.text)
        if n <= 5:
            slam_fs = 200
        elif n <= 6:
            slam_fs = 158
        elif n <= 7:
            slam_fs = 138
        else:
            slam_fs = 120
        events.append(dialogue(
            "Slam",
            r"{\an5\pos(540,960)\fs" + str(slam_fs) +
            r"\fad(40,60)\fscx85\fscy85\blur2"
            r"\t(0,150,\fscx100\fscy100\blur0)}" + scene.text
        ))
        # 細い金のアクセントラインを下に入れる
        events.append(
            f"Dialogue: 0,{start},{end},Overlay,,0,0,0,,"
            r"{\an5\pos(540,1080)\p1\bord0\shad0\1c" + hex_to_ass_color(GOLD) +
            r"\1a&H20&\fad(80,60)}m 0 0 l 120 0 l 120 3 l 0 3{\p0}"
        )

    elif scene.kind == "photo_tag":
        # 実写 + ブランド上バナー + 左下の番号タグ + ルーム名
        # 上に薄いダーク帯 (ブランド用) 100px
        events.append(rect("&H000000&", "&HA0&", 0, 0, WIDTH, 140))
        # 左下のタグ用小さい暗塊 (高さ260, 幅600)
        events.append(rect("&H000000&", "&H60&", 0, HEIGHT-310, 680, 310))
        # ブランド (上中央)
        events.append(dialogue(
            "Brand",
            r"{\fad(300,200)}" + BRAND
        ))
        # 番号タグ
        if scene.tag_num:
            events.append(dialogue(
                "TagNum",
                r"{\fad(200,200)\pos(80,1650)}" + scene.tag_num
            ))
            # タグ下の縦線
            events.append(
                f"Dialogue: 0,{start},{end},Overlay,,0,0,0,,"
                r"{\an7\pos(80,1700)\p1\bord0\shad0\1c" + hex_to_ass_color(GOLD) +
                r"\1a&H10&\fad(250,200)}m 0 0 l 60 0 l 60 3 l 0 3{\p0}"
            )
        # ルーム名 (下ワイプ風)
        events.append(dialogue(
            "Tag",
            r"{\fad(250,200)\pos(80,1750)}" + scene.text
        ))

    elif scene.kind == "photo":
        # テキストなしクリーンな実写カット
        pass

    elif scene.kind == "bridge":
        # 動画背景 + ブランド上帯 + 中央大文字 + 下暗幕
        events.append(rect("&H000000&", "&HA0&", 0, 0, WIDTH, 140))
        events.append(rect("&H000000&", "&H50&", 0, 820, WIDTH, 1100))
        events.append(dialogue(
            "Brand",
            r"{\fad(300,200)}" + BRAND
        ))
        events.append(dialogue(
            "BridgeTitle",
            r"{\an5\pos(540,1000)\fad(300,200)\fscx90\fscy90"
            r"\t(0,300,\fscx100\fscy100)}" + scene.text
        ))
        events.append(dialogue(
            "BridgeSub",
            r"{\an5\pos(540,1140)\fad(400,200)}" + scene.sub
        ))

    elif scene.kind == "cta_wide":
        # CTA 大文字。下から浮上 + フェード
        events.append(rect("&H000000&", "&H60&", 0, 700, WIDTH, 500))
        events.append(dialogue(
            "CtaBig",
            r"{\an5\move(540,1080,540,960,0,400)\fad(400,300)"
            r"\fscx92\fscy92\t(0,400,\fscx100\fscy100)}" + scene.text
        ))
        # 金線アクセント
        events.append(
            f"Dialogue: 0,{start},{end},Overlay,,0,0,0,,"
            r"{\an5\pos(540,1080)\p1\bord0\shad0\1c" + hex_to_ass_color(GOLD) +
            r"\1a&H10&\fad(500,200)}m 0 0 l 120 0 l 120 4 l 0 4{\p0}"
        )

    elif scene.kind == "cta_text":
        # 上にブランド、中央にメインテキスト + サブ、下にタップ誘導
        events.append(rect("&H000000&", "&H70&", 0, 0, WIDTH, 240))
        events.append(rect("&H000000&", "&H50&", 0, 700, WIDTH, 1220))
        events.append(dialogue(
            "Brand",
            r"{\fad(300,0)}" + BRAND
        ))
        # CtaBig style is 140 — for stacked layout shrink via tags
        events.append(dialogue(
            "CtaBig",
            r"{\an5\pos(540,900)\fad(500,0)\fscx78\fscy78}" + scene.text
        ))
        events.append(dialogue(
            "CtaSub",
            r"{\an5\pos(540,1030)\fad(700,0)}" + scene.sub
        ))
        # 下部の小さい指示テキスト
        events.append(dialogue(
            "Brand",
            r"{\an2\pos(540,1780)\fad(900,0)}" + "↑ Instagramのプロフィールへ"
        ))

    header = f"""[Script Info]
Title: Scene
ScriptType: v4.00+
PlayResX: {WIDTH}
PlayResY: {HEIGHT}
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
"""
    style_block = "\n".join(style_lines) + "\n"
    events_header = "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    events_block = "\n".join(events) + "\n"
    return header + style_block + events_header + events_block


# ---------- シーンレンダ ----------


def build_video_filter(scene: Scene, ass_path: Path) -> str:
    d_frames = max(1, int(round(scene.duration * FPS)))
    z0, z1 = scene.zoom_start, scene.zoom_end
    z_expr = f"'{z0:.4f}+({z1-z0:+.4f})*on/{d_frames}'"

    # 実写を多少だけトーン調整 (自然な色を残す)
    tone = "eq=brightness=-0.04:contrast=1.02:saturation=0.95"
    subs = f"subtitles={ass_path}:fontsdir=/usr/share/fonts"

    if scene.image:
        # 9:16 2x キャンバス (2160x3840) に可変位置でクロップ
        cover_scale = "scale=-1:3840:force_original_aspect_ratio=increase"
        # crop x = (in_w - 2160) * crop_x_pct
        canvas_crop = (
            f"crop=2160:3840:"
            f"(in_w-2160)*{scene.crop_x_pct:.3f}:(in_h-3840)/2"
        )
        kb = (
            f"zoompan=z={z_expr}"
            f":d={d_frames}"
            f":s={WIDTH}x{HEIGHT}"
            f":fps={FPS}"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        )
        return f"{cover_scale},{canvas_crop},{kb},{tone},{subs}"

    if scene.video:
        parts = []
        if scene.video_logo_box:
            x, y, w, h = scene.video_logo_box
            parts.append(f"drawbox=x={x}:y={y}:w={w}:h={h}:color=black:t=fill")
        parts += [
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase",
            f"crop={WIDTH}:{HEIGHT}",
            f"fps={FPS}",
            tone,
            subs,
        ]
        return ",".join(parts)

    return subs


def render_scene(ffmpeg: str, scene: Scene, ass_path: Path, out_path: Path) -> None:
    vf = build_video_filter(scene, ass_path)

    cmd: list[str] = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]

    if scene.image:
        img_path = REPO_ROOT / scene.image
        if not img_path.exists():
            sys.exit(f"ERROR: image not found: {img_path}")
        cmd += ["-loop", "1", "-framerate", str(FPS), "-t", f"{scene.duration}",
                "-i", str(img_path)]
    elif scene.video:
        vid_path = REPO_ROOT / scene.video
        if not vid_path.exists():
            sys.exit(f"ERROR: video not found: {vid_path}")
        cmd += ["-ss", "0", "-t", f"{scene.duration}", "-i", str(vid_path)]
    else:
        bg = hex_to_ffmpeg_color(scene.bg_hex)
        cmd += ["-f", "lavfi", "-i",
                f"color=c={bg}:s={WIDTH}x{HEIGHT}:r={FPS}:d={scene.duration}"]

    cmd += ["-f", "lavfi", "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000"]

    # ごく短いフェード (ハードカット感を残しつつ黒フレーム防止)
    fade_t = 0.08 if scene.kind != "slam" else 0.04
    fade_out_st = max(0.0, scene.duration - fade_t)
    vf_full = (
        f"{vf},"
        f"fade=t=in:st=0:d={fade_t},"
        f"fade=t=out:st={fade_out_st:.3f}:d={fade_t}"
    )

    cmd += [
        "-vf", vf_full,
        "-map", "0:v", "-map", "1:a",
        "-t", f"{scene.duration}",
        "-r", str(FPS),
        "-c:v", "libx264", "-preset", "medium", "-crf", "19",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
        "-shortest",
        "-movflags", "+faststart",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)


def concat(ffmpeg: str, files: list[Path], out: Path) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for p in files:
            f.write(f"file '{p.resolve()}'\n")
        list_path = f.name
    try:
        cmd = [
            ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", list_path,
            "-c", "copy", "-movflags", "+faststart",
            str(out),
        ]
        subprocess.run(cmd, check=True)
    finally:
        os.unlink(list_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_out = REPO_ROOT / "output" / "reel_w3_hikakukentou2.mp4"
    parser.add_argument("--out", type=Path, default=default_out)
    args = parser.parse_args()

    ffmpeg = find_ffmpeg()
    font_path, font_name = find_font()
    print(f"ffmpeg: {ffmpeg}")
    print(f"font  : {font_path} ({font_name})")
    print(f"out   : {args.out}")

    args.out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        scene_files: list[Path] = []
        running = 0.0
        for i, scene in enumerate(SCENES):
            ass_file = tmp_path / f"scene_{i:02d}.ass"
            ass_file.write_text(build_scene_ass(scene, font_name), encoding="utf-8")
            mp4 = tmp_path / f"scene_{i:02d}.mp4"
            if scene.image:
                bg = f"img:{scene.image[:28]}"
            elif scene.video:
                bg = "vid:clideo"
            else:
                bg = "blk"
            label = scene.text or scene.sub or "(clean)"
            print(f"  [{i:>2}] t={running:05.2f}s +{scene.duration:.1f}s  "
                  f"{scene.kind:10s} {bg:32s} {label}")
            render_scene(ffmpeg, scene, ass_file, mp4)
            scene_files.append(mp4)
            running += scene.duration

        print("concatenating...")
        concat(ffmpeg, scene_files, args.out)

    size = args.out.stat().st_size
    print(f"done: {args.out} ({size / 1024:.1f} KB, {running:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
