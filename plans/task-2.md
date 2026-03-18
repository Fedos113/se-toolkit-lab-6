# Task 2: The Documentation Agent - Implementation Plan

## Overview

This plan describes how to implement the agentic loop with `read_file` and `list_files` tools, enabling the agent to navigate and read the project wiki to answer questions.

## 1. Tool Schema Definitions

### `read_file` Tool

**Purpose**: Read the contents of a file from the project repository.

**Schema** (OpenAI function-calling format):
```json
{
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
```

**Implementation**:
- Accept a `path` parameter (relative to project root)
- Validate the path does not contain `..` traversal
- Resolve to absolute path and verify it's within project directory
- Read file contents using Python's `open()`
- Return contents as string, or error message if file doesn't exist

### `list_files` Tool

**Purpose**: List files and directories at a given path.

**Schema**:
```json
{
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
```

**Implementation**:
- Accept a `path` parameter (relative to project root)
- Validate the path does not contain `..` traversal
- Resolve to absolute path and verify it's within project directory
- Use `os.listdir()` to get entries
- Return newline-separated string of entries

## 2. Path Security Strategy

**Goal**: Prevent directory traversal attacks (e.g., `../../../etc/passwd`).

**Implementation**:
1. Define `PROJECT_ROOT` as the absolute path to the project directory.
2. For any tool receiving a `path` parameter:
   - Reject paths containing `..`
   - Reject absolute paths (must be relative)
   - Resolve the full path: `os.path.join(PROJECT_ROOT, path)`
   - Use `os.path.realpath()` to resolve symlinks
   - Verify the resolved path starts with `PROJECT_ROOT`
3. Return an error message if security check fails.

## 3. Agentic Loop Implementation

### Loop Flow

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

### Implementation Steps

1. **Initialize messages list** with system prompt and user question.
2. **Loop** (max 10 iterations):
   - Call LLM with `tools` parameter containing both tool schemas.
   - Parse response:
     - If `tool_calls` present:
       - Execute each tool call
       - Store results in `tool_calls` output list
       - Append tool results as `{"role": "tool", "tool_call_id": ..., "content": ...}`
       - Continue loop
     - If no `tool_calls`:
       - Extract final answer from message content
       - Extract source (wiki file reference) from answer or tool results
       - Break loop
3. **Output JSON** with `answer`, `source`, and `tool_calls` fields.

### System Prompt Strategy

The system prompt should instruct the LLM to:
- Use `list_files` to discover wiki files when asked about documentation structure.
- Use `read_file` to read specific wiki files to find answers.
- Always include the source reference (file path + section anchor) in the answer.
- Be concise and direct.

Example system prompt:
```
You are a documentation assistant. You have access to two tools:
- list_files: List files in a directory
- read_file: Read contents of a file

When answering questions about the project:
1. Use list_files to discover what wiki files exist
2. Use read_file to read relevant files and find answers
3. Always cite your source as "wiki/filename.md#section-anchor"
4. Answer concisely

Do not make up information. Only answer based on what you read from files.
```

## 4. Output JSON Structure

```json
{
  "answer": "The answer extracted from wiki content",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git-workflow.md\n..."
    },
    {
      "tool": "read_file",
      "args": {"path": "wiki/git-workflow.md"},
      "result": "...file contents..."
    }
  ]
}
```

## 5. Error Handling

| Error Case | Handling |
|------------|----------|
| File not found | Return error message as tool result |
| Path traversal attempt | Return security error message |
| LLM API failure | Exit with error code, message to stderr |
| Max iterations reached | Use whatever answer is available |

## 6. Testing Strategy

Add 2 regression tests to `test_agent.py`:

1. **Test merge conflict question**:
   - Question: "How do you resolve a merge conflict?"
   - Expected: `read_file` in tool_calls, `wiki/git-workflow.md` in source

2. **Test wiki listing question**:
   - Question: "What files are in the wiki?"
   - Expected: `list_files` in tool_calls

## 7. Implementation Order

1. Create this plan file (plans/task-2.md)
2. Define tool functions (`read_file`, `list_files`) with security checks
3. Define tool schemas for LLM function calling
4. Implement agentic loop with max 10 iterations
5. Update system prompt
6. Update JSON output to include `source` and populated `tool_calls`
7. Update AGENT.md documentation
8. Add regression tests
9. Run tests and verify
