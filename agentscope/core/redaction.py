"""Secret redaction pipeline for trace events."""

from __future__ import annotations

import re
from typing import Any, Optional

from agentscope.core.models import TraceEvent, EventType


# Common secret patterns
SECRET_PATTERNS: list[tuple[re.Pattern, str]] = [
    # API keys
    (re.compile(r'(sk-[a-zA-Z0-9]{20,})'), 'sk-***'),
    (re.compile(r'(ghp_[a-zA-Z0-9]{36})'), 'ghp_***'),
    (re.compile(r'(gho_[a-zA-Z0-9]{36})'), 'gho_***'),
    (re.compile(r'(ghu_[a-zA-Z0-9]{36})'), 'ghu_***'),
    (re.compile(r'(ghs_[a-zA-Z0-9]{36})'), 'ghs_***'),
    (re.compile(r'(ghr_[a-zA-Z0-9]{36})'), 'ghr_***'),
    # Generic key=value patterns
    (re.compile(r'((?:api[_-]?key|token|secret|password|passwd)\s*[=:]\s*)["\']?[^\s"\']+["\']?', re.IGNORECASE), r'\1***'),
    # Bearer tokens
    (re.compile(r'(Bearer\s+)[a-zA-Z0-9_\-\.]+', re.IGNORECASE), r'\1***'),
    # AWS keys
    (re.compile(r'(AKIA[0-9A-Z]{16})'), 'AKIA***'),
    # Private keys
    (re.compile(r'(-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----)[\s\S]*?(-----END (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----)'), r'\1\n***\n\2'),
    # Connection strings with passwords
    (re.compile(r'(://[^:]+:)[^@]+(@)'), r'\1***\2'),
]

# Keys in dicts that should always be redacted
SENSITIVE_KEYS = {
    'api_key', 'apikey', 'token', 'secret', 'password', 'passwd',
    'access_token', 'refresh_token', 'private_key', 'secret_key',
    'authorization', 'auth_token', 'bearer', 'credentials',
}


class RedactionPipeline:
    """Redacts sensitive data from trace events."""

    def __init__(self, extra_patterns: Optional[list[tuple[str, str]]] = None):
        self.patterns = list(SECRET_PATTERNS)
        if extra_patterns:
            for pattern, replacement in extra_patterns:
                self.patterns.append((re.compile(pattern), replacement))

    def redact_text(self, text: str) -> str:
        """Apply all redaction patterns to a string."""
        result = text
        for pattern, replacement in self.patterns:
            result = pattern.sub(replacement, result)
        return result

    def redact_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Recursively redact sensitive values in a dict."""
        result = {}
        for key, value in data.items():
            if key.lower() in SENSITIVE_KEYS:
                result[key] = '***'
            elif isinstance(value, str):
                result[key] = self.redact_text(value)
            elif isinstance(value, dict):
                result[key] = self.redact_dict(value)
            elif isinstance(value, list):
                result[key] = self.redact_list(value)
            else:
                result[key] = value
        return result

    def redact_list(self, data: list[Any]) -> list[Any]:
        """Recursively redact sensitive values in a list."""
        result = []
        for item in data:
            if isinstance(item, str):
                result.append(self.redact_text(item))
            elif isinstance(item, dict):
                result.append(self.redact_dict(item))
            elif isinstance(item, list):
                result.append(self.redact_list(item))
            else:
                result.append(item)
        return result

    def redact_event(self, event: TraceEvent) -> TraceEvent:
        """Redact sensitive data from a trace event."""
        # Redact the data dict
        event.data = self.redact_dict(event.data)

        # Redact tool call arguments and results
        if event.tool_call:
            event.tool_call.arguments = self.redact_dict(event.tool_call.arguments)
            if event.tool_call.result:
                event.tool_call.result = self.redact_text(event.tool_call.result)

        # Redact error messages
        if event.error:
            event.error = self.redact_text(event.error)

        return event
