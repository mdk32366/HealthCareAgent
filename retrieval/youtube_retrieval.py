"""
YouTube retrieval: search for relevant health videos and extract transcripts.
Falls back to yt-dlp metadata when youtube-transcript-api is unavailable.
"""
from __future__ import annotations
import hashlib, logging, re
from typing import Optional

from agent.models import SourceDocument, HealthTopic

log = logging.getLogger(__name__)

# Curated YouTube channel IDs / handles for healthcare
TRUSTED_YT_CHANNELS = [
    "UCsT0YIqwnpJCM-mx7-gSA4Q",  # TEDx Talks (health)
    "UCVxxyygDaGoXn9yQN3kxHIA",  # Medscape
    "UCgRiqs3GMqEEFD8pDcxNqjQ",  # Mayo Clinic
    "UC1O0jDlnZjA5ZQOK5RmNRoQ",  # Cleveland Clinic
    "UCDZRqC4HQjBiYTqBkJgYMIw",  # Healthline
    "UCWQ3lFHLm5ZRSd98l7dpqPw",  # Osmosis (med education)
]


def _clean_transcript(text: str) -> str:
    """Remove filler, collapse whitespace."""
    text = re.sub(r"\[.*?\]", "", text)          # [Music], [Applause]
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def search_youtube(
    query: str,
    topic: HealthTopic,
    max_results: int = 5,
) -> list[SourceDocument]:
    """
    Search YouTube for health-related videos, extract transcripts.
    Uses youtube-transcript-api for transcripts and yt-dlp for metadata.
    """
    topic_yt_queries = {
        HealthTopic.VACCINES:   f"{query} vaccine treatment site:youtube.com",
        HealthTopic.CANCER:     f"{query} cancer therapy explained site:youtube.com",
        HealthTopic.HEMOPHILIA: f"{query} hemophilia treatment site:youtube.com",
        HealthTopic.WEIGHT:     f"{query} weight loss treatment site:youtube.com",
        HealthTopic.DIABETES:   f"{query} diabetes management site:youtube.com",
        HealthTopic.GENERAL:    f"{query} medical explanation site:youtube.com",
    }
    yt_query = topic_yt_queries.get(topic, f"{query} medical explanation")

    video_ids: list[str] = []

    # Method 1: yt-dlp search (no API key required)
    try:
        import yt_dlp
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "playlistend": max_results,
        }
        search_url = f"ytsearch{max_results}:{yt_query}"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_url, download=False)
            if info and "entries" in info:
                for entry in info["entries"]:
                    if entry and entry.get("id"):
                        video_ids.append(entry["id"])
    except Exception as exc:
        log.warning(f"yt-dlp search failed: {exc}")

    if not video_ids:
        log.info("No YouTube video IDs found")
        return []

    docs = []
    for vid_id in video_ids[:max_results]:
        doc = _fetch_video_doc(vid_id, query, topic)
        if doc:
            docs.append(doc)

    log.info(f"YouTube retrieval: {len(docs)} usable transcripts for: {query!r}")
    return docs


def _fetch_video_doc(
    video_id: str,
    query: str,
    topic: HealthTopic,
) -> Optional[SourceDocument]:
    """
    Fetch metadata + transcript for a single YouTube video.
    Returns None if transcript is unavailable.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    title = url   # fallback

    # Get metadata via yt-dlp
    try:
        import yt_dlp
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                title    = info.get("title", url)
                uploader = info.get("uploader", "")
                date_str = info.get("upload_date", "")
                if date_str:
                    date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    except Exception:
        uploader = ""
        date_str = ""

    # Get transcript via youtube-transcript-api
    transcript_text = ""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound
        transcript = YouTubeTranscriptApi.get_transcript(
            video_id, languages=["en", "en-US", "en-GB"]
        )
        raw = " ".join(seg["text"] for seg in transcript)
        transcript_text = _clean_transcript(raw)
    except Exception as exc:
        log.debug(f"No transcript for {video_id}: {exc}")
        return None   # skip videos without accessible transcripts

    if len(transcript_text) < 100:
        return None

    # Trim to reasonable size (first 3000 chars for context)
    transcript_text = transcript_text[:3000]

    return SourceDocument(
        content=(
            f"YouTube Video: {title}\n"
            f"Channel: {uploader}\n\n"
            f"Transcript excerpt:\n{transcript_text}"
        ),
        url=url,
        title=title,
        source_type="youtube",
        topic=topic.value,
        published_date=date_str,
        chunk_id=hashlib.md5(video_id.encode()).hexdigest(),
    )
