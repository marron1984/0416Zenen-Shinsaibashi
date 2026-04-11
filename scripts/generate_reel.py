#!/usr/bin/env python3
"""
generate_reel.py

第3週：比較検討② — Instagram Reels 向けプレースホルダ動画生成スクリプト.

- 出力: 1080x1920 / 30fps / H.264 yuv420p / 無音 AAC / faststart
- テキストは libass (ffmpeg の subtitles フィルタ) 経由で日本語描画
- 完成動画の素材写真を差し替えるときは SCENES の background を画像パスに変更する

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
from dataclasses import dataclass, field
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


@dataclass
class Scene:
    duration: float
    bg_hex: str
    title: str
    sub: str
    badge: str = ""
    caption: str = ""
    title_color: str = WHITE
    sub_color: str = SUB_GRAY
    badge_color: str = GOLD
    caption_color: str = GOLD


SCENES: list[Scene] = [
    Scene(3.0, COAL, "大切な接待で", "失敗したくない方へ", title_color=CREAM),
    Scene(3.0, NAVY, "席が近い。声が響く。", "落ち着いて話せない。"),
    Scene(3.0, COAL, "完全個室", "誰にも聞かれない空間", badge="01"),
    Scene(3.0, NAVY, "ゆとりある席間", "自然と距離が守られる", badge="02"),
    Scene(3.0, COAL, "静かな導線設計", "来店から退店まで気を遣わせない", badge="03"),
    Scene(3.0, NAVY, "会食・顔合わせに最適", "格式と寛ぎを両立", badge="04"),
    Scene(6.0, COAL, "大切な一席は", "心斎橋の会食処で",
          caption="Instagramで詳細を見る", title_color=CREAM),
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
    """Return (font_file_path, ass_font_name)."""
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
    """#RRGGBB -> 0xRRGGBB for ffmpeg color source."""
    return "0x" + hex_rgb.lstrip("#").upper()


def ass_ts(seconds: float) -> str:
    """seconds -> H:MM:SS.CS (centiseconds)."""
    cs_total = int(round(seconds * 100))
    h, rem = divmod(cs_total, 360000)
    m, rem = divmod(rem, 6000)
    s, cs = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def build_scene_ass(scene: Scene, font_name: str) -> str:
    """Build a standalone ASS subtitle file for a single scene."""
    dur = scene.duration
    start = ass_ts(0.0)
    end = ass_ts(dur)
    # フェードイン/アウト (ミリ秒): \fad(in_ms, out_ms)
    fade = r"{\fad(400,400)}"

    brand = BRAND

    # Styles use ASS color format.
    styles = [
        ("Brand", font_name, 44, hex_to_ass_color(CREAM), 0, 2, 80),
        ("Title", font_name, 96, hex_to_ass_color(scene.title_color), -1, 5, 0),
        ("Sub", font_name, 60, hex_to_ass_color(scene.sub_color), 0, 5, 0),
        ("Badge", font_name, 220, hex_to_ass_color(scene.badge_color), -1, 5, 0),
        ("Caption", font_name, 52, hex_to_ass_color(scene.caption_color), -1, 2, 240),
    ]

    style_lines = []
    # Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour,
    #         Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle,
    #         BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
    for name, fn, size, color, bold, align, marginv in styles:
        style_lines.append(
            f"Style: {name},{fn},{size},{color},&H000000FF,&H00000000,&H64000000,"
            f"{bold},0,0,0,100,100,0,0,1,0,0,{align},40,40,{marginv},1"
        )

    events: list[str] = []

    def add(style: str, text: str, pos: tuple[int, int] | None = None):
        pos_tag = f"{{\\pos({pos[0]},{pos[1]})}}" if pos else ""
        events.append(
            f"Dialogue: 0,{start},{end},{style},,0,0,0,,{fade}{pos_tag}{text}"
        )

    # Brand band (top)
    add("Brand", brand)

    # Badge (if any)
    if scene.badge:
        add("Badge", scene.badge, pos=(WIDTH // 2, 620))
        # divider line drawn with \p1 vector drawing
        divider = (
            f"Dialogue: 0,{start},{end},Title,,0,0,0,,"
            r"{\an5\pos(540,820)\p1\c" + hex_to_ass_color(scene.badge_color) + r"}"
            "m 0 0 l 160 0 l 160 4 l 0 4"
            r"{\p0}"
        )
        events.append(divider)

    # Title (centered, moved to upper-middle)
    title_y = 960 if not scene.badge else 940
    add("Title", scene.title, pos=(WIDTH // 2, title_y))

    # Sub
    sub_y = title_y + 150
    add("Sub", scene.sub, pos=(WIDTH // 2, sub_y))

    # Caption (CTA) bottom
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


def render_scene(
    ffmpeg: str,
    scene: Scene,
    ass_path: Path,
    out_path: Path,
    font_name: str,
) -> None:
    bg = hex_to_ffmpeg_color(scene.bg_hex)
    # fontsdir lets libass locate fonts on disk without relying on fontconfig
    vf = f"subtitles={ass_path}:fontsdir=/usr/share/fonts"
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"color=c={bg}:s={WIDTH}x{HEIGHT}:r={FPS}:d={scene.duration}",
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-vf", vf,
        "-t", f"{scene.duration}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-shortest",
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
    default_out = Path(__file__).resolve().parent.parent / "output" / "reel_w3_hikakukentou2.mp4"
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
            print(f"  scene {i}: {scene.duration:>4.1f}s  {scene.title}")
            render_scene(ffmpeg, scene, ass_file, mp4, font_name)
            scene_files.append(mp4)

        print("concatenating...")
        concat(ffmpeg, scene_files, args.out)

    size = args.out.stat().st_size
    print(f"done: {args.out} ({size / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
