"""Agent adapters — shim wrappers for popular coding agents."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Optional

import logging

from agentscope.core.emitter import AgentScopeSession

logger = logging.getLogger(__name__)


class AiderAdapter:
    """Adapter that captures Aider CLI runs via output parsing."""

    def __init__(self, session: AgentScopeSession):
        self.session = session

    def wrap_command(self, args: list[str]) -> list[str]:
        """Wrap an aider command to enable verbose output for capture."""
        return ["aider", "--verbose", "--no-git", *args]

    def parse_and_record(self, line: str) -> None:
        """Parse a line of Aider output and record events."""
        line = line.strip()
        if not line:
            return

        # Detect model info
        if "Model:" in line:
            parts = line.split("Model:")[-1].strip()
            self.session.run.model = parts
            return

        # Detect shell commands
        if line.startswith("$ ") or line.startswith("```bash"):
            cmd = line.lstrip("$ ").strip("`")
            self.session.add_shell_command(cmd)
            return

        # Detect file edits
        if "Applied edit to" in line:
            file_path = line.split("Applied edit to")[-1].strip()
            self.session.add_file_diff(file_path, "modified")

        if "Added" in line and ".py" in line:
            file_path = line.split("Added")[-1].strip()
            self.session.add_file_diff(file_path, "added")

        # Detect LLM responses (main chat output)
        if line.startswith(">") or line.startswith("Assistant:"):
            content = line.lstrip("> ").lstrip("Assistant:").strip()
            self.session.add_llm_call(
                model=self.session.run.model,
                prompt="",
                response=content,
            )

        # Detect errors
        if "Error" in line or "Traceback" in line:
            self.session.add_error(line)

        # Detect test results
        if "passed" in line.lower() and ("failed" in line.lower() or "error" in line.lower()):
            self.session.add_test_result("suite", "passed" in line.lower() and "failed" not in line.lower())


class ContinueAdapter:
    """Adapter for Continue IDE agent mode via MCP interception."""

    def __init__(self, session: AgentScopeSession):
        self.session = session

    def on_tool_call(self, tool_name: str, arguments: dict[str, Any]) -> None:
        """Called when the agent makes a tool call."""
        self.session.add_tool_call(tool_name, arguments)

    def on_tool_result(self, tool_name: str, result: str, error: Optional[str] = None) -> None:
        """Called when a tool call returns."""
        # Update the last tool call with result
        if self.session.run.events:
            last = self.session.run.events[-1]
            if last.event_type.value == "tool_call" and last.tool_call:
                last.tool_call.result = result
                last.tool_call.error = error

    def on_llm_response(
        self,
        model: str,
        prompt: str,
        response: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> None:
        """Called when the LLM responds."""
        self.session.add_llm_call(
            model=model,
            prompt=prompt,
            response=response,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )


def record_subprocess(
    session: AgentScopeSession,
    command: list[str],
    cwd: str = ".",
    timeout: Optional[float] = None,
) -> subprocess.CompletedProcess:
    """Run a subprocess and capture its output as trace events."""
    session.add_shell_command(" ".join(command))

    start = time.monotonic()
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration = (time.monotonic() - start) * 1000

        session.add_shell_command(
            " ".join(command),
            output=result.stdout[-5000:] if result.stdout else None,
            exit_code=result.returncode,
            duration_ms=duration,
        )

        if result.returncode != 0:
            session.add_error(
                f"Command failed with exit code {result.returncode}",
                context=result.stderr[-1000:] if result.stderr else None,
            )

        return result

    except subprocess.TimeoutExpired:
        session.add_error(f"Command timed out after {timeout}s")
        raise
    except FileNotFoundError:
        session.add_error(f"Command not found: {command[0]}")
        raise
