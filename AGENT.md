# Agent Implementation Documentation

## 1. Overview

This document details the implementation of `agent.py`, a CLI tool that connects to an LLM via an OpenAI-compatible API to answer user questions using an **agentic loop** with tool calls. The agent can navigate and read the project wiki using `read_file` and `list_files` tools, and query the backend API using `query_api`.

## 2. Architecture & Flow

### Agentic Loop

The agent implements a ReAct-style loop:

```
Question → LLM (with tool schemas) → tool_calls?
    │                                   │
    │ no                                │ yes
    │                                   ▼
    │                           Execute tool(s)
    │                                   │
    │                                   ▼
    │                           Append tool results as "tool" role
    │                                   │
    │                                   ▼
    └─────────────────────────── Back to LLM (max 10 iterations)
                                        │
                                        ▼
                                   Final answer → JSON output
```

### Key Components

1. **Tool Functions**: `read_file()`, `list_files()`, and `query_api()` with proper error handling.
2. **Tool Schemas**: OpenAI function-calling format for LLM.
3. **Agentic Loop**: Iterative LLM calls with tool execution (max 10 iterations).
4. **System Prompt**: Instructs LLM to use tools and provides guidance on tool selection.

### Key Constraints

- **Input**: Single string argument (the question).
- **Output**: Strictly valid JSON on `stdout` with `answer`, `source`, and `tool_calls` fields.
- **Debug/Errors**: All non-JSON output (logs, errors, usage) goes to `stderr`.
- **Timeout**: Maximum 60 seconds per LLM call, 30 seconds per API call.
- **Max Iterations**: 10 tool call iterations per question.
- **Exit Codes**: `0` for success, `1` for failure.

### LLM Provider

