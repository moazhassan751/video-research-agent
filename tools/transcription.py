"""
transcription.py — Groq Whisper Video Transcription Tool
=========================================================

This file contains:
  1. TRANSCRIPTION_SCHEMA  — the JSON schema shown to the LLM
  2. transcribe_video()    — the function that transcribes a YouTube video

HOW THIS WORKS (two-step process):
  Step A: Download the audio track from the YouTube video using yt-dlp.
          yt-dlp grabs the audio-only stream (m4a or webm format) directly
          from YouTube — no ffmpeg needed, no video data downloaded.

  Step B: Send the audio file to Groq's Whisper API (whisper-large-v3-turbo).
          Groq hosts OpenAI's Whisper model and your existing GROQ_API_KEY
          covers both the LLM (LLaMA) and Whisper. The API accepts audio
          files up to 25MB and returns the transcript as text.

WHY SAVE THE TRANSCRIPT INSIDE THIS FUNCTION?
  The tool owns its side effects. If transcription succeeds, saving to disk
  happens right here. The orchestration loop stays simple — it just routes
  messages. The tool reports back "saved_to": "..." so the model can tell
  the user where their transcript lives.
"""

import os
import re
import json
import tempfile
import shutil
from pathlib import Path

from groq import Groq
import yt_dlp


# =============================================================================
# TOOL SCHEMA
# =============================================================================
# The description tells the model:
#   1. WHAT it does (transcribes audio from a YouTube video)
#   2. HOW it does it (downloads audio, then uses Groq Whisper)
#   3. WHAT it returns (transcript text + saved file path)
#   4. WHAT errors look like (JSON with 'error' field)

TRANSCRIPTION_SCHEMA = {
    "type": "function",
    "function": {
        "name": "transcribe_video",
        "description": (
            "Transcribes the audio content of a YouTube video. First downloads "
            "the audio track using yt-dlp, then transcribes it using Groq's "
            "Whisper speech-to-text model. The transcript is automatically saved "
            "to a local file in the knowledge_base/ directory. Returns a JSON "
            "object with 'transcript' (the transcribed text), 'saved_to' (the "
            "file path where the transcript was saved), and 'video_title'. "
            "If transcription fails, returns a JSON object with an 'error' field."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "video_url": {
                    "type": "string",
                    "description": (
                        "The full YouTube video URL to transcribe, e.g. "
                        "'https://www.youtube.com/watch?v=dQw4w9WgXcQ'. "
                        "Must be a valid YouTube watch URL."
                    ),
                },
                "video_title": {
                    "type": "string",
                    "description": (
                        "The title of the video, used to generate a readable "
                        "filename for the saved transcript. If not provided, "
                        "a generic filename based on the video ID will be used."
                    ),
                },
            },
            "required": ["video_url"],
        },
    },
}


# =============================================================================
# HELPER: Generate a safe filename from a video title
# =============================================================================
def _make_safe_filename(title: str, max_length: int = 80) -> str:
    """
    Converts a video title into a filesystem-friendly filename.

    "How Transformers Work (2024)"  ->  "how_transformers_work_2024"
    "C++ Tutorial: Part 1/3"        ->  "c_tutorial_part_13"
    """
    safe = re.sub(r"[^\w\s-]", "", title)
    safe = re.sub(r"\s+", "_", safe.strip())
    safe = safe.lower()[:max_length].rstrip("_")
    return safe if safe else "untitled_video"


# =============================================================================
# HELPER: Download audio from YouTube
# =============================================================================
def _download_audio(video_url: str, output_dir: str, section: str = None) -> str:
    """
    Downloads audio-only stream from YouTube using yt-dlp.

    Key Optimization:
    We target lower bitrate audio streams (ba[abr<=64]/worstaudio).
    Speech recognition models (Whisper) only need vocal frequencies.
    Downloading at 32k-64k mono reduces file size by 75%+ without losing
    speech accuracy, fitting 45min+ videos under Groq's 25MB limit.
    """
    output_template = os.path.join(output_dir, "audio.%(ext)s")

    ydl_opts = {
        # Prefer low-bitrate audio streams suitable for speech recognition
        "format": "ba[abr<=64]/ba[abr<=96]/worstaudio/bestaudio[ext=m4a]/bestaudio",
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 30,
    }

    if section:
        # Download specific section if video is exceptionally long (e.g. "*00:00-20:00")
        ydl_opts["download_ranges"] = yt_dlp.utils.download_range_func(None, [(0, 1200)])
        ydl_opts["force_keyframes_at_cuts"] = True

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    files = os.listdir(output_dir)
    if not files:
        raise FileNotFoundError("yt-dlp did not produce an output file.")

    return os.path.join(output_dir, files[0])


