"""
main.py — CLI Entry Point
==========================

This is the file you run:
    python main.py "find a video about how transformers work"
    python main.py   (interactive — prompts you for a query)

It does three things:
  1. Loads API keys from .env file using python-dotenv
  2. Takes the user's query from command-line args or input()
  3. Calls run_agent() and prints the final answer

This file is intentionally simple — all the complex logic lives in agent.py
and the tool files. main.py is just the front door.
"""

import sys
import os

# Load environment variables BEFORE importing anything that uses them.
# python-dotenv reads your .env file and sets the variables in os.environ.
# This must happen first, otherwise the tool functions will see empty API keys.
from dotenv import load_dotenv
load_dotenv()

from agent import run_agent


def main():
    """Entry point for the agent CLI."""
    # ------------------------------------------------------------------
    # STEP 1: Validate that all required API keys are present.
    #
    # We check upfront rather than letting tools fail mid-loop.
    # This gives the user a clear, immediate error message instead of
    # a cryptic tool error 2 turns into the conversation.
    # ------------------------------------------------------------------
    required_keys = {
        "SERPAPI_KEY": "SerpApi (for YouTube search)",
        "GROQ_API_KEY": "Groq (for the LLM backbone + Whisper transcription)",
    }

    missing = []
    for key, service in required_keys.items():
        if not os.environ.get(key):
            missing.append(f"  - {key} ({service})")

    if missing:
        print("[ERROR] Missing required API keys:\n")
        print("\n".join(missing))
        print("\nCreate a .env file in the project root with these keys.")
        print("See .env.example for the template.")
        sys.exit(1)

    print("[SUCCESS] All API keys loaded successfully.")

    # ------------------------------------------------------------------
    # STEP 2: Get the user's query.
    #
    # Two modes:
    #   python main.py "find a video about X"  → takes from sys.argv
    #   python main.py                         → prompts interactively
    # ------------------------------------------------------------------
    if len(sys.argv) > 1:
        # Join all args after the script name into one query string
        user_query = " ".join(sys.argv[1:])
    else:
        print("\n[START] Video Research Agent")
        print("─" * 40)
        user_query = input("Enter your query: ").strip()

    if not user_query:
        print("[ERROR] No query provided. Usage: python main.py \"your query here\"")
        sys.exit(1)

    # ------------------------------------------------------------------
    # STEP 3: Run the agent and display the result.
    # ------------------------------------------------------------------
    try:
        final_answer = run_agent(user_query)
    except KeyboardInterrupt:
        print("\n\n[INFO] Agent interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Agent failed with an unexpected error: {e}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("FINAL ANSWER")
    print(f"{'='*60}")
    print(final_answer)
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
