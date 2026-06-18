"""Build a structured TaskResult from an AgentResult + Verification."""

from __future__ import annotations

from understory.application.agent_runner import AgentResult
from understory.domain.trace import TaskResult
from understory.domain.verification import Verification


def format_result(
    agent_result: AgentResult,
    verification: Verification,
    session_id: str,
) -> TaskResult:
    """Combine agent output and verification into a structured result."""
    return TaskResult(
        status=agent_result.status,
        steps=agent_result.steps,
        session_id=session_id,
        output=agent_result.output,
        files_changed=tuple(verification.found_files),
        verification_status=verification.status,
        verification_summary=verification.summary,
    )
