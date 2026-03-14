# Agent Implementation Documentation

## 1. Overview
This document details the implementation of `agent.py`, a foundational CLI tool that connects to an LLM (OpenAI) to answer user questions. It serves as the base for future agentic capabilities involving tools and loops.

## 2. Architecture & Flow
The agent follows a linear pipeline:
`CLI Input` → `Argument Parsing` → `LLM API Call` → `JSON Formatting` → `Stdout Output`

### Key Constraints
- **Input**: Single string argument (the question).
- **Output**: Strictly valid JSON on `stdout`.
- **Debug/Errors**: All non-JSON output (logs, errors, usage) goes to `stderr`.
- **Timeout**: Maximum 60 seconds for the LLM response.
- **Exit Codes**: `0` for success, `1` for failure.

## 3. Step-by-Step Implementation Logic

### Step 1: Imports and Setup
The script imports necessary standard libraries for system interaction, JSON handling, and error management, along with the OpenAI SDK.
- `sys`: For command-line arguments (`argv`) and stream control (`stdout`, `stderr`).
- `json`: To serialize the final response dictionary.
- `openai`: To initialize the client and communicate with the LLM.

### Step 2: Argument Validation
Upon execution, the script checks `sys.argv`:
- If fewer than 2 arguments are present (script name + question), it prints a usage message to `stderr` and exits with code `1`.
- If valid, the question is extracted from `sys.argv[1]`.

### Step 3: LLM Client Initialization
An `OpenAI` client instance is created.
- **Authentication**: Relies on the `OPENAI_API_KEY` environment variable.
- **Model Selection**: Configured to use `gpt-4o` (configurable constant).

### Step 4: Constructing the API Request
The script calls `client.chat.completions.create()` with specific parameters:
- **Messages**: A list containing:
  1. A `system` message defining the persona ("helpful assistant", "answer concisely").
  2. A `user` message containing the input question.
- **Max Tokens**: Limited to 500 to ensure brevity and speed.
- **Timeout**: Set to `60` seconds to enforce the response time rule.

### Step 5: Processing the Response
- The script extracts the content from the first choice in the response (`response.choices[0].message.content`).
- Whitespace is stripped to ensure clean output.

### Step 6: Formatting the Output
A Python dictionary is constructed to match the required schema:
```python
result = {
    "answer": "<extracted_text>",
    "tool_calls": []  # Reserved for Task 2
}
