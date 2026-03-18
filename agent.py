#!/usr/bin/env python3
"""
Agent CLI - connects to an LLM via OpenAI-compatible API.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON with "answer" and "tool_calls" fields to stdout.
    All debug/error output goes to stderr.
"""

import sys
import json
import os
from openai import OpenAI


def load_env():
    """Load environment variables from .env.agent.secret if it exists."""
    env_file = os.path.join(os.path.dirname(__file__), ".env.agent.secret")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


def main():
    # Validate command-line arguments
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"Your question here\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    # Load environment configuration
    load_env()

    # Get configuration from environment
    api_key = os.environ.get("LLM_API_KEY")
    api_base = os.environ.get("LLM_API_BASE", "http://localhost:8000/v1")
    model = os.environ.get("LLM_MODEL", "qwen3-coder-plus")

    # Validate required configuration
    if not api_key:
        print("Error: LLM_API_KEY not set. Please configure .env.agent.secret", file=sys.stderr)
        sys.exit(1)

    # Initialize OpenAI-compatible client
    client = OpenAI(
        api_key=api_key,
        base_url=api_base
    )

    try:
        print(f"Calling LLM: {model}...", file=sys.stderr)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Answer concisely."},
                {"role": "user", "content": question}
            ],
            max_tokens=500,
            timeout=60
        )

        answer = response.choices[0].message.content.strip()

        # Construct required JSON output
        result = {
            "answer": answer,
            "tool_calls": []  # Empty array as per Task 1 rules
        }

        # Output only valid JSON to stdout
        print(json.dumps(result))

        print("Done.", file=sys.stderr)
        sys.exit(0)

    except Exception as e:
        # Send debug/progress info to stderr
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
