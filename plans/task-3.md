# Task 3: The System Agent - Implementation Plan

## Overview

This task extends the Task 2 agent with a new `query_api` tool that allows the LLM to send HTTP requests to the deployed backend API. This enables the agent to answer both static system questions (framework, ports, status codes) and data-dependent queries (item count, scores, errors).

## Implementation Approach

### 1. Environment Variables

The agent must read all configuration from environment variables (not hardcoded):

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API key for `query_api` auth | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Base URL for query_api | Optional, defaults to `http://localhost:42002` |

**Key insight:** Two distinct keys:
- `LLM_API_KEY` authenticates with the LLM provider
- `LMS_API_KEY` authenticates with the backend API

### 2. query_api Tool Schema

Define the tool as an OpenAI function-calling schema:

```json
{
  "type": "function",
  "function": {
    "name": "query_api",
    "description": "Send an HTTP request to the backend API. Use for data queries like item counts, analytics, or checking API responses.",
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
```

### 3. query_api Tool Implementation

The tool function will:
1. Read `LMS_API_KEY` from environment
2. Read `AGENT_API_BASE_URL` from environment (default: `http://localhost:42002`)
3. Construct the full URL
4. Send HTTP request with `Authorization: Bearer <LMS_API_KEY>` header
5. Return JSON string with `status_code` and `body`

```python
def query_api(method: str, path: str, body: str = None) -> str:
    """Query the backend API with authentication."""
    import urllib.request
    import urllib.error
    import json
    
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
        return json.dumps({
            "status_code": e.code,
            "body": e.read().decode()
        })
    except Exception as e:
        return json.dumps({
            "status_code": 0,
            "body": f"Error: {str(e)}"
        })
```

### 4. System Prompt Update

Update the system prompt to guide the LLM on when to use each tool:

```
You are a documentation and system assistant for a software engineering lab project.

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
```

### 5. Testing Strategy

Add 2 regression tests to `test_agent.py`:

1. **Framework detection test**: "What Python web framework does the backend use?"
   - Expected: `read_file` in tool_calls
   - Expected answer contains: "FastAPI"

2. **Database query test**: "How many items are in the database?"
   - Expected: `query_api` in tool_calls
   - Expected answer contains: a number > 0

### 6. Iteration Strategy

After initial implementation:
1. Run `uv run run_eval.py` to test all 10 questions
2. For each failure:
   - Check if the right tool was called
   - Check if the answer contains expected keywords
   - Adjust tool descriptions or system prompt as needed
3. Common issues and fixes:
   - Agent doesn't use query_api → Improve tool description
   - Agent uses wrong tool → Clarify system prompt guidance
   - Agent times out → Reduce max iterations or simplify prompt

## Benchmark Results (to be filled after first run)

**Note:** The evaluation requires valid LLM credentials. The autochecker will inject its own credentials during evaluation.

Initial score: _/10 (pending autochecker evaluation)

First failures:
- [ ] Question X: [description]
- [ ] Question Y: [description]

Iteration strategy:
1. Fix issue A
2. Re-run
3. Fix issue B
4. Re-run

## Final Score (to be filled)

**Note:** Update this section after running `run_eval.py` with valid credentials.

Final score: _/10

Lessons learned:
- **Environment Variable Management:** Two distinct API keys must be managed carefully - `LLM_API_KEY` for the LLM provider and `LMS_API_KEY` for the backend API. Mixing these up causes authentication failures.
- **Tool Description Clarity:** The LLM sometimes calls the wrong tool. Clear tool descriptions and explicit guidance in the system prompt are essential for correct tool selection.
- **Error Handling in query_api:** Robust error handling is needed for HTTP errors (401, 404, 500), connection errors, and timeouts. The implementation catches `urllib.error.HTTPError` separately to extract status codes.
- **Benchmark Iteration:** Some questions require multiple tool calls (e.g., query API for error, then read source to find bug). The system prompt should guide the LLM to chain tools appropriately.
