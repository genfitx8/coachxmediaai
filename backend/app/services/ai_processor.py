"""
Stub AI processor functions. Replace these with real model calls (e.g. OpenAI Whisper,
GPT-4, or custom CV models) when integrating actual AI capabilities.
"""


def transcribe(media_key: str) -> dict:
    """Simulate audio/video transcription."""
    return {
        "transcript": "stub transcript text",
        "language": "en",
        "media_key": media_key,
    }


def summarize(transcript: str) -> dict:
    """Simulate text summarization."""
    return {
        "summary": "stub summary",
        "word_count": len(transcript.split()),
    }


def analyze(media_key: str) -> dict:
    """Simulate video/image analysis."""
    return {
        "scenes": [],
        "duration": 0,
        "objects": [],
        "media_key": media_key,
    }
