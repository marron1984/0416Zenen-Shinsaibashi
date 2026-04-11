#!/usr/bin/env python3
"""
generate_reel.py

第3週：比較検討② — Instagram Reels 向け動画生成スクリプト.

- 出力: 1080x1920 / 30fps / H.264 yuv420p / 無音 AAC / faststart
- 背景は単色 or 実写画像 (Ken Burns 風ゆるやかなズーム)
- テキストは libass (ffmpeg の subtitles フィルタ) 経由で日本語描画
- 実写背景の上には下半分に黒のグラデ状オーバーレイを重ねて可読性を確保

使い方:
    python3 scripts/generate_reel.py
    python3 scripts/generate_reel.py --out output/custom.mp4
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

# 色 (#RRGGBB)
NAVY = "#0e1a2b"
COAL = "#1a1410"
GOLD = "#c8a96a"
CREAM = "#e9dfcb"
WHITE = "#f5f5f5"
SUB_GRAY = "#b8b0a2"

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Scene:
    duration: float
    title: str
    sub: str
    bg_hex: str = COAL
    image: str | None = None   # ファイル名 (REPO_ROOT 相対)
    video: str | None = None   # 実写動画クリップ (REPO_ROOT 相対)
    video_start: float = 0.0   # ソース内の開始秒
    video_logo_box: tuple[int, int, int, int] | None = None
    # ^ (x, y, w, h) ソース座標で塗りつぶす位置。透かし除去用
    badge: str = ""
    caption: str = ""
    title_color: str = WHITE
    sub_color: str = SUB_GRAY
    badge_color: str = GOLD
    caption_color: str = GOLD
    zoom_dir: str = "in"  # "in" or "out"


SCENES: list[Scene] = [
    Scene(3.0, "大切な接待で", "失敗したくない方へ",
          bg_hex=COAL, title_color=CREAM),

    Scene(3.0, "席が近い。声が響く。", "落ち着かない空間は、話も進まない。",
          bg_hex=NAVY),

    Scene(4.0, "陽明 Youmei", "畳に市松、品格の個室",
          image="陽明 Youmei.JPG",
          badge="01", caption="2〜6名 / 完全個室",
          zoom_dir="in"),

    Scene(4.0, "日月 Nichigetsu", "品のある和モダン",
          image=" 日月 Nichigetsu02.JPG",
          badge="02", caption="2〜6名 / 完全個室",
          zoom_dir="out"),

    Scene(4.0, "梨山 rizan", "茶器が彩る禅の空間",
          image="梨山 rizan01.JPG",
          badge="03", caption="7〜10名 / 完全個室",
          zoom_dir="in"),

    Scene(3.0, "すべて完全個室", "守られる席間、静かな会話",
          bg_hex=COAL, title_color=CREAM),

    # 玄関の生け花ショット (設えの細やかさを見せる)
    # 元動画 720x1280 / 2.07s / 右下にウォーターマーク
    Scene(2.0, "細部まで、おもてなし", "季節の設えで、あなたを迎える",
          video="clideo_editor_e9c04e2420fe4c5fbf9ff8c0e9ab7f6a.mp4",
          video_start=0.0,
          video_logo_box=(400, 1185, 320, 85),
          title_color=CREAM),

    Scene(6.0, "大切な一席は", "心斎橋 禅園で",
          image="陽明 Youmei.JPG",
          caption="Instagramで詳細を見る",
          title_color=CREAM, zoom_dir="out"),
]

BRAND = "Zenen Shinsaibashi"

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
    """#RRGGBB -> &H00BBGGRR (ASS primary color, opaque)."""
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
    fade = r"{\fad(400,400)}"

    # Instagram Reels のセーフエリアを意識:
    # - top ~220px はアカウント情報
    # - bottom ~400px はいいね/キャプション UI
    # テキストは 260 〜 1520 の範囲に収める
    # Brand band: y=200
    # Badge: y=520
    # Title: y=900 (no badge) / y=880 (with badge)
    # Sub: Title + 150
    # Caption: y=1440

    styles = [
        # name, size, color, bold, alignment, marginv
        ("Brand", 44, hex_to_ass_color(CREAM), 0, 2, 140),
        ("Title", 96, hex_to_ass_color(scene.title_color), -1, 5, 0),
        ("Sub", 56, hex_to_ass_color(scene.sub_color), 0, 5, 0),
        ("Badge", 200, hex_to_ass_color(scene.badge_color), -1, 5, 0),
        ("Caption", 48, hex_to_ass_color(scene.caption_color), -1, 2, 460),
        ("Overlay", 10, "&H00000000", 0, 7, 0),  # for shape drawing
    ]

    style_lines = []
    for name, size, color, bold, align, marginv in styles:
        # Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour,
        #         Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle,
        #         BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
        style_lines.append(
            f"Style: {name},{font_name},{size},{color},&H000000FF,&H00000000,&H64000000,"
            f"{bold},0,0,0,100,100,0,0,1,0,0,{align},40,40,{marginv},1"
        )

    events: list[str] = []

    def add(style: str, text: str, pos: tuple[int, int] | None = None,
            extra_tags: str = ""):
        pos_tag = f"{{\\pos({pos[0]},{pos[1]})}}" if pos else ""
        events.append(
            f"Dialogue: 0,{start},{end},{style},,0,0,0,,{fade}{extra_tags}{pos_tag}{text}"
        )

    has_media_bg = scene.image is not None or scene.video is not None

    # ----- 実写背景のときだけ、テキスト可読性のための暗幕レイヤーを敷く -----
    # 画像全体の 20% ダーケンは ffmpeg の eq フィルタ側でやっているので、
    # ここでは文字が来る領域を追加で暗く落とす。
    if has_media_bg:
        # 上の帯 (ブランド + バッジ領域) y=0〜820
        top_band = (
            f"Dialogue: 0,{start},{end},Overlay,,0,0,0,,"
            r"{\an7\pos(0,0)\p4\bord0\shad0\1c&H000000&\1a&H58&}"
            f"m 0 0 l {WIDTH*16} 0 l {WIDTH*16} {820*16} l 0 {820*16}"
            r"{\p0}"
        )
        events.append(top_band)
        # 下の帯 (タイトル〜キャプション) y=820〜1920
        bottom_band = (
            f"Dialogue: 0,{start},{end},Overlay,,0,0,0,,"
            r"{\an7\pos(0,820)\p4\bord0\shad0\1c&H000000&\1a&H38&}"
            f"m 0 0 l {WIDTH*16} 0 l {WIDTH*16} {1100*16} l 0 {1100*16}"
            r"{\p0}"
        )
        events.append(bottom_band)
        # 文字直下のさらに濃い帯 (y=870〜1540)
        text_band = (
            f"Dialogue: 0,{start},{end},Overlay,,0,0,0,,"
            r"{\an7\pos(0,870)\p4\bord0\shad0\1c&H000000&\1a&H28&}"
            f"m 0 0 l {WIDTH*16} 0 l {WIDTH*16} {670*16} l 0 {670*16}"
            r"{\p0}"
        )
        events.append(text_band)

    # ----- Brand band (top) -----
    add("Brand", BRAND, pos=(WIDTH // 2, 220))

    # ----- Badge -----
    if scene.badge:
        add("Badge", scene.badge, pos=(WIDTH // 2, 600))
        # divider line under badge
        divider = (
            f"Dialogue: 0,{start},{end},Title,,0,0,0,,"
            + fade
            + r"{\an5\pos(540,790)\p1\bord0\shad0\1c" + hex_to_ass_color(scene.badge_color) + r"\1a&H20&}"
            "m 0 0 l 160 0 l 160 4 l 0 4"
            r"{\p0}"
        )
        events.append(divider)

    # ----- Title & Sub -----
    title_y = 900 if not scene.badge else 900
    add("Title", scene.title, pos=(WIDTH // 2, title_y))
    sub_y = title_y + 140
    add("Sub", scene.sub, pos=(WIDTH // 2, sub_y))

    # ----- Caption (bottom CTA) -----
    if scene.caption:
        add("Caption", scene.caption)

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
    """Build the -vf filter chain for the scene."""
    d_frames = int(round(scene.duration * FPS))
    # Ken Burns のズーム量 (1.00 -> 1.12)
    zmax = 1.12
    if scene.zoom_dir == "in":
        z_expr = f"'1.0+{zmax-1.0:.4f}*on/{d_frames}'"
    else:  # "out": start zoomed, end at 1.0
        z_expr = f"'{zmax:.4f}-{zmax-1.0:.4f}*on/{d_frames}'"

    # 共通: テキスト可読性と落ち着いたトーンのための色調補正
    tone = "eq=brightness=-0.12:contrast=0.96:saturation=0.88"
    subs = f"subtitles={ass_path}:fontsdir=/usr/share/fonts"

    if scene.image:
        # 静止画: 2倍キャンバスにカバースケール → Ken Burns → トーン → 字幕
        cover_scale = "scale=-1:3840:force_original_aspect_ratio=increase"
        canvas_crop = "crop=2160:3840:(in_w-2160)/2:(in_h-3840)/2"
        kb = (
            f"zoompan=z={z_expr}"
            f":d={d_frames}"
            f":s={WIDTH}x{HEIGHT}"
            f":fps={FPS}"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        )
        return f"{cover_scale},{canvas_crop},{kb},{tone},{subs}"

    if scene.video:
        # 動画クリップ: 透かし塗りつぶし → 9:16 cover scale → fps 変換 → トーン → 字幕
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

    # 単色背景
    return subs


def render_scene(
    ffmpeg: str,
    scene: Scene,
    ass_path: Path,
    out_path: Path,
) -> None:
    vf = build_video_filter(scene, ass_path)

    cmd: list[str] = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
    ]

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
        # 映像だけ採用し、音声は後段で anullsrc に差し替える
        cmd += ["-ss", f"{scene.video_start}", "-t", f"{scene.duration}",
                "-i", str(vid_path)]
    else:
        bg = hex_to_ffmpeg_color(scene.bg_hex)
        cmd += ["-f", "lavfi", "-i",
                f"color=c={bg}:s={WIDTH}x{HEIGHT}:r={FPS}:d={scene.duration}"]

    cmd += ["-f", "lavfi", "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000"]

    # Fade in/out applied on top of the main vf chain for a softer cut
    fade_t = 0.4
    vf_full = (
        f"{vf},"
        f"fade=t=in:st=0:d={fade_t},"
        f"fade=t=out:st={max(0.0, scene.duration - fade_t):.3f}:d={fade_t}"
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
        # Use concat demuxer with re-encode to guarantee identical stream
        # parameters (some clips come from image loops, others from lavfi
        # color — re-encoding normalizes container metadata).
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
    parser.add_argument("--out", type=Path, default=default_out, help="output mp4 path")
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
        for i, scene in enumerate(SCENES):
            ass_file = tmp_path / f"scene_{i:02d}.ass"
            ass_file.write_text(build_scene_ass(scene, font_name), encoding="utf-8")
            mp4 = tmp_path / f"scene_{i:02d}.mp4"
            if scene.image:
                bg_label = f"img:{scene.image}"
            elif scene.video:
                bg_label = f"vid:{scene.video[:32]}"
            else:
                bg_label = f"col:{scene.bg_hex}"
            print(f"  scene {i}: {scene.duration:>4.1f}s  {bg_label:32s}  {scene.title}")
            render_scene(ffmpeg, scene, ass_file, mp4)
            scene_files.append(mp4)

        print("concatenating...")
        concat(ffmpeg, scene_files, args.out)

    size = args.out.stat().st_size
    print(f"done: {args.out} ({size / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
