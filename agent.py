#!/usr/bin/env python3
import sys
import json
import os
from openai import OpenAI

def main():
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"Your question here\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    # Initialize client (assumes OPENAI_API_KEY is set in environment)
    client = OpenAI()

    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # or any other model you prefer
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Answer concisely."},
                {"role": "user", "content": question}
            ],
            max_tokens=500,
            timeout=60  # Ensure response within 60 seconds
        )

        answer = response.choices[0].message.content.strip()

        # Construct required JSON output
        result = {
            "answer": answer,
            "tool_calls": []  # Empty array as per Task 1 rules
        }

        # Output only valid JSON to stdout
        print(json.dumps(result))

        # Exit code 0 on success
        sys.exit(0)

    except Exception as e:
        # Send debug/progress info to stderr
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
