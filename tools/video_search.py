"""
video_search.py — SerpApi YouTube Search Tool
==============================================

This file contains two things:
  1. VIDEO_SEARCH_SCHEMA — the JSON schema shown to the LLM so it knows this tool exists
  2. search_video()     — the actual Python function that runs when the LLM calls this tool

IMPORTANT CONCEPT: The schema and the function are completely separate things.
- The schema is TEXT that the LLM reads to decide "should I call this tool?"
- The function is CODE that YOUR program runs after the LLM says "yes, call it with these args"
- The LLM never sees or runs your Python code. It only sees the schema.
"""

import os
import re
import json
import requests


# =============================================================================
# TOOL SCHEMA (Step 1)
# =============================================================================
# This dict gets converted to JSON and sent to Groq as part of the
# chat completion request. The model reads it like a menu item:
#   "name"        → what to call it by (the model outputs this exact string)
#   "description" → WHEN to use it and WHAT it returns (the model's decision-making input)
#   "parameters"  → WHAT arguments to provide (the model fills these in)
#
# BAD description:  "Searches for videos"
#   → Too vague. The model doesn't know if this searches Vimeo, TikTok, or YouTube.
#      It doesn't know what format the result comes in.
#
# GOOD description: "Searches YouTube for a video matching the query using SerpApi.
#                    Returns a JSON object with 'title', 'url', and 'channel' of
#                    the top result, or an 'error' field if the search fails."
#   → The model knows: it's YouTube, it uses SerpApi, it returns structured JSON
#     with specific fields. This lets the model use the 'url' field in a follow-up
#     tool call (like passing it to a transcription tool).

VIDEO_SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_video",
        "description": (
            "Searches YouTube for a video matching the given query using SerpApi. "
            "Returns a JSON object containing 'title' (the video's title), "
            "'url' (the full YouTube watch URL), and 'channel' (the uploader's "
            "channel name) for the top matching result. If no results are found "
            "or the search fails, returns a JSON object with an 'error' field "
            "describing what went wrong."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "The search query to find a YouTube video. "
                        "Should be a natural-language phrase describing the "
                        "video topic, e.g. 'how transformers work in AI' or "
                        "'Python asyncio tutorial'."
                    ),
                }
            },
            "required": ["query"],
        },
    },
}


# =============================================================================
# TOOL IMPLEMENTATION (Step 2)
# =============================================================================
# This function does the ACTUAL WORK. It's called by your orchestration loop
# when the model outputs a tool_call with name="search_video".
#
# Key design rules:
#   1. Always return a JSON STRING (not a dict) — the tool result goes back
#      into the messages array as a string.
#   2. On failure, return {"error": "..."} — never raise an exception that
#      would crash the loop. Let the model see the error and decide what to do.
#   3. Use environment variables for API keys — never hardcode secrets.

def search_video(query: str) -> str:
    """
    Calls SerpApi's YouTube search endpoint and returns the top result.

    Args:
        query: The search string (e.g. "how transformers work")

    Returns:
        A JSON string with keys: title, url, channel
        OR a JSON string with key: error
    """
    # -------------------------------------------------------------------
    # STEP A: Validate input before doing any external call.
    #
    # WHY? The model generates the arguments as text. It can produce:
    #   - An empty string:   {"query": ""}
    #   - Whitespace only:   {"query": "   "}
    #   - Something weird:   {"query": 12345}   (wrong type)
    #
    # If we blindly pass an empty query to SerpApi, we'd waste an API call
    # and get confusing results. Catching it here is cheaper and clearer.
    # -------------------------------------------------------------------
    if not query or not isinstance(query, str) or not query.strip():
        return json.dumps({"error": "Invalid query: query must be a non-empty string."})

    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        return json.dumps({"error": "SERPAPI_KEY environment variable is not set."})

    # -------------------------------------------------------------------
    # STEP B: Make the API call, wrapped in try/except.
    #
    # What could go wrong here?
    #   - Network timeout (no internet, SerpApi down)
    #   - Invalid API key (401 response)
    #   - Rate limit exceeded (429 response)
    #   - Unexpected response format (SerpApi changes their API)
    #
    # In ALL these cases, we catch the exception and return {"error": ...}
    # so the model can see what happened and either retry or tell the user.
    # -------------------------------------------------------------------
    try:
        response = requests.get(
            "https://serpapi.com/search",
            params={
                "engine": "youtube",      # Use SerpApi's YouTube-specific engine
                "search_query": query,    # The search term
                "api_key": api_key,
                "num": 1,                 # We only need the top result
            },
            timeout=15,  # Don't hang forever if SerpApi is slow
        )
        response.raise_for_status()  # Raises HTTPError for 4xx/5xx responses

    except requests.exceptions.Timeout:
        return json.dumps({"error": "SerpApi request timed out after 15 seconds."})
    except requests.exceptions.ConnectionError:
        return json.dumps({"error": "Could not connect to SerpApi. Check your internet connection."})
    except requests.exceptions.HTTPError as e:
        return json.dumps({"error": f"SerpApi returned HTTP error: {e}"})
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"SerpApi request failed: {e}"})

    # -------------------------------------------------------------------
    # STEP C: Parse the response and extract the first video result.
    #
    # SerpApi returns a JSON object. For YouTube searches, the video results
    # live under the key "video_results". Each result has:
    #   - "title": the video title
    #   - "link":  the full YouTube URL
    #   - "channel": {"name": "...", "link": "..."}
    # -------------------------------------------------------------------
    try:
        data = response.json()
    except (json.JSONDecodeError, ValueError):
        return json.dumps({"error": "SerpApi returned invalid JSON."})

    video_results = data.get("video_results", [])
    if not video_results:
        return json.dumps({"error": f"No YouTube videos found for query: '{query}'"})

    top_result = video_results[0]

    # Extract fields safely — use .get() with defaults so we never crash
    # on missing keys if SerpApi changes their response format.
    result = {
        "title": top_result.get("title", "Unknown Title"),
        "url": top_result.get("link", ""),
        "channel": top_result.get("channel", {}).get("name", "Unknown Channel"),
    }

    # Final safety check: did we actually get a URL?
    if not result["url"]:
        return json.dumps({"error": "Found a video result but it had no URL."})

    # Extract video ID to generate crisp YouTube thumbnail URL
    video_id_match = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", result["url"])
    if video_id_match:
        result["thumbnail"] = f"https://img.youtube.com/vi/{video_id_match.group(1)}/hqdefault.jpg"
    else:
        result["thumbnail"] = top_result.get("thumbnail", {}).get("static", "")

    return json.dumps(result)
