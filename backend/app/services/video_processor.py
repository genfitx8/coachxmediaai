"""Video processing utilities using ffmpeg directly.

This module replaces the previous moviepy-based implementation. moviepy holds
clips in memory which routinely pushes a side-by-side render past the Render
free plan's 512 MB RAM ceiling. Calling ffmpeg's ``filter_complex`` directly
streams frames between filters and keeps peak memory under ~200 MB for short
HD clips, which is what the synchronous Phase 1 endpoint targets.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

# Font shipped by the ``fonts-dejavu-core`` apt package installed in the
# backend Dockerfile. drawtext requires an absolute path on Linux.
_DEJAVU_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

TARGET_HEIGHT = 480
LABEL_HEIGHT = 40
BEFORE_BG = "0x2D6A2D"  # dark green
AFTER_BG = "0x1E508C"  # dark blue


def _ffmpeg_bin() -> str:
    return shutil.which("ffmpeg") or "ffmpeg"


def _ffprobe_bin() -> str:
    return shutil.which("ffprobe") or "ffprobe"


def _probe_duration(path: str | Path) -> float:
    result = subprocess.run(
        [
            _ffprobe_bin(),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr.strip() or 'unknown error'}")
    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError(
            f"ffprobe returned non-numeric duration: {result.stdout!r}"
        ) from exc


def _label_filter(text: str, bg_color: str) -> str:
    """Build the per-side filter chain: scale → pad → drawtext."""
    font_clause = f":fontfile={_DEJAVU_BOLD}" if Path(_DEJAVU_BOLD).exists() else ""
    return (
        f"scale=-2:{TARGET_HEIGHT},"
        f"pad=iw:ih+{LABEL_HEIGHT}:0:{LABEL_HEIGHT}:color={bg_color},"
        f"drawtext=text='{text}':fontcolor=white:fontsize=22"
        f":x=(w-text_w)/2:y=({LABEL_HEIGHT}-text_h)/2{font_clause}"
    )


def create_comparison_video(
    before_path: str | Path,
    after_path: str | Path,
    output_path: str | Path,
) -> None:
    """Render a side-by-side before/after MP4 using ffmpeg.

    Both inputs are trimmed to the shorter clip's duration, scaled to a
    common height, padded with a coloured label bar (green ``Before`` on the
    left, blue ``After`` on the right), then horizontally stacked.
    """
    duration = min(_probe_duration(before_path), _probe_duration(after_path))
    if duration <= 0:
        raise RuntimeError("Input clip has zero or unknown duration.")

    filter_complex = (
        f"[0:v]trim=0:{duration},setpts=PTS-STARTPTS,"
        f"{_label_filter('Before', BEFORE_BG)}[left];"
        f"[1:v]trim=0:{duration},setpts=PTS-STARTPTS,"
        f"{_label_filter('After', AFTER_BG)}[right];"
        f"[left][right]hstack=inputs=2[v]"
    )

    cmd = [
        _ffmpeg_bin(),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(before_path),
        "-i",
        str(after_path),
        "-filter_complex",
        filter_complex,
        "-map",
        "[v]",
        "-map",
        "0:a?",  # take audio from the "before" clip if present
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        "-movflags",
        "+faststart",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
    if result.returncode != 0:
        # ffmpeg writes useful diagnostics to stderr even at loglevel=error.
        raise RuntimeError(
            f"ffmpeg exited with code {result.returncode}: "
            f"{result.stderr.strip() or 'no stderr output'}"
        )


# Speed factors we expose to the UI. Values < 1 slow the video down, > 1
# speed it up. ffmpeg's setpts uses 1/speed: setpts=PTS*2 = 0.5x playback.
ALLOWED_SLOW_MOTION_SPEEDS = (0.5, 0.25, 0.125)


def _atempo_chain(speed: float) -> str:
    """Build an atempo filter chain that matches ``speed`` (audio playback rate).

    A single atempo filter only accepts factors in [0.5, 2.0]; chain copies
    of 0.5 (or 2.0) until the residual factor falls inside that range.
    """
    if speed <= 0:
        raise ValueError("speed must be > 0")
    if speed == 1.0:
        return "atempo=1.0"
    parts: list[str] = []
    remaining = speed
    while remaining < 0.5:
        parts.append("atempo=0.5")
        remaining /= 0.5  # divide by 0.5 == multiply by 2
    while remaining > 2.0:
        parts.append("atempo=2.0")
        remaining /= 2.0
    parts.append(f"atempo={remaining:.6f}")
    return ",".join(parts)


def create_slow_motion_video(
    input_path: str | Path,
    output_path: str | Path,
    speed: float,
) -> None:
    """Re-time ``input_path`` to ``speed`` and write to ``output_path``.

    ``speed`` is the playback rate: 0.5 = half speed (slow motion), 2.0 = 2×.
    Audio is re-timed in pitch-preserving fashion via the ``atempo`` filter.
    """
    if speed <= 0:
        raise ValueError("speed must be > 0")
    pts_factor = 1.0 / speed  # setpts multiplies PTS by this factor

    video_filter = f"setpts={pts_factor:.6f}*PTS"
    audio_filter = _atempo_chain(speed)

    cmd = [
        _ffmpeg_bin(),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(input_path),
        "-filter_complex",
        f"[0:v]{video_filter}[v];[0:a]{audio_filter}[a]",
        "-map",
        "[v]",
        "-map",
        "[a]?",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
    if result.returncode != 0:
        # If the source has no audio, the audio filter half of the graph
        # fails — retry without audio so the video pipeline still wins.
        if "Stream specifier" in (result.stderr or "") or "no such filter" in (
            result.stderr or ""
        ):
            video_only_cmd = [
                _ffmpeg_bin(),
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(input_path),
                "-filter:v",
                video_filter,
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(output_path),
            ]
            retry = subprocess.run(
                video_only_cmd, capture_output=True, text=True, timeout=240
            )
            if retry.returncode == 0:
                return
            result = retry
        raise RuntimeError(
            f"ffmpeg exited with code {result.returncode}: "
            f"{result.stderr.strip() or 'no stderr output'}"
        )

