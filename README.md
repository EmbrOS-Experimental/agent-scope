<div align="center">

# 🔭 AgentScope

**DevTools for Coding Agents — Replay, Debug, Compare**

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-brightgreen.svg)](https://python.org)
[![Tests](https://img.shields.io/badge/tests-56%2F56%E2%9C%93-success.svg)](tests/)
[![EmbrOS](https://img.shields.io/badge/built%20by-embros.xyz-orange.svg)](https://embros.xyz)

*Your AI agent made a $47 mistake. Where did it go wrong?*

[Features](#features) • [Quick Start](#quick-start) • [CLI Usage](#cli-usage) • [SDK](#sdk) • [Adapters](#adapters) • [Self-Host](#self-host)

</div>

---

## The Problem

You gave your coding agent a task. It ran for 12 minutes, burned through 50K tokens, and produced **broken code**. 

Langfuse shows you the LLM traces. SWE-agent gives you a trajectory file. But **none of them answer the only question that matters:**

> 🤔 *"Why did it take THAT action at step 7?"*

## The Solution

AgentScope is the **time-travel debugger for coding agents**. It captures every LLM call, tool invocation, file diff, shell command, and test result — then lets you scrub through the entire run like a video.

```bash
# Install
pip install agentscope

# Capture any agent run
agentscope record -- aider --model claude-sonnet-4

# Replay and debug
agentscope show <run-id>

# Compare good vs bad run
agentscope compare <run-1> <run-2>
```

<div align="center">

### 🎬 See what your agent actually did
### 🔍 Find the exact step where it went wrong
### 📊 Compare two runs side-by-side
### 💰 Track tokens, cost, and duration

</div>

## Features

| Feature | Description |
|---------|-------------|
| 🎬 **Time-travel replay** | Scrub forward/backward through every agent action |
| 🔧 **Tool call inspector** | See every tool invocation with args, results, timing |
| 📝 **File diff viewer** | Track every file change with line-level diffs |
| 🧪 **Test result capture** | Record pass/fail for every test run |
| 💰 **Token & cost tracking** | Know exactly how much each run costs |
| 🔐 **Secret redaction** | Automatic detection and redaction of API keys, tokens, passwords |
| 🔀 **Git state snapshots** | Capture branch, commit, dirty state at each step |
| ✅ **Approval checkpoints** | Log human-in-the-loop approval events |
| 🔄 **Side-by-side compare** | Compare any two runs to find regressions |
| 📦 **Cross-platform** | Windows, macOS, Linux — works everywhere |

## Quick Start

### 1. Install

```bash
pip install agentscope
```

### 2. Use as a Python SDK

```python
from agentscope import AgentEmitter

emitter = AgentEmitter()
session = emitter.start_session(
    title="Fix auth bug #42",
    agent_type="aider",
    model="claude-sonnet-4"
)

# Agent analyzes the problem
session.add_llm_call(
    model="claude-sonnet-4",
    prompt="Analyze the auth bug",
    response="The token validation is missing a null check...",
    prompt_tokens=500, completion_tokens=200,
    cost_usd=0.015
)

# Agent runs a shell command
session.add_shell_command("cat src/auth.py", exit_code=0)

# Agent edits a file
session.add_file_diff("src/auth.py", "modified", lines_added=1, lines_removed=1)

# Agent runs tests
session.add_test_result("test_validate_token", passed=True, duration_ms=120)

# Done!
run = session.end("completed")
print(f"Run complete: {run.summary.total_events} events, ${run.summary.total_cost_usd:.4f}")
```

### 3. Use as a CLI

```bash
# List all captured runs
agentscope list

# Show detailed timeline of a run
agentscope show <run-id>

# Compare two runs
agentscope compare <run-1> <run-2>

# Export run as JSON
agentscope export <run-id>

# Check storage info
agentscope info
```

## CLI Usage

```
Usage: agentscope [OPTIONS] COMMAND [ARGS]...

  AgentScope — DevTools for coding agents.
  Replay, debug, and compare AI agent runs.

Commands:
  show       Show details of a captured run
  list       List captured runs
  export     Export a run as JSON
  compare    Compare two runs side-by-side
  delete     Delete a captured run
  prune      Prune old runs
  info       Show storage info
```

## Adapters

AgentScope ships with adapters for popular coding agents:

| Adapter | Status | Description |
|---------|--------|-------------|
| **Aider** | ✅ Ready | Parse Aider CLI output into trace events |
| **Continue** | ✅ Ready | MCP interception for Continue IDE agent mode |
| **OpenHands** | 🔜 Planned | OpenHands platform integration |
| **LangGraph** | 🔜 Planned | LangGraph workflow tracing |

Create your own adapter in ~50 lines of code:

```python
from agentscope.adapters import BaseAdapter

class MyAgentAdapter(BaseAdapter):
    def on_tool_call(self, name, args):
        self.session.add_tool_call(name, args)
    
    def on_llm_response(self, model, prompt, response):
        self.session.add_llm_call(model, prompt, response)
```

## Architecture

```
Agent SDK Shim → Trace Events → AgentScope Store → Replay UI
                                          ↓
                                    Redaction Pipeline
                                          ↓
                                   Cross-Platform Storage
                                   (Win / macOS / Linux)
```

**Stack:**
- **Python SDK** — Pydantic models, Click CLI, Rich output
- **Storage** — Filesystem (JSON/JSONL), cross-platform paths
- **Redaction** — Regex-based secret detection (API keys, tokens, passwords)
- **Adapters** — Pluggable shim system for any coding agent

## Self-Host & Team Mode

Coming in v0.2:
- Docker Compose stack with Postgres backend
- Web-based replay UI with timeline scrubber
- Team collaboration and run sharing
- SSO and access controls

## Built By

AgentScope is built by the team behind [EmbrOS](https://embros.xyz) — the AI Builder Operating System.

We built AgentScope because we needed it ourselves. Every day we watch AI agents build software, and every day we ask: *"What did it actually do?"*

Now you can answer that question too.

## License

Apache-2.0 — free to use, modify, and distribute.

## Contributing

PRs welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

<div align="center">

**Star this repo if it helped you debug your agent ⭐**

[🐦 Twitter](https://x.com/embOS_ai) • [💬 Discord](https://discord.gg/FZsWkYpM9b) • [🌐 embros.xyz](https://embros.xyz)

</div>

---

🐦 Follow on X: [@probert_mihai](https://x.com/probert_mihai)
