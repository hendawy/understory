"""Workspace domain — a filesystem confined to a single root directory.

Every path is relative to the workspace root. Operations that would resolve
outside the root (via ``..``, absolute paths, or symlinks) are rejected.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class WorkspaceError(Exception):
    """Base class for workspace failures."""


class PathEscape(WorkspaceError):
    """A path resolved outside the workspace root."""


class WorkspaceFileNotFound(WorkspaceError):
    """A read/edit targeted a file that does not exist."""


class EditConflict(WorkspaceError):
    """An edit's ``old`` text was missing or not uniquely present."""


class Workspace(Protocol):
    """Confined filesystem. All paths are relative to the root."""

    def read(self, path: str) -> str:
        """Return file contents. Raises WorkspaceFileNotFound if absent."""
        ...

    def write(self, path: str, content: str) -> None:
        """Write content, creating parent dirs within the root as needed."""
        ...

    def edit(self, path: str, old: str, new: str) -> None:
        """Replace the unique occurrence of ``old`` with ``new``.

        Raises WorkspaceFileNotFound if the file is absent, EditConflict if
        ``old`` is missing or appears more than once.
        """
        ...

    def list_dir(self, path: str = ".") -> Sequence[str]:
        """Return entry names directly under ``path``."""
        ...
