"""LocalFilesystemWorkspace — a Workspace confined to a single root directory."""

from __future__ import annotations

import pathlib
from collections.abc import Sequence

from understory.domain.workspace import (
    EditConflict,
    PathEscape,
    Workspace,
    WorkspaceFileNotFound,
)


class LocalFilesystemWorkspace(Workspace):
    """Workspace backed by the local filesystem, confined to *root*."""

    def __init__(self, root: pathlib.Path) -> None:
        self._root = root.resolve()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_and_check(self, path: str) -> pathlib.Path:
        """Return the absolute path for *path*, raising PathEscape if it
        resolves outside the root (including via symlinks)."""
        raw = pathlib.Path(path)

        # Reject absolute paths that sit outside the root up front.
        if raw.is_absolute():
            candidate = raw.resolve()
            self._assert_inside(candidate)
            return candidate

        # Build the joined path without resolving so we can walk up the chain.
        joined = self._root / raw

        # For the confinement check we need to follow symlinks on whatever
        # portion of the path actually exists, then append the remaining
        # non-existent tail.  Path.resolve() does this correctly even when
        # the target does not exist (Python 3.6+ strict=False default).
        resolved = joined.resolve()
        self._assert_inside(resolved)
        return resolved

    def _assert_inside(self, resolved: pathlib.Path) -> None:
        """Raise PathEscape unless *resolved* is the root or a descendant."""
        try:
            resolved.relative_to(self._root)
        except ValueError:
            raise PathEscape(f"{resolved} is outside workspace root {self._root}") from None

    # ------------------------------------------------------------------
    # Protocol implementation
    # ------------------------------------------------------------------

    def read(self, path: str) -> str:
        """Return file contents. Raises WorkspaceFileNotFound if absent."""
        target = self._resolve_and_check(path)
        try:
            return target.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise WorkspaceFileNotFound(path) from None

    def write(self, path: str, content: str) -> None:
        """Write *content*, creating parent dirs within the root as needed."""
        target = self._resolve_and_check(path)
        # Ensure the parent directory exists (and is inside root).
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def edit(self, path: str, old: str, new: str) -> None:
        """Replace the unique occurrence of *old* with *new*.

        Raises WorkspaceFileNotFound if the file is absent, EditConflict if
        *old* is missing or appears more than once.
        """
        target = self._resolve_and_check(path)
        try:
            text = target.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise WorkspaceFileNotFound(path) from None

        count = text.count(old)
        if count == 0:
            raise EditConflict(f"{old!r} not found in {path}")
        if count > 1:
            raise EditConflict(f"{old!r} appears {count} times in {path}; must be unique")

        target.write_text(text.replace(old, new, 1), encoding="utf-8")

    def list_dir(self, path: str = ".") -> Sequence[str]:
        """Return entry names directly under *path*."""
        target = self._resolve_and_check(path)
        return [entry.name for entry in target.iterdir()]