# =============================================================================
# TOOL IMPLEMENTATION
# =============================================================================
def transcribe_video(video_url: str, video_title: str = "") -> str:
    """
    Downloads audio from a YouTube video and transcribes it using Groq Whisper.
    Saves the transcript to knowledge_base/.

    Args:
        video_url:   Full YouTube URL
        video_title: Optional title for the saved filename

    Returns:
        JSON string with: transcript, saved_to, video_title
        OR JSON string with: error
    """
    # -------------------------------------------------------------------
    # STEP A: Validate inputs
    # -------------------------------------------------------------------
    if not video_url or not isinstance(video_url, str):
        return json.dumps({"error": "video_url must be a non-empty string."})

    youtube_patterns = ["youtube.com/watch", "youtu.be/", "youtube.com/shorts/"]
    if not any(pattern in video_url for pattern in youtube_patterns):
        return json.dumps({
            "error": f"URL does not appear to be a YouTube video: {video_url}"
        })

    groq_key = os.environ.get("GROQ_API_KEY")
    if not groq_key:
        return json.dumps({"error": "GROQ_API_KEY environment variable is not set."})

    # -------------------------------------------------------------------
    # STEP B: Download audio from YouTube using yt-dlp
    #
    # We download to a temporary directory that we clean up afterward.
    # This prevents leftover audio files from piling up on disk.
    # -------------------------------------------------------------------
    temp_dir = tempfile.mkdtemp(prefix="agent_audio_")

    try:
        audio_path = _download_audio(video_url, temp_dir)
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        error_msg = str(e)
        if "Video unavailable" in error_msg or "Private video" in error_msg:
            return json.dumps({"error": f"Video is unavailable or private: {error_msg}"})
        elif "HTTP Error 429" in error_msg:
            return json.dumps({"error": f"YouTube rate-limited the download. Try again in a minute."})
        else:
            return json.dumps({"error": f"Failed to download audio from YouTube: {error_msg}"})

    # Check file size — Groq Whisper accepts up to 25MB
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    if file_size_mb > 24:
        # Retry with 20-minute section clipping if full audio exceeds 24MB
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
            temp_dir = tempfile.mkdtemp(prefix="agent_audio_clip_")
            audio_path = _download_audio(video_url, temp_dir, section="00:00-20:00")
            file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        except Exception:
            pass

    if file_size_mb > 25:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return json.dumps({
            "error": f"Audio file is {file_size_mb:.1f}MB, which exceeds Groq Whisper's "
                     f"25MB limit. Try a shorter video or segment."
        })

    # -------------------------------------------------------------------
    # STEP C: Send audio to Groq Whisper for transcription
    #
    # Groq hosts OpenAI's Whisper model. We use the same GROQ_API_KEY
    # that powers the LLM. The API is:
    #   client.audio.transcriptions.create(file=..., model=...)
    #
    # The model "whisper-large-v3-turbo" is fast and accurate.
    # -------------------------------------------------------------------
    try:
        client = Groq()
        filename = os.path.basename(audio_path)

        with open(audio_path, "rb") as audio_file:
            transcription_result = client.audio.transcriptions.create(
                file=(filename, audio_file.read()),
                model="whisper-large-v3-turbo",
                response_format="text",
            )

        # The result is the transcript text directly (when response_format="text")
        transcript = str(transcription_result).strip()

    except Exception as e:
        error_msg = str(e)
        if "413" in error_msg or "too large" in error_msg.lower():
            return json.dumps({"error": "Audio file too large for Whisper API. Try a shorter video."})
        elif "401" in error_msg or "403" in error_msg:
            return json.dumps({"error": f"Groq authentication failed for Whisper. Check GROQ_API_KEY. Details: {error_msg}"})
        else:
            return json.dumps({"error": f"Groq Whisper transcription failed: {error_msg}"})
    finally:
        # Always clean up the temp audio file
        shutil.rmtree(temp_dir, ignore_errors=True)

    if not transcript:
        return json.dumps({"error": "Whisper returned an empty transcript. The video may have no speech."})

    # -------------------------------------------------------------------
    # STEP D: Save transcript to knowledge_base/
    # -------------------------------------------------------------------
    try:
        project_root = Path(__file__).parent.parent
        kb_dir = project_root / "knowledge_base"
        kb_dir.mkdir(exist_ok=True)

        title_for_file = video_title if video_title else "untitled_video"
        safe_name = _make_safe_filename(title_for_file)
        file_path = kb_dir / f"{safe_name}.txt"

        # Handle duplicate filenames
        counter = 1
        while file_path.exists():
            file_path = kb_dir / f"{safe_name}_{counter}.txt"
            counter += 1

        file_path.write_text(transcript, encoding="utf-8")
        saved_to = str(file_path)

    except OSError as e:
        return json.dumps({
            "transcript": transcript[:2000],
            "saved_to": None,
            "save_error": f"Could not save transcript to disk: {e}",
            "video_title": video_title or "untitled",
        })

    # -------------------------------------------------------------------
    # STEP E: Return structured result
    #
    # Truncate transcript in the return value to avoid bloating the
    # model's context. The full text is saved to disk.
    # -------------------------------------------------------------------
    return json.dumps({
        "transcript": transcript[:3000],
        "full_transcript_length": len(transcript),
        "saved_to": saved_to,
        "video_title": video_title or "untitled",
    })
