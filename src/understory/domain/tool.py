"""Tool domain — a named capability the agent loop can invoke.

A Tool turns a parsed ``{"tool": name, "args": {...}}`` call into an
observation string. Tools validate their own args and raise ToolError on
bad input; the agent loop turns raised errors into observations.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from understory.domain.chat import Schema


class ToolError(Exception):
    """A tool was called with missing or invalid arguments."""


class Tool(Protocol):
    name: str
    description: str
    parameters: Schema

    def run(self, args: Mapping[str, str]) -> str:
        """Execute with string args, returning an observation."""
        ...
