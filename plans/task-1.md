# Task 1: Agent Architecture and LLM Configuration Plan

## 1. LLM Provider and Model Selection
- **Provider**: Self-hosted or API-accessible Qwen (Alibaba Cloud).
- **Model**: `Qwen2.5-Coder-32B-Instruct` (or the highest parameter count available within resource constraints, e.g., `Qwen2.5-72B-Instruct` if latency permits).
  - *Rationale*: The "Coder" variant is optimized for code generation, debugging, and understanding complex repository structures, aligning with the requirement to implement efficient algorithms (e.g., k-d trees, divide-and-conquer) in C++.
  - *Context Window*: Utilize the model's extended context window (up to 128k tokens) to ingest entire project files and documentation for coherent multi-file editing.

## 2. Agent Structure
The agent will follow a **ReAct (Reason + Act)** loop enhanced with **Tool Use** capabilities.

### **Core Components**
1.  **Orchestrator (Brain)**:
    -   Receives user prompts.
    -   Decomposes high-level tasks into sub-tasks (e.g., "Implement k-d tree" → "Define Node struct" → "Implement Insert" → "Implement Search").
    -   Maintains conversation history and short-term memory.

2.  **Memory Module**:
    -   **Short-term**: Current conversation context.
    -   **Long-term**: Vector store (e.g., FAISS or ChromaDB) indexing the codebase, previous commit messages, and `task-*.md` plans to ensure replicability and context awareness across sessions.

3.  **Tool Interface**:
    -   **File System Access**: Read/Write/Edit files within the project directory.
    -   **Shell Execution**: Run compilation (`g++`, `cmake`), testing scripts, and git commands.
    -   **Search**: Grep/Regex search across the codebase for symbol definitions.

### **Workflow Loop**
1.  **Observation**: Analyze current state (file contents, error logs, user request).
2.  **Reasoning**: Formulate a step-by-step plan based on the observation.
3.  **Action**: Select a tool (e.g., `write_file`, `run_command`) and execute.
4.  **Verification**: Parse tool output (success/failure). If failure, analyze error and retry with corrected logic.
5.  **Response**: Summarize changes made and update `task-*.md` with progress.

## 3. Implementation Constraints & Standards
- **Language**: C++17/20 standard compliance.
- **Style**: Formal, concise, no contractions in comments/documentation.
- **Documentation**: All public methods must include Doxygen-style comments.
- **Replicability**: Every agent action must be logged to ensure the process can be reproduced manually if needed.
- **Output Format**: Code blocks must be strictly formatted; no conversational filler in code generation steps.

## 4. Next Steps
- Initialize the Python environment for the agent framework (e.g., LangChain or LlamaIndex).
- Configure the Qwen API endpoint or local inference server (vLLM/Ollama).
- Implement the File System and Shell tools.
- Execute the first iteration: Create the project skeleton and initial C++ class templates.
