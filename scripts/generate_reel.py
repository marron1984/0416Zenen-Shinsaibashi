#!/usr/bin/env python3
"""
generate_reel.py — v6 editorial Mincho Reels generator.

第3週「比較検討②」向け Instagram Reels。
高級業態向けのエディトリアル/マガジン調:

- 32 秒 / 13 カット / うち 8 カットが実写 (写真優位)
- 明朝体 (IPAexMincho) でエレガントなセリフ表現
- 全体的に小さめのフォント、余白重視の editorial レイアウト
- 各個室ごとにワイド→タイト/別アングルの複数カットで見せる
- 店舗情報はスタッガード・フェードで順次表示

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

# BGM (リポジトリ直下に配置)。見つからなければ無音のまま
BGM_FILE = "Silver_Water_Under_Stone.mp3"
BGM_VOLUME = 0.55       # 0.0–1.0 (マスター音量)
BGM_FADE_IN_SEC = 2.0
BGM_FADE_OUT_SEC = 2.2

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
    kind: str                # "photo_tag" | "photo_text" | "photo_brand" |
                             # "photo_info" | "photo_cta"
    duration: float
    text: str = ""
    sub: str = ""
    bg_hex: str = BLACK  # (unused in v7 — 全シーン写真背景)
    image: str | None = None
    video: str | None = None  # (legacy, 未使用)
    video_logo_box: tuple[int, int, int, int] | None = None
    crop_x_pct: float = 0.5
    zoom_start: float = 1.00
    zoom_end: float = 1.08
    # 写真背景のダーケン量 (0.0–0.5) と gblur シグマ
    # テキストを重ねる時に写真を沈めて可読性を確保する
    bg_darken: float = 0.0
    bg_blur: int = 0


SCENES: list[Scene] = [
    # 1. 陽明 + タグ
    Scene("photo_tag", 4.5, text="陽明  Youmei", sub="2〜6名様",
          image="陽明 Youmei.JPG", crop_x_pct=0.5,
          zoom_start=1.00, zoom_end=1.06),

    # 2. 日月 + タグ
    Scene("photo_tag", 4.5, text="日月  Nichigetsu", sub="2〜6名様",
          image=" 日月 Nichigetsu01 .JPG", crop_x_pct=0.5,
          zoom_start=1.00, zoom_end=1.06),

    # 3. 梨山 + タグ (茶器)
    Scene("photo_tag", 4.5, text="梨山  rizan", sub="7〜10名様",
          image="梨山 rizan01.JPG", crop_x_pct=0.45,
          zoom_start=1.00, zoom_end=1.06),

    # 4. 写真の上にテキスト「すべて、完全個室。」
    Scene("photo_text", 3.5, text="すべて、完全個室。",
          image=" 日月 Nichigetsu02.JPG", crop_x_pct=0.5,
          zoom_start=1.06, zoom_end=1.00,
          bg_darken=0.22, bg_blur=5),

    # 5. 写真の上にブランド「心斎橋 禅園 / Shinsaibashi Zenen」
    Scene("photo_brand", 3.5, text="心斎橋　禅園", sub="Shinsaibashi Zenen",
          image="梨山 rizan02.JPG", crop_x_pct=0.5,
          zoom_start=1.04, zoom_end=1.00,
          bg_darken=0.24, bg_blur=5),

    # 6. 写真の上に店舗情報カード
    Scene("photo_info", 7.0,
          image=" 日月 Nichigetsu03 .JPG", crop_x_pct=0.5,
          zoom_start=1.00, zoom_end=1.03,
          bg_darken=0.38, bg_blur=12),

    # 7. 写真の上に CTA「詳しくは、プロフィールへ。」
    Scene("photo_cta", 3.0, text="詳しくは、プロフィールへ。",
          image="梨山 rizan03.JPG", crop_x_pct=0.5,
          zoom_start=1.04, zoom_end=1.00,
          bg_darken=0.24, bg_blur=5),
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
    """明朝体を優先して検出する。"""
    candidates = [
        ("/usr/share/fonts/opentype/ipaexfont-mincho/ipaexm.ttf", "IPAexMincho"),
        ("/usr/share/fonts/opentype/ipafont-mincho/ipam.ttf", "IPAMincho"),
        ("/usr/share/fonts/truetype/fonts-japanese-mincho.ttf", "IPAexMincho"),
        ("/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf", "IPAGothic"),
        ("/usr/share/fonts/truetype/fonts-japanese-gothic.ttf", "IPAGothic"),
    ]
    for path, name in candidates:
        if Path(path).exists():
            return path, name
    sys.exit("ERROR: Japanese font not found. Install fonts-ipaexfont-mincho.")


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

    # スタイル定義 (name, size, color, bold, alignment, marginV, outline)
    # 洗練されたエディトリアル感を出すために全体的に小さめのサイズに。
    styles = [
        ("TextBlack",    62, hex_to_ass_color(CREAM),    0, 5,   0, 0),
        ("Tag",          38, hex_to_ass_color(CREAM),    0, 7,   0, 2),
        ("TagSub",       26, hex_to_ass_color(GOLD),     0, 7,   0, 2),
        ("Brand",        22, hex_to_ass_color(CREAM),    0, 8, 120, 2),
        ("BrandBig",     84, hex_to_ass_color(CREAM),    0, 5,   0, 0),
        ("BrandEn",      28, hex_to_ass_color(GOLD),     0, 5,   0, 0),
        ("BridgeText",   48, hex_to_ass_color(CREAM),    0, 5,   0, 2),
        ("InfoName",     58, hex_to_ass_color(CREAM),    0, 5,   0, 0),
        ("InfoEn",       24, hex_to_ass_color(GOLD),     0, 5,   0, 0),
        ("InfoAddr",     30, hex_to_ass_color(WHITE),    0, 5,   0, 0),
        ("InfoTel",      38, hex_to_ass_color(CREAM),    0, 5,   0, 0),
        ("InfoHours",    30, hex_to_ass_color(WHITE),    0, 5,   0, 0),
        ("InfoClosed",   26, hex_to_ass_color(SUB_GRAY), 0, 5,   0, 0),
        ("InfoHint",     26, hex_to_ass_color(CREAM),    0, 2, 120, 0),
        ("Cta",          58, hex_to_ass_color(CREAM),    0, 5,   0, 0),
        ("Overlay",      10, "&H00000000",               0, 7,   0, 0),
    ]
    style_lines = [
        f"Style: {name},{font_name},{size},{color},&H000000FF,"
        f"&H00000000,&H64000000,{bold},0,0,0,100,100,0,0,1,{outline},0,"
        f"{align},40,40,{marginv},1"
        for (name, size, color, bold, align, marginv, outline) in styles
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

    if scene.kind == "photo_tag":
        # エディトリアル風: 明朝の小さめテキストを左下に添える
        events.append(rect("&HA8&", 0, HEIGHT - 160, WIDTH, 160))
        events.append(dialogue(
            "Brand",
            r"{\fad(1100,600)\fsp4}" + BRAND
        ))
        # 左下 - 縦の細い金線
        events.append(
            f"Dialogue: 0,{start},{end},Overlay,,0,0,0,,"
            r"{\an7\pos(80,1780)\p1\bord0\shad0\1c" + hex_to_ass_color(GOLD) +
            r"\1a&H10&\fad(900,600)}m 0 0 l 2 0 l 2 80 l 0 80{\p0}"
        )
        events.append(dialogue(
            "Tag",
            r"{\fad(900,600)\pos(110,1788)\fsp2}" + scene.text
        ))
        events.append(dialogue(
            "TagSub",
            r"{\fad(1100,600)\pos(110,1838)\fsp4}" + scene.sub
        ))

    elif scene.kind == "photo_text":
        # 暗くぼかした写真の上に中央のテキスト
        fs = auto_slam_fs(scene.text, base=68)
        events.append(
            f"Dialogue: 0,{start},{end},Overlay,,0,0,0,,"
            r"{\an5\pos(540,900)\p1\bord0\shad0\1c" + hex_to_ass_color(GOLD) +
            r"\1a&H20&\fad(700,500)}m 0 0 l 80 0 l 80 2 l 0 2{\p0}"
        )
        events.append(dialogue(
            "TextBlack",
            r"{\an5\pos(540,990)\fs" + str(fs) +
            r"\fsp6\fad(900,600)}" + scene.text
        ))

    elif scene.kind == "photo_brand":
        # 暗くぼかした写真の上にブランド店名 + 英語
        events.append(dialogue(
            "BrandBig",
            r"{\an5\pos(540,910)\fsp10\fad(900,600)}" + scene.text
        ))
        events.append(
            f"Dialogue: 0,{start},{end},Overlay,,0,0,0,,"
            r"{\an5\pos(540,980)\p1\bord0\shad0\1c" + hex_to_ass_color(GOLD) +
            r"\1a&H20&\fad(1100,600)}m 0 0 l 90 0 l 90 2 l 0 2{\p0}"
        )
        events.append(dialogue(
            "BrandEn",
            r"{\an5\pos(540,1020)\fsp6\fad(1200,500)}" + scene.sub
        ))

    elif scene.kind == "photo_info":
        # 暗くぼかした写真の上に店舗情報をスタッガード・フェードで
        fade_out_start_ms = end_ms - 500
        lines = [
            ("InfoName",   580, STORE_INFO["name_jp"], 200,  8),
            ("InfoEn",     680, STORE_INFO["name_en"], 400,  6),
            ("InfoAddr",   830, STORE_INFO["postal"],  700,  2),
            ("InfoAddr",   880, STORE_INFO["addr1"],   800,  2),
            ("InfoAddr",   930, STORE_INFO["addr2"],   900,  2),
            ("InfoTel",   1050, STORE_INFO["tel"],    1150,  4),
            ("InfoHours", 1180, STORE_INFO["lunch"],  1400,  2),
            ("InfoHours", 1225, STORE_INFO["dinner"], 1500,  2),
            ("InfoClosed",1340, STORE_INFO["closed"], 1700,  2),
        ]
        for style_name, y, text, delay, fsp in lines:
            events.append(dialogue(
                style_name,
                f"{{\\an5\\pos(540,{y})\\fsp{fsp}"
                + stagger_fade(delay, rise_ms=600,
                               hold_to_ms=fade_out_start_ms,
                               fade_out_ms=500)
                + "}" + text
            ))
        events.append(
            f"Dialogue: 0,{start},{end},Overlay,,0,0,0,,"
            r"{\an5\pos(540,735)\p1\bord0\shad0\1c" + hex_to_ass_color(GOLD) +
            r"\1a&H20&" + stagger_fade(500, rise_ms=600,
                                       hold_to_ms=fade_out_start_ms,
                                       fade_out_ms=500) + r"}"
            "m 0 0 l 80 0 l 80 2 l 0 2{\\p0}"
        )
        events.append(dialogue(
            "InfoHint",
            r"{\fsp4" + stagger_fade(2000, rise_ms=800,
                                     hold_to_ms=fade_out_start_ms,
                                     fade_out_ms=500) + r"}" + STORE_INFO["cta_hint"]
        ))

    elif scene.kind == "photo_cta":
        # 暗くぼかした写真の上に CTA テキスト + ブランド
        fs = auto_slam_fs(scene.text, base=58)
        events.append(dialogue(
            "Cta",
            r"{\an5\pos(540,920)\fs" + str(fs) +
            r"\fsp6\fad(900,500)}" + scene.text
        ))
        events.append(
            f"Dialogue: 0,{start},{end},Overlay,,0,0,0,,"
            r"{\an5\pos(540,990)\p1\bord0\shad0\1c" + hex_to_ass_color(GOLD) +
            r"\1a&H20&\fad(1100,500)}m 0 0 l 90 0 l 90 2 l 0 2{\p0}"
        )
        events.append(dialogue(
            "Brand",
            r"{\an5\pos(540,1040)\fsp4\fad(1300,500)}" + BRAND
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

    # テキスト重ねシーンで写真を沈めて可読性を担保
    brightness = -0.03 - scene.bg_darken
    saturation = max(0.4, 0.94 - scene.bg_darken * 0.8)
    tone = (
        f"eq=brightness={brightness:.3f}:"
        f"contrast=1.02:saturation={saturation:.3f}"
    )
    blur = f",gblur=sigma={scene.bg_blur}" if scene.bg_blur > 0 else ""
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
        return f"{cover_scale},{canvas_crop},{kb},{tone}{blur},{subs}"

    # フォールバック: 単色背景 (v7 では使用されない)
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
    else:
        # v7 では到達しない想定だが保険で単色背景
        bg = hex_to_ffmpeg_color(scene.bg_hex)
        cmd += ["-f", "lavfi", "-i",
                f"color=c={bg}:s={WIDTH}x{HEIGHT}:r={FPS}:d={scene.duration}"]

    cmd += ["-f", "lavfi", "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000"]

    # 長めのフェードで繋ぎをなめらかに (ゆったりとした展開)
    fade_t = 0.50
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


def mux_bgm(ffmpeg: str, src_video: Path, bgm: Path, out: Path,
            total_duration: float) -> None:
    """src_video の映像に bgm をミックスして out に書き出す。

    - 動画側の無音トラックは捨てて BGM だけを使う
    - BGM が動画より短い場合は 1 度だけ再生して自然に終わらせる
    - BGM 冒頭と末尾でフェード
    """
    # 動画より BGM が短い場合、BGM 再生後は無音で動画尺まで埋める
    # (ループは loop point で音が飛ぶので使わない)
    bgm_dur = get_audio_duration(ffmpeg, bgm)
    play_end = min(total_duration, bgm_dur)
    fade_out_start = max(0.0, play_end - BGM_FADE_OUT_SEC)
    af = (
        f"volume={BGM_VOLUME},"
        f"afade=t=in:st=0:d={BGM_FADE_IN_SEC},"
        f"afade=t=out:st={fade_out_start:.3f}:d={BGM_FADE_OUT_SEC},"
        f"apad=whole_dur={total_duration:.3f}"
    )
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(src_video),
        "-i", str(bgm),
        "-filter_complex", f"[1:a]{af}[a]",
        "-map", "0:v:0", "-map", "[a]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-t", f"{total_duration:.3f}",
        "-movflags", "+faststart",
        str(out),
    ]
    subprocess.run(cmd, check=True)


def get_audio_duration(ffmpeg: str, path: Path) -> float:
    """ffmpeg で音声の尺を秒で取得。"""
    r = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(path)],
        capture_output=True, text=True,
    )
    import re
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", r.stderr)
    if not m:
        return 0.0
    h, mm, ss = m.groups()
    return int(h) * 3600 + int(mm) * 60 + float(ss)


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
        silent_out = tmp_path / "silent.mp4"
        concat(ffmpeg, scene_files, silent_out)

        bgm_path = REPO_ROOT / BGM_FILE
        if bgm_path.exists():
            print(f"muxing BGM: {BGM_FILE}")
            mux_bgm(ffmpeg, silent_out, bgm_path, args.out, running)
        else:
            print(f"no BGM found at {bgm_path}, leaving silent")
            shutil.copy(silent_out, args.out)

    size = args.out.stat().st_size
    print(f"done: {args.out} ({size / 1024:.1f} KB, {running:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
