#!/usr/bin/env python3
"""
generate_reel.py — v5 high-end, slow, cinematic Reels generator.

第3週「比較検討②」向け Instagram Reels。
高級業態向けの落ち着いたトーンを重視:

- 31 秒 / 9 カット / 平均 3.4 秒の余白のあるペース
- Ken Burns は 1.00–1.10 のごく控えめなズーム
- テキストは断定調・短文で静かに立ち上げる (ポップアップなし)
- 実店舗情報をスタッガード・フェードで表示するインフォカード
- クロスフェード風の長め (0.35s) フェードで繋ぎをまろやかに

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
from dataclasses import dataclass, field
from pathlib import Path

# ---------- 設定 ----------
WIDTH = 1080
HEIGHT = 1920
FPS = 30

BLACK = "#000000"
CREAM = "#e9ddc4"
GOLD = "#c8a36a"
WHITE = "#f4efe3"
SUB_GRAY = "#a8a090"

REPO_ROOT = Path(__file__).resolve().parent.parent
BRAND = "Shinsaibashi  Zenen"

# 店舗情報 (info_card シーンで表示)
STORE_INFO = {
    "name_jp":   "心斎橋　禅園",
    "name_en":   "Shinsaibashi Zenen",
    "postal":    "〒542-0086",
    "addr1":     "大阪市中央区西心斎橋 1-3-3",
    "addr2":     "オー・エム・ホテル日航ビル B2F",
    "tel":       "TEL  06-6241-7027",
    "lunch":     "LUNCH    11:30 – 14:45   (L.O. 14:00)",
    "dinner":    "DINNER  17:00 – 22:00   (L.O. 21:00)",
    "closed":    "定休日    不定休 (施設に準ずる)",
    "cta_hint":  "詳しくは、プロフィールへ",
}

# ---------- Scene ----------


@dataclass
class Scene:
    kind: str                # "photo_intro" | "text_black" | "photo_tag" | "bridge" |
                             # "brand_reveal" | "info_card" | "cta_final"
    duration: float
    text: str = ""
    sub: str = ""
    bg_hex: str = BLACK
    image: str | None = None
    video: str | None = None
    video_logo_box: tuple[int, int, int, int] | None = None
    crop_x_pct: float = 0.5
    zoom_start: float = 1.00
    zoom_end: float = 1.08


SCENES: list[Scene] = [
    # 1. オープニング (陽明 — ゆるやかに引き、途中でテキストが立ち上がる)
    Scene("photo_intro", 3.0, text="大切な、ひと席を。",
          image="陽明 Youmei.JPG", crop_x_pct=0.5,
          zoom_start=1.10, zoom_end=1.00),

    # 2. 黒背景 テキストカード
    Scene("text_black", 2.5, text="すべて、完全個室。"),

    # 3. 陽明 (中央クロップ / ゆっくりズームイン)
    Scene("photo_tag", 4.0, text="陽明   Youmei", sub="2〜6名様",
          image="陽明 Youmei.JPG", crop_x_pct=0.5,
          zoom_start=1.00, zoom_end=1.08),

    # 4. 日月 (中央クロップ / ゆっくりズームアウト)
    Scene("photo_tag", 4.0, text="日月   Nichigetsu", sub="2〜6名様",
          image=" 日月 Nichigetsu02.JPG", crop_x_pct=0.5,
          zoom_start=1.08, zoom_end=1.00),

    # 5. 梨山 (やや左寄せで茶器側を入れる)
    Scene("photo_tag", 4.0, text="梨山   rizan", sub="7〜10名様",
          image="梨山 rizan01.JPG", crop_x_pct=0.45,
          zoom_start=1.00, zoom_end=1.08),

    # 6. 生け花 ブリッジ (季節の設え)
    Scene("bridge", 2.0, text="細やかな、おもてなし。",
          video="clideo_editor_e9c04e2420fe4c5fbf9ff8c0e9ab7f6a.mp4",
          video_logo_box=(400, 1185, 320, 85)),

    # 7. ブランド露出 (黒背景)
    Scene("brand_reveal", 3.0, text="心斎橋　禅園", sub="Shinsaibashi Zenen"),

    # 8. インフォカード (住所・電話・営業時間)
    Scene("info_card", 5.5),

    # 9. CTA (プロフィール誘導)
    Scene("cta_final", 3.0, text="詳しくは、プロフィールへ。"),
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


def auto_slam_fs(text: str, base: int = 120) -> int:
    """文字数に応じて 1080px 幅に収まる上限 fs を返す。"""
    n = max(1, len(text))
    # IPAGothic の全角は 1em ≈ 0.95 * fs 幅 と見なして余白込み
    max_fs = int(1080 * 0.90 / (n * 0.95))
    return min(base, max_fs)


# ---------- ASS 生成 ----------


def build_scene_ass(scene: Scene, font_name: str) -> str:
    dur = scene.duration
    start = ass_ts(0.0)
    end = ass_ts(dur)
    end_ms = int(round(dur * 1000))

    # スタイル定義 (name, size, color, bold, alignment, marginV)
    styles = [
        ("TextBlack",   140, hex_to_ass_color(CREAM),   0, 5, 0),
        ("Intro",        88, hex_to_ass_color(CREAM),  -1, 2, 320),
        ("Tag",          54, hex_to_ass_color(CREAM),  -1, 1, 200),
        ("TagSub",       38, hex_to_ass_color(GOLD),    0, 1, 140),
        ("Brand",        30, hex_to_ass_color(CREAM),   0, 8, 160),
        ("BrandBig",    160, hex_to_ass_color(CREAM),  -1, 5, 0),
        ("BrandEn",      46, hex_to_ass_color(GOLD),    0, 5, 0),
        ("BridgeText",   84, hex_to_ass_color(CREAM),  -1, 5, 0),
        ("InfoName",    100, hex_to_ass_color(CREAM),  -1, 5, 0),
        ("InfoEn",       36, hex_to_ass_color(GOLD),    0, 5, 0),
        ("InfoAddr",     42, hex_to_ass_color(WHITE),   0, 5, 0),
        ("InfoTel",      54, hex_to_ass_color(CREAM),  -1, 5, 0),
        ("InfoHours",    42, hex_to_ass_color(WHITE),   0, 5, 0),
        ("InfoClosed",   36, hex_to_ass_color(SUB_GRAY),0, 5, 0),
        ("InfoHint",     34, hex_to_ass_color(CREAM),   0, 2, 120),
        ("Cta",         100, hex_to_ass_color(CREAM),  -1, 5, 0),
        ("Overlay",      10, "&H00000000",              0, 7, 0),
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

    def rect(alpha_hex: str, x: int, y: int, w: int, h: int) -> str:
        return (
            f"Dialogue: 0,{start},{end},Overlay,,0,0,0,,"
            f"{{\\an7\\pos({x},{y})\\p4\\bord0\\shad0\\1c&H000000&\\1a{alpha_hex}}}"
            f"m 0 0 l {w*16} 0 l {w*16} {h*16} l 0 {h*16}"
            f"{{\\p0}}"
        )

    def hline(color: str, alpha_hex: str, x: int, y: int, w: int, h: int = 3) -> str:
        return (
            f"Dialogue: 0,{start},{end},Overlay,,0,0,0,,"
            f"{{\\an7\\pos({x},{y})\\p1\\bord0\\shad0\\1c{color}\\1a{alpha_hex}}}"
            f"m 0 0 l {w} 0 l {w} {h} l 0 {h}"
            f"{{\\p0}}"
        )

    def stagger_fade(delay_ms: int, rise_ms: int = 700,
                     hold_to_ms: int | None = None,
                     fade_out_ms: int = 400) -> str:
        """\\fade() で遅れ付きフェードインを作る。"""
        t1 = delay_ms
        t2 = delay_ms + rise_ms
        t3 = (hold_to_ms if hold_to_ms is not None
              else max(t2 + 400, end_ms - fade_out_ms))
        t4 = end_ms
        return f"\\fade(255,0,0,{t1},{t2},{t3},{t4})"

    # ---------- kind 別のイベント生成 ----------

    if scene.kind == "text_black":
        fs = auto_slam_fs(scene.text, base=140)
        events.append(dialogue(
            "TextBlack",
            r"{\an5\pos(540,960)\fs" + str(fs) +
            r"\fad(800,600)}" + scene.text
        ))
        # 金の細い水平線 (下に少し離して置く)
        events.append(
            f"Dialogue: 0,{start},{end},Overlay,,0,0,0,,"
            r"{\an5\pos(540,1100)\p1\bord0\shad0\1c" + hex_to_ass_color(GOLD) +
            r"\1a&H30&\fad(900,500)}m 0 0 l 150 0 l 150 3 l 0 3{\p0}"
        )

    elif scene.kind == "photo_intro":
        # 陽明のワイドに、1秒後からテキストがそっと立ち上がる
        # 上部のブランドも遅れて入る
        events.append(dialogue(
            "Brand",
            r"{" + stagger_fade(600, rise_ms=900) + r"}" + BRAND
        ))
        # 中央テキスト
        events.append(dialogue(
            "Intro",
            r"{\an2\pos(540,1600)" + stagger_fade(1000, rise_ms=1000) +
            r"}" + scene.text
        ))
        # 下部金線
        events.append(
            f"Dialogue: 0,{start},{end},Overlay,,0,0,0,,"
            r"{\an2\pos(540,1660)\p1\bord0\shad0\1c" + hex_to_ass_color(GOLD) +
            r"\1a&H30&" + stagger_fade(1200, rise_ms=900) + r"}"
            "m 0 0 l 180 0 l 180 3 l 0 3{\\p0}"
        )

    elif scene.kind == "photo_tag":
        # 実写 + 左下に控えめなタグ (番号なし)
        # 下部に半透明の薄い暗幕 (高さ 260)
        events.append(rect("&H90&", 0, HEIGHT - 280, WIDTH, 280))
        # ブランド (右上、小さく)
        events.append(dialogue(
            "Brand",
            r"{\fad(900,600)}" + BRAND
        ))
        # 左の縦細金線 (装飾)
        events.append(
            f"Dialogue: 0,{start},{end},Overlay,,0,0,0,,"
            r"{\an7\pos(80,1700)\p1\bord0\shad0\1c" + hex_to_ass_color(GOLD) +
            r"\1a&H20&\fad(900,600)}m 0 0 l 3 0 l 3 120 l 0 120{\p0}"
        )
        # ルーム名 (縦線の右)
        events.append(dialogue(
            "Tag",
            r"{\fad(900,600)\pos(130,1715)}" + scene.text
        ))
        # キャパシティ
        events.append(dialogue(
            "TagSub",
            r"{\fad(1100,600)\pos(130,1795)}" + scene.sub
        ))

    elif scene.kind == "bridge":
        # 生け花動画 + 下帯暗幕 + 中央テキスト
        # clideo.com 透かしは drawbox で黒塗りしているが、
        # 半透明のオーバーレイだと境目が見えてしまうので、
        # 下 500px は完全不透明の黒で覆って透かしと同化させる
        events.append(rect("&H00&", 0, HEIGHT - 500, WIDTH, 500))
        events.append(dialogue(
            "BridgeText",
            r"{\an5\pos(540,1650)\fad(700,500)}" + scene.text
        ))

    elif scene.kind == "brand_reveal":
        # 大きなブランド名 (JP) + 英語 + 下の金線
        events.append(dialogue(
            "BrandBig",
            r"{\an5\pos(540,900)\fad(900,600)}" + scene.text
        ))
        events.append(
            f"Dialogue: 0,{start},{end},Overlay,,0,0,0,,"
            r"{\an5\pos(540,1020)\p1\bord0\shad0\1c" + hex_to_ass_color(GOLD) +
            r"\1a&H20&\fad(1100,600)}m 0 0 l 140 0 l 140 3 l 0 3{\p0}"
        )
        events.append(dialogue(
            "BrandEn",
            r"{\an5\pos(540,1080)\fad(1200,500)}" + scene.sub
        ))

    elif scene.kind == "info_card":
        # 店舗情報。スタッガード・フェードで順番に立ち上げる
        fade_out_end_ms = end_ms
        fade_out_start_ms = end_ms - 500
        lines = [
            # (style, y, text, delay_ms)
            ("InfoName",   460, STORE_INFO["name_jp"],  200),
            ("InfoEn",     580, STORE_INFO["name_en"],  400),
            ("InfoAddr",   760, STORE_INFO["postal"],   700),
            ("InfoAddr",   820, STORE_INFO["addr1"],    800),
            ("InfoAddr",   880, STORE_INFO["addr2"],    900),
            ("InfoTel",   1020, STORE_INFO["tel"],     1150),
            ("InfoHours", 1170, STORE_INFO["lunch"],   1400),
            ("InfoHours", 1230, STORE_INFO["dinner"],  1500),
            ("InfoClosed",1370, STORE_INFO["closed"],  1700),
        ]
        for style_name, y, text, delay in lines:
            events.append(dialogue(
                style_name,
                f"{{\\an5\\pos(540,{y})"
                + stagger_fade(delay, rise_ms=600,
                               hold_to_ms=fade_out_start_ms,
                               fade_out_ms=500)
                + "}" + text
            ))
        # 店名下の金線
        events.append(
            f"Dialogue: 0,{start},{end},Overlay,,0,0,0,,"
            r"{\an5\pos(540,660)\p1\bord0\shad0\1c" + hex_to_ass_color(GOLD) +
            r"\1a&H30&" + stagger_fade(500, rise_ms=600,
                                       hold_to_ms=fade_out_start_ms,
                                       fade_out_ms=500) + r"}"
            "m 0 0 l 120 0 l 120 3 l 0 3{\\p0}"
        )
        # 下部誘導
        events.append(dialogue(
            "InfoHint",
            r"{" + stagger_fade(2000, rise_ms=800,
                                hold_to_ms=fade_out_start_ms,
                                fade_out_ms=500) + r"}" + STORE_INFO["cta_hint"]
        ))

    elif scene.kind == "cta_final":
        fs = auto_slam_fs(scene.text, base=88)
        events.append(dialogue(
            "Cta",
            r"{\an5\pos(540,880)\fs" + str(fs) +
            r"\fad(900,500)}" + scene.text
        ))
        # 装飾金線
        events.append(
            f"Dialogue: 0,{start},{end},Overlay,,0,0,0,,"
            r"{\an5\pos(540,980)\p1\bord0\shad0\1c" + hex_to_ass_color(GOLD) +
            r"\1a&H20&\fad(1100,500)}m 0 0 l 150 0 l 150 3 l 0 3{\p0}"
        )
        # ブランドを下に小さく
        events.append(dialogue(
            "Brand",
            r"{\an5\pos(540,1060)\fad(1300,500)}" + BRAND
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

    # 自然な色を残しつつ、ほんの少しだけトーンを沈める
    tone = "eq=brightness=-0.03:contrast=1.02:saturation=0.94"
    subs = f"subtitles={ass_path}:fontsdir=/usr/share/fonts"

    if scene.image:
        cover_scale = "scale=-1:3840:force_original_aspect_ratio=increase"
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

    # 長めのフェードで繋ぎをなめらかに
    fade_t = 0.35
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
            label = scene.text or scene.sub or ("[info]" if scene.kind == "info_card" else "")
            print(f"  [{i:>2}] t={running:05.2f}s +{scene.duration:.1f}s  "
                  f"{scene.kind:13s} {bg:32s} {label}")
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
