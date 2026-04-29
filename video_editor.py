"""Video processing utilities for golf lesson videos."""

import os

import numpy as np
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
FONT_COLOR = 'white'
BEFORE_BG = (45, 106, 45)    # dark green
AFTER_BG = (30, 80, 140)     # dark blue
TITLE_BG = (20, 60, 20)


def _resize_to_height(clip, height):
    """Resize clip to a fixed height, preserving aspect ratio."""
    scale = height / clip.h
    new_w = int(clip.w * scale)
    # ensure even dimensions for codec compatibility
    new_w = new_w if new_w % 2 == 0 else new_w + 1
    return resize(clip, height=height, width=new_w)


def _make_label_clip(text, width, height, bg_color, duration):
    """Create a solid-color label clip with centred text."""
    bg = ColorClip(size=(width, height), color=bg_color, duration=duration)
    try:
        txt = TextClip(
            text,
            fontsize=22,
            color=FONT_COLOR,
            font='DejaVu-Sans-Bold',
        ).set_duration(duration)
        txt = txt.set_position('center')
        return CompositeVideoClip([bg, txt], size=(width, height))
    except Exception:
        # If text rendering fails (no fonts), return plain colour bar
        return bg


def create_comparison_video(before_path, after_path, output_path):
    """Create a side-by-side before/after comparison video.

    Args:
        before_path: Path to the "before" video file.
        after_path:  Path to the "after" video file.
        output_path: Destination path for the output MP4.
    """
    before_clip = VideoFileClip(before_path)
    after_clip = VideoFileClip(after_path)

    try:
        # Match durations — use the shorter clip's length
        duration = min(before_clip.duration, after_clip.duration)
        before_clip = before_clip.subclip(0, duration)
        after_clip = after_clip.subclip(0, duration)

        # Resize both clips to the same height
        before_resized = _resize_to_height(before_clip, TARGET_HEIGHT)
        after_resized = _resize_to_height(after_clip, TARGET_HEIGHT)

        w_before = before_resized.w
        w_after = after_resized.w

        # Create label bars
        before_label = _make_label_clip('Before', w_before, LABEL_HEIGHT, BEFORE_BG, duration)
        after_label = _make_label_clip('After', w_after, LABEL_HEIGHT, AFTER_BG, duration)

        # Stack label + video vertically for each side using clips_array
        left = clips_array([[before_label], [before_resized]])
        right = clips_array([[after_label], [after_resized]])

        # Place side by side
        final = clips_array([[left, right]])

        final.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile=output_path + '.temp_audio.m4a',
            remove_temp=True,
            logger=None,
        )
    finally:
        before_clip.close()
        after_clip.close()


def _parse_time(value):
    """Parse a time value that can be a number (seconds) or HH:MM:SS string."""
    if isinstance(value, (int, float)):
        return float(value)
    value = str(value).strip()
    parts = value.split(':')
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    if len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return float(value)


def create_summary_video(lesson_path, clips, output_path):
    """Extract clips from a lesson video and concatenate with crossfade transitions.

    Args:
        lesson_path: Path to the full lesson video.
        clips:       List of dicts with 'start' and 'end' keys (seconds or HH:MM:SS).
        output_path: Destination path for the output MP4.
    """
    if not clips:
        raise ValueError('At least one clip must be specified.')

    source = VideoFileClip(lesson_path)
    segments = []
    try:
        for clip_info in clips:
            start = _parse_time(clip_info['start'])
            end = _parse_time(clip_info['end'])
            if end <= start:
                raise ValueError(f'Clip end time ({end}s) must be greater than start time ({start}s).')
            end = min(end, source.duration)
            start = max(start, 0.0)
            if start >= source.duration:
                continue
            seg = source.subclip(start, end)
            segments.append(seg)

        if not segments:
            raise ValueError('No valid clips found within the video duration.')

        crossfade = 0.5  # seconds
        # Apply crossfade if more than one clip and each is long enough
        if len(segments) > 1:
            faded = []
            for i, seg in enumerate(segments):
                if i > 0 and seg.duration > crossfade:
                    seg = seg.crossfadein(crossfade)
                faded.append(seg)
            final = concatenate_videoclips(faded, padding=-crossfade, method='compose')
        else:
            final = segments[0]

        final.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile=output_path + '.temp_audio.m4a',
            remove_temp=True,
            logger=None,
        )
    finally:
        source.close()
        for seg in segments:
            try:
                seg.close()
            except Exception:
                pass