The agent uses **Qwen Code API** deployed on a VM via [`qwen-code-oai-proxy`](https://github.com/inno-se-toolkit/qwen-code-oai-proxy). This proxy exposes Qwen Code through an OpenAI-compatible API.

| Model              | Tool calling | Notes                                        |
| ------------------ | ------------ | -------------------------------------------- |
| `qwen3-coder-plus` | Strong       | Recommended, default                         |
| `coder-model`      | Strong       | Qwen 3.5 Plus                                |

## 3. Configuration

The agent reads configuration from environment variables. The `.env.agent.secret` and `.env.docker.secret` files are local conveniences — the autochecker will inject its own values when evaluating.

| Variable             | Purpose                                                      | Source                          |
| -------------------- | ------------------------------------------------------------ | ------------------------------- |
| `LLM_API_KEY`        | LLM provider API key                                         | `.env.agent.secret`             |
| `LLM_API_BASE`       | LLM API endpoint URL                                         | `.env.agent.secret`             |
| `LLM_MODEL`          | Model name                                                   | `.env.agent.secret`             |
| `LMS_API_KEY`        | Backend API key for `query_api` auth                         | `.env.docker.secret`            |
| `AGENT_API_BASE_URL` | Base URL for `query_api` (default: `http://localhost:42002`) | Optional, defaults to localhost |

> **Note:** Two distinct keys: `LMS_API_KEY` (in `.env.docker.secret`) protects your backend endpoints. `LLM_API_KEY` (in `.env.agent.secret`) authenticates with your LLM provider. Don't mix them up.

## 4. Tools

### `read_file`

Read a file from the project repository.

**Parameters**:
- `path` (string, required): Relative path from project root (e.g., `wiki/git-workflow.md`).

**Returns**: File contents as a string, or an error message if the file doesn't exist.

**Security**:
- Rejects paths containing `..` (directory traversal).
- Rejects absolute paths.
- Verifies resolved path is within project directory.

**Example**:
```python
read_file("wiki/git-workflow.md")
# Returns: "# Git workflow\n\n..."
```

### `list_files`

List files and directories at a given path.

**Parameters**:
- `path` (string, required): Relative directory path from project root (e.g., `wiki`).

**Returns**: Newline-separated listing of entries, or an error message.

**Security**:
- Rejects paths containing `..` (directory traversal).
- Rejects absolute paths.
- Verifies resolved path is within project directory.

**Example**:
```python
list_files("wiki")
# Returns: "api.md\narchitectural-views.md\n..."
```

### `query_api` (Task 3)

Send an HTTP request to the backend API.

**Parameters**:
- `method` (string, required): HTTP method (GET, POST, PUT, DELETE, etc.)
- `path` (string, required): API path (e.g., `/items/`, `/analytics/completion-rate`)
- `body` (string, optional): JSON request body for POST/PUT requests

**Returns**: JSON string with `status_code` and `body` fields.

**Authentication**: Uses `LMS_API_KEY` from environment variables with Bearer token authentication.

**Example**:
```python
query_api("GET", "/items/")
# Returns: '{"status_code": 200, "body": "[...]"}'

query_api("GET", "/items/", body=None)
# Returns: '{"status_code": 401, "body": "{\"detail\": \"Unauthorized\"}"}'
```

### Path Security Implementation

Both file tools use `validate_path()` to ensure security:

1. Check for `..` in path (directory traversal attempt).
2. Check if path is absolute (must be relative).
3. Resolve full path: `PROJECT_ROOT / path`.
4. Verify resolved path starts with `PROJECT_ROOT`.

If any check fails, returns a security error message.

## 5. Tool Schemas (Function Calling)

Tools are registered with the LLM using OpenAI function-calling format:

```json
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
```

The LLM uses these schemas to decide which tool to call and with what arguments.

## 6. System Prompt Strategy

The system prompt instructs the LLM to use tools appropriately:

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
If you cannot find the answer, say so honestly.
```

### Tool Selection Decision Tree

The LLM decides which tool to use based on the question type:

1. **"What files exist..." / "List..."** → `list_files`
2. **"According to the wiki..." / "What does the code say..."** → `read_file`
3. **"How many..." / "Query the API..." / "What status code..."** → `query_api`
4. **"Explain the bug..."** → `query_api` first to see the error, then `read_file` to find the source

## 7. Step-by-Step Implementation Logic

### Step 1: Imports and Setup

The script imports standard libraries for system interaction, JSON handling, path manipulation, and environment management, along with the OpenAI SDK.

### Step 2: Constants

- `PROJECT_ROOT`: Absolute path to project directory (parent of `agent.py`).
- `MAX_ITERATIONS`: Maximum tool call iterations (10).

### Step 3: Environment Loading

The `load_env()` function reads `.env.agent.secret` if it exists, parsing key-value pairs and setting environment variables.

### Step 4: Path Security

The `validate_path()` function checks:
- No `..` in path.
- Path is not absolute.
- Resolved path is within `PROJECT_ROOT`.

### Step 5: Tool Functions

- `read_file(path)`: Validates path, reads file, returns contents or error.
- `list_files(path)`: Validates path, lists directory, returns entries or error.
- `query_api(method, path, body)`: Reads `LMS_API_KEY` and `AGENT_API_BASE_URL` from environment, sends HTTP request with Bearer auth, returns JSON with status_code and body.

### Step 6: Tool Schemas

`TOOL_SCHEMAS` defines all three tools in OpenAI function-calling format.

### Step 7: Agentic Loop

The `run_agentic_loop()` function:

1. Initializes messages with system prompt and user question.
2. Loops up to `MAX_ITERATIONS`:
   - Calls LLM with `tools=TOOL_SCHEMAS`.
   - If `tool_calls` present:
     - Executes each tool via `execute_tool_call()`.
     - Appends results as `{"role": "tool", ...}` messages.
     - Continues loop.
   - If no `tool_calls`:
     - Extracts answer and source.
     - Returns JSON result.
3. If max iterations reached, returns partial result.

### Step 8: Tool Execution

`execute_tool_call()`:
- Extracts tool name and arguments from tool call.
- Calls corresponding function from `TOOL_FUNCTIONS`.
- Returns dict with `tool`, `args`, and `result`.

### Step 9: Source Extraction

`extract_source_from_answer()`:
- Uses regex to find `wiki/*.md#anchor` patterns in answer.
- Falls back to extracting from tool call args.
- Defaults to `"wiki"` if no source found.

### Step 10: Main Function

1. Validates command-line arguments.
2. Loads environment.
3. Initializes OpenAI client.
4. Runs agentic loop.
5. Outputs JSON to stdout.

## 8. Output JSON Structure

```json
{
  "answer": "There are 8 items in the database.",
  "source": "wiki",
  "tool_calls": [
    {
      "tool": "query_api",
      "args": {"method": "GET", "path": "/items/"},
      "result": "{\"status_code\": 200, \"body\": \"[...]\"}"
    }
  ]
}
```

### Fields

- `answer` (string): The final answer from the LLM.
- `source` (string): Wiki section reference (e.g., `wiki/git-workflow.md#section`) or `wiki` for API queries.
- `tool_calls` (array): All tool calls made during the loop. Each entry has:
  - `tool`: Tool name (`read_file`, `list_files`, or `query_api`).
  - `args`: Arguments passed to the tool.
  - `result`: Tool output (file contents, directory listing, or API response).

## 9. Usage

### Basic Usage

```bash
# Copy and configure environment
cp .env.agent.example .env.agent.secret
# Edit .env.agent.secret with your LLM credentials

# Run the agent
uv run agent.py "How many items are in the database?"
```

### Expected Output

```json
{
  "answer": "There are 8 items in the database.",
  "source": "wiki",
  "tool_calls": [...]
}
```

### Debug Output (stderr)

```
Calling LLM: qwen3-coder-plus...
Iteration 1/10
Executing tool: query_api with args: {'method': 'GET', 'path': '/items/'}
Done.
```

## 10. Error Handling

| Error                          | Behavior                                           |
| ------------------------------ | -------------------------------------------------- |
| Missing command-line argument  | Prints usage to stderr, exits with code `1`        |
| Missing `LLM_API_KEY`          | Prints error to stderr, exits with code `1`        |
| Path traversal attempt         | Returns security error as tool result              |
| File not found                 | Returns error message as tool result               |
| API connection failure         | Returns error JSON with status_code: 0             |
| API timeout (>30 seconds)      | Returns error JSON with status_code: 0             |
| Max iterations reached         | Returns partial answer with tool results           |

## 11. Testing

To test the agent:

```bash
# Run a single question
uv run agent.py "What files are in the wiki?"

# Run the test suite
uv run python test_agent.py

# Run the evaluation benchmark
uv run run_eval.py
```

### Test Cases

1. **Merge conflict question**: `"How do you resolve a merge conflict?"`
   - Expects: `read_file` in tool_calls, `wiki/git-workflow.md` in source.

2. **Wiki listing question**: `"What files are in the wiki?"`
   - Expects: `list_files` in tool_calls.

3. **Framework question** (Task 3): `"What Python web framework does the backend use?"`
   - Expects: `read_file` in tool_calls, answer contains "FastAPI".

4. **Database count question** (Task 3): `"How many items are in the database?"`
   - Expects: `query_api` in tool_calls, answer contains a positive number.

### Test Verification

Tests verify:
- Valid JSON output.
- Presence of `answer`, `source`, and `tool_calls` fields.
- Correct tools are called for specific questions.
- Answer content matches expected keywords.

## 12. Lessons Learned (Task 3)

### Environment Variable Management

The biggest challenge in Task 3 was managing two distinct API keys:
- `LLM_API_KEY` for the LLM provider
- `LMS_API_KEY` for the backend API

Initially, I confused these two keys, which caused authentication failures. The solution was to clearly document the distinction in both the code comments and this AGENT.md file.

### Tool Description Clarity

The LLM sometimes called the wrong tool for a question. For example, it would try to `read_file` when asked about item counts. The fix was to improve the tool descriptions and add explicit guidance in the system prompt:

```
Tool selection guidance:
- Use list_files to discover what files exist in a directory
- Use read_file to read wiki documentation, source code, or configuration files
- Use query_api to query the running backend API for data (item counts, analytics, etc.)
  or to check API behavior (status codes, errors)
```

### Error Handling in query_api

The `query_api` tool needed robust error handling for:
- HTTP errors (401, 404, 500)
- Connection errors
- Timeouts

The implementation catches `urllib.error.HTTPError` separately to extract the status code and error body, and catches generic exceptions for network issues.

### Benchmark Iteration

Running `run_eval.py` revealed edge cases:
- Some questions require multiple tool calls (e.g., query API for error, then read source to find bug)
- The LLM sometimes needs explicit guidance to chain tools
- Answer phrasing matters for keyword matching

### Final Evaluation Score

After iteration, the agent passes all 10 local questions in `run_eval.py`. The key fixes were:
1. Clearer tool descriptions
2. Explicit tool selection guidance in system prompt
3. Robust error handling in `query_api`
4. Proper environment variable loading for both LLM and backend API keys
