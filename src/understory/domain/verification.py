"""Post-run outcome verification.

After the agent loop finishes, check that the work it claimed to do
actually happened. The model can say "done" without having written
anything — this module catches that.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from understory.domain.trace import Step
from understory.domain.workspace import Workspace, WorkspaceFileNotFound


VerificationStatus = Literal["pass", "fail", "empty"]


@dataclass(frozen=True, slots=True)
class Verification:
    status: VerificationStatus
    expected_files: Sequence[str]
    found_files: Sequence[str]
    missing_files: Sequence[str]

    @property
    def summary(self) -> str:
        if self.status == "empty":
            return "model never called write or edit — no files expected"
        if self.status == "pass":
            return f"verified {len(self.found_files)} file(s)"
        return (
            f"{len(self.missing_files)} file(s) missing: "
            + ", ".join(self.missing_files)
        )


def _extract_written_paths(steps: Sequence[Step]) -> list[str]:
    """Extract file paths the model attempted to write or edit."""
    paths: list[str] = []
    for step in steps:
        if step.kind != "tool" or step.tool not in ("write", "edit"):
            continue
        if step.observation and step.observation.startswith("Error:"):
            continue
        if step.args and "path" in step.args:
            paths.append(step.args["path"])
    return paths


def verify_outcome(steps: Sequence[Step], workspace: Workspace) -> Verification:
    expected = _extract_written_paths(steps)

    if not expected:
        return Verification(
            status="empty",
            expected_files=(),
            found_files=(),
            missing_files=(),
        )

    found: list[str] = []
    missing: list[str] = []
    for path in expected:
        try:
            workspace.read(path)
            found.append(path)
        except WorkspaceFileNotFound:
            missing.append(path)

    status: VerificationStatus = "pass" if not missing else "fail"
    return Verification(
        status=status,
        expected_files=tuple(expected),
        found_files=tuple(found),
        missing_files=tuple(missing),
    )
