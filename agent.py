#!/usr/bin/env python3
"""
Agent CLI - connects to an LLM via OpenAI-compatible API.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON with "answer", "source", and "tool_calls" fields to stdout.
    All debug/error output goes to stderr.
"""

import sys
import json
import os
from pathlib import Path
from openai import OpenAI


# Project root directory (parent of agent.py)
PROJECT_ROOT = Path(__file__).resolve().parent

# Maximum tool call iterations per question
MAX_ITERATIONS = 10


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


def validate_path(path: str) -> tuple[bool, str]:
    """
    Validate that a path is safe (no directory traversal).
    
    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is empty.
    """
    # Reject paths with directory traversal
    if ".." in path:
        return False, "Security error: path traversal not allowed"
    
    # Reject absolute paths
    if os.path.isabs(path):
        return False, "Security error: absolute paths not allowed"
    
    # Resolve the full path
    full_path = (PROJECT_ROOT / path).resolve()
    
    # Ensure the resolved path is within project root
    if not str(full_path).startswith(str(PROJECT_ROOT)):
        return False, "Security error: path outside project directory"
    
    return True, ""


def read_file(path: str) -> str:
    """
    Read a file from the project repository.
    
    Parameters:
        path: Relative path from project root.
    
    Returns:
        File contents as string, or error message if file doesn't exist.
    """
    is_valid, error = validate_path(path)
    if not is_valid:
        return error
    
    full_path = PROJECT_ROOT / path
    
    if not full_path.exists():
        return f"Error: File not found: {path}"
    
    if not full_path.is_file():
        return f"Error: Not a file: {path}"
    
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


def list_files(path: str) -> str:
    """
    List files and directories at a given path.

    Parameters:
        path: Relative directory path from project root.

    Returns:
        Newline-separated listing of entries, or error message.
    """
    is_valid, error = validate_path(path)
    if not is_valid:
        return error

    full_path = PROJECT_ROOT / path

    if not full_path.exists():
        return f"Error: Directory not found: {path}"

    if not full_path.is_dir():
        return f"Error: Not a directory: {path}"

    try:
        entries = os.listdir(full_path)
        return "\n".join(sorted(entries))
    except Exception as e:
        return f"Error listing directory: {e}"


def query_api(method: str, path: str, body: str = None) -> str:
    """
    Send an HTTP request to the backend API.

    Parameters:
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        path: API path (e.g., '/items/', '/analytics/completion-rate')
        body: Optional JSON request body for POST/PUT requests

    Returns:
        JSON string with status_code and body fields.
    """
    import urllib.request
    import urllib.error
    import json

    # Read configuration from environment variables
    api_key = os.environ.get("LMS_API_KEY", "")
    base_url = os.environ.get("AGENT_API_BASE_URL", "http://localhost:42002")

    url = f"{base_url}{path}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = body.encode() if body else None

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            response_body = resp.read().decode()
            return json.dumps({
                "status_code": resp.status,
                "body": response_body
            })
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        return json.dumps({
            "status_code": e.code,
            "body": error_body
        })
    except Exception as e:
        return json.dumps({
            "status_code": 0,
            "body": f"Error: {str(e)}"
        })


# Tool schemas for OpenAI function calling
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the project repository. Returns file contents or error message.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g., 'wiki/git-workflow.md')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given path. Returns newline-separated entries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root (e.g., 'wiki')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Send an HTTP request to the backend API. Use for data queries like item counts, analytics, or checking API responses. Returns JSON with status_code and body.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "description": "HTTP method (GET, POST, PUT, DELETE, etc.)"
                    },
                    "path": {
                        "type": "string",
                        "description": "API path (e.g., '/items/', '/analytics/completion-rate')"
                    },
                    "body": {
                        "type": "string",
                        "description": "Optional JSON request body for POST/PUT requests"
                    }
                },
                "required": ["method", "path"]
            }
        }
    }
]

# Map tool names to functions
TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_files": list_files,
    "query_api": query_api
}

