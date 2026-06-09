# AgentScope — Vision

## Elevator Pitch
Open-source "DevTools for coding agents" that lets developers replay every LLM step, tool call, file diff and shell command as a **time-travel debugger**.

## The Problem
Langfuse and Phoenix cover generic LLM tracing. SWE-agent emits trajectory files. Playwright Trace Viewer proves step-through replay works. But none of these give you a **repo-aware** debugger for coding agents that fuses traces with git diffs, shell history, tool approvals, branch state, and test artefacts.

## User Stories
1. A developer wraps a Continue/OpenHands/Aider/LangGraph workflow with a tiny SDK or CLI shim
2. AgentScope captures the full run: prompts, responses, tool arguments, diffs, test runs, token/cost usage, approvals, rollbacks
3. When the agent does something stupid, the developer scrubs backwards, compares two runs side by side, and answers: **why did it take that action?**

## Core Features
- Full-run capture: LLM requests/responses, tool calls with arguments, file diffs, shell commands
- Git-state snapshots: branch, commit hash, working tree state at each step
- Test artefact capture: pass/fail, stdout, stderr, timing
- Token + cost tracking per run
- Approval/rollback event logging
- Side-by-side run comparison (good run vs bad run)
- Redaction pipeline for secrets
- Local-first storage (SQLite + files), team mode (Postgres/S3)

## What Makes It Different
- **Repo-aware**: ties traces to git diffs, branch state, file context — not just LLM spans
- **Time-travel debugger**: scrub forward/backward through an agent run like a video
- **Adapter ecosystem**: works with Continue, OpenHands, Aider, LangGraph via shims
- Built on OTel/OpenInference standards — not a custom format

## Virality Hooks
- "Good run vs bad run" side-by-side clips
- "This $47 agent mistake traced in 30 seconds"
- Thread: "I debugged an agent's bad architecture decision using AgentScope"

## License
Apache-2.0

## Monetization
Hosted retention, team collaboration, SSO, private artefact storage, long-term analytics, enterprise adapters
