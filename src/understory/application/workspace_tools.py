"""Workspace-backed tools for the agent loop.

Each class wraps a ``Workspace`` and implements the ``Tool`` protocol so the
agent runner can call them by name.  This module imports only from
``understory.domain`` — no I/O of its own.
"""

from __future__ import annotations

from collections.abc import Mapping

from understory.domain.chat import Schema
from understory.domain.tool import Tool, ToolError
from understory.domain.workspace import Workspace


class ReadTool(Tool):
    """Read the contents of a workspace file.  Args: path."""

    name = "read"
    description = "read(path): return the contents of a file"
    parameters: Schema = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    }

    def __init__(self, workspace: Workspace) -> None:
        self._ws = workspace

    def run(self, args: Mapping[str, str]) -> str:
        if "path" not in args:
            raise ToolError("read requires 'path'")
        return self._ws.read(args["path"])


class WriteTool(Tool):
    """Write content to a workspace file.  Args: path, content."""

    name = "write"
    description = "write(path, content): write content to a file, creating it if needed"
    parameters: Schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["path", "content"],
    }

    def __init__(self, workspace: Workspace) -> None:
        self._ws = workspace

    def run(self, args: Mapping[str, str]) -> str:
        if "path" not in args:
            raise ToolError("write requires 'path'")
        if "content" not in args:
            raise ToolError("write requires 'content'")
        self._ws.write(args["path"], args["content"])
        return f"wrote {args['path']}"


class EditTool(Tool):
    """Replace a unique substring in a workspace file.  Args: path, old, new."""

    name = "edit"
    description = "edit(path, old, new): replace a unique occurrence of old with new in a file"
    parameters: Schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "old": {"type": "string"},
            "new": {"type": "string"},
        },
        "required": ["path", "old", "new"],
    }

    def __init__(self, workspace: Workspace) -> None:
        self._ws = workspace

    def run(self, args: Mapping[str, str]) -> str:
        for key in ("path", "old", "new"):
            if key not in args:
                raise ToolError(f"edit requires '{key}'")
        self._ws.edit(args["path"], args["old"], args["new"])
        return f"edited {args['path']}"


class ListDirTool(Tool):
    """List the entries of a workspace directory.  Args: path (optional, default '.')."""

    name = "list_dir"
    description = "list_dir(path?): list entries directly under path (default '.')"
    parameters: Schema = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
    }

    def __init__(self, workspace: Workspace) -> None:
        self._ws = workspace

    def run(self, args: Mapping[str, str]) -> str:
        path = args.get("path", ".")
        entries = self._ws.list_dir(path)
        return "\n".join(entries)
