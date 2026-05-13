"""Video processing utilities (synchronous, file-path based).

Ported from the original ``video_editor.py`` so the FastAPI backend can run
the comparison/summary pipelines inside a Celery worker or directly during a
short-lived HTTP request.
"""

from __future__ import annotations

from moviepy.editor import (
    VideoFileClip,
    CompositeVideoClip,
    concatenate_videoclips,
    ColorClip,
    TextClip,
    clips_array,
)
from moviepy.video.fx.resize import resize


TARGET_HEIGHT = 480
LABEL_HEIGHT = 40
FONT_COLOR = "white"
BEFORE_BG = (45, 106, 45)
AFTER_BG = (30, 80, 140)


def _resize_to_height(clip, height: int):
    scale = height / clip.h
    new_w = int(clip.w * scale)
    if new_w % 2 != 0:
        new_w += 1
    return resize(clip, height=height, width=new_w)


def _make_label_clip(text: str, width: int, height: int, bg_color, duration: float):
    bg = ColorClip(size=(width, height), color=bg_color, duration=duration)
    try:
        txt = (
            TextClip(text, fontsize=22, color=FONT_COLOR, font="DejaVu-Sans-Bold")
            .set_duration(duration)
            .set_position("center")
        )
        return CompositeVideoClip([bg, txt], size=(width, height))
    except Exception:
        return bg


def create_comparison_video(before_path: str, after_path: str, output_path: str) -> None:
    """Render a side-by-side before/after MP4."""
    before_clip = VideoFileClip(before_path)
    after_clip = VideoFileClip(after_path)
    try:
        duration = min(before_clip.duration, after_clip.duration)
        before_clip = before_clip.subclip(0, duration)
        after_clip = after_clip.subclip(0, duration)

        before_resized = _resize_to_height(before_clip, TARGET_HEIGHT)
        after_resized = _resize_to_height(after_clip, TARGET_HEIGHT)

        before_label = _make_label_clip(
            "Before", before_resized.w, LABEL_HEIGHT, BEFORE_BG, duration
        )
        after_label = _make_label_clip(
            "After", after_resized.w, LABEL_HEIGHT, AFTER_BG, duration
        )

        left = clips_array([[before_label], [before_resized]])
        right = clips_array([[after_label], [after_resized]])
        final = clips_array([[left, right]])

        final.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=output_path + ".temp_audio.m4a",
            remove_temp=True,
            logger=None,
            threads=2,
            preset="ultrafast",
        )
    finally:
        before_clip.close()
        after_clip.close()


def _parse_time(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    value = str(value).strip()
    parts = value.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    if len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return float(value)


def create_summary_video(lesson_path: str, clips: list[dict], output_path: str) -> None:
    """Extract clips from a single lesson video and concatenate with crossfade."""
    if not clips:
        raise ValueError("At least one clip must be specified.")

    source = VideoFileClip(lesson_path)
    segments = []
    try:
        for clip_info in clips:
            start = _parse_time(clip_info["start"])
            end = _parse_time(clip_info["end"])
            if end <= start:
                raise ValueError(
                    f"Clip end ({end}s) must be greater than start ({start}s)."
                )
            end = min(end, source.duration)
            start = max(start, 0.0)
            if start >= source.duration:
                continue
            segments.append(source.subclip(start, end))

        if not segments:
            raise ValueError("No valid clips found within the video duration.")

        crossfade = 0.5
        if len(segments) > 1:
            faded = []
            for i, seg in enumerate(segments):
                if i > 0 and seg.duration > crossfade:
                    seg = seg.crossfadein(crossfade)
                faded.append(seg)
            final = concatenate_videoclips(faded, padding=-crossfade, method="compose")
        else:
            final = segments[0]

        final.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=output_path + ".temp_audio.m4a",
            remove_temp=True,
            logger=None,
            threads=2,
            preset="ultrafast",
        )
    finally:
        source.close()
        for seg in segments:
            try:
                seg.close()
            except Exception:
                pass