# System prompt for the documentation agent
SYSTEM_PROMPT = """You are a documentation and system assistant for a software engineering lab project.

You have access to three tools:
- list_files: List files and directories at a given path
- read_file: Read the contents of a file
- query_api: Send HTTP requests to the backend API

Tool selection guidance:
- Use list_files to discover what files exist in a directory
- Use read_file to read wiki documentation, source code, or configuration files
- Use query_api to query the running backend API for data (item counts, analytics, etc.)
  or to check API behavior (status codes, errors)

When answering questions:
1. For wiki/documentation questions: use read_file on wiki/*.md files
2. For source code questions: use read_file on backend/app/*.py files
3. For data queries (how many items, what's the completion rate): use query_api
4. For API behavior questions (status codes, errors): use query_api

Always cite your source. Answer concisely and directly.
Do not make up information. Only answer based on what you read or query.
If you cannot find the answer, say so honestly.
"""


def execute_tool_call(tool_call) -> dict:
    """
    Execute a single tool call and return the result.
    
    Parameters:
        tool_call: OpenAI tool call object with function name and arguments.
    
    Returns:
        Dict with tool, args, and result fields.
    """
    tool_name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    
    print(f"Executing tool: {tool_name} with args: {args}", file=sys.stderr)
    
    if tool_name not in TOOL_FUNCTIONS:
        result = f"Error: Unknown tool: {tool_name}"
    else:
        func = TOOL_FUNCTIONS[tool_name]
        result = func(**args)
    
    return {
        "tool": tool_name,
        "args": args,
        "result": result
    }


def extract_source_from_answer(answer: str, tool_calls: list) -> str:
    """
    Extract the source reference from the answer or tool calls.
    
    Looks for wiki file references in the answer, or extracts from tool call results.
    """
    # Try to find wiki file reference in answer
    import re
    wiki_pattern = r"wiki/[\w\-\.]+\.md(?:#[\w\-]+)?"
    match = re.search(wiki_pattern, answer, re.IGNORECASE)
    if match:
        return match.group(0)
    
    # Try to find wiki file from tool calls
    for call in tool_calls:
        if call["tool"] == "read_file":
            path = call["args"].get("path", "")
            if path.startswith("wiki/"):
                return path
    
    return "wiki"  # Default to wiki directory


def run_agentic_loop(question: str) -> dict:
    """
    Run the agentic loop to answer a question using tools.
    
    Parameters:
        question: The user's question.
    
    Returns:
        Dict with answer, source, and tool_calls fields.
    """
    # Initialize messages with system prompt and user question
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question}
    ]
    
    # Track all tool calls for output
    all_tool_calls = []
    
    # Agentic loop
    for iteration in range(MAX_ITERATIONS):
        print(f"Iteration {iteration + 1}/{MAX_ITERATIONS}", file=sys.stderr)
        
        # Call LLM with tool schemas
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_SCHEMAS,
            max_tokens=1000,
            timeout=60
        )
        
        choice = response.choices[0]
        message = choice.message
        
        # Check if LLM wants to call tools
        if message.tool_calls:
            # Execute each tool call
            for tool_call in message.tool_calls:
                result = execute_tool_call(tool_call)
                all_tool_calls.append(result)
                
                # Append tool result as a "tool" role message
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result["result"]
                })
            
            # Continue loop to let LLM process tool results
            continue
        else:
            # No tool calls - LLM provided final answer
            answer = message.content.strip()
            source = extract_source_from_answer(answer, all_tool_calls)
            
            return {
                "answer": answer,
                "source": source,
                "tool_calls": all_tool_calls
            }
    
    # Max iterations reached - return whatever we have
    print("Max iterations reached", file=sys.stderr)
    if all_tool_calls:
        # Try to construct an answer from tool results
        last_result = all_tool_calls[-1]["result"]
        source = extract_source_from_answer("", all_tool_calls)
        return {
            "answer": f"Max iterations reached. Last tool result: {last_result[:200]}",
            "source": source,
            "tool_calls": all_tool_calls
        }
    else:
        return {
            "answer": "Unable to answer within iteration limit",
            "source": "wiki",
            "tool_calls": []
        }


def main():
    # Validate command-line arguments
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"Your question here\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    # Load environment configuration
    load_env()

    # Get configuration from environment
    global client, model
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
        
        # Run the agentic loop
        result = run_agentic_loop(question)

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
