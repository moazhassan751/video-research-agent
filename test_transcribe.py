"""
test_transcribe.py — Test Long Video Audio Optimization
"""

import os
from dotenv import load_dotenv
load_dotenv()

from tools.transcription import transcribe_video

def main():
    # Long video that previously returned 43.8MB audio
    test_url = "https://www.youtube.com/watch?v=F8vI5_gN90g"
    test_title = "Inside the planets most urgent climate warning Global Warning E1"

    print("--- TESTING LOW-BITRATE AUDIO OPTIMIZATION FOR LONG VIDEO ---")
    print(f"Target URL: {test_url}")
    print("Downloading & transcribing...")

    result = transcribe_video(test_url, test_title)
    print("\nResult JSON:")
    print(result[:400] + "..." if len(result) > 400 else result)

if __name__ == "__main__":
    main()
