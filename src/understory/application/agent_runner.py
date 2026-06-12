"""Agent loop — let a model drive tools to complete a task.

Protocol (text-based, model-agnostic):

The runner sends a system prompt describing the task and the available
tools, then loops. Each turn the model must reply with a SINGLE JSON object:

- a tool call:   {"tool": "<name>", "args": {"<k>": "<v>", ...}}
- a final answer:{"done": "<answer>"}

For a tool call, the runner executes the tool and appends an observation
(``Observation: <result>`` or ``Error: <reason>``) as the next user message,
then continues. A malformed reply or unknown tool yields an error
observation nudging the model back to the JSON format; it still counts as a
step. The loop ends when the model returns ``done`` (status "done") or when
``max_steps`` is reached (status "max_steps").
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

from understory.domain.chat import ChatProvider, Message, ModelName
from understory.domain.tool import Tool, ToolError
from understory.domain.trace import Step
from understory.domain.workspace import WorkspaceError


@dataclass(frozen=True, slots=True)
class AgentResult:
    status: Literal["done", "max_steps"]
    output: str
    steps: int
    transcript: Sequence[Step] = field(default_factory=tuple)


def action_schema(tool_names: Sequence[str]) -> dict[str, object]:
    """Provider-neutral JSON schema for one agent action.

    The reply must be exactly one of a tool call ``{"tool", "args"}`` or a
    final ``{"done"}``. Passed to the provider for constrained decoding.
    """
    return {
        "type": "object",
        "oneOf": [
            {
                "type": "object",
                "properties": {
                    "tool": {"type": "string", "enum": list(tool_names)},
                    "args": {"type": "object"},
                },
                "required": ["tool", "args"],
            },
            {
                "type": "object",
                "properties": {"done": {"type": "string"}},
                "required": ["done"],
            },
        ],
    }


class AgentRunner:
    def __init__(
        self,
        provider: ChatProvider,
        tools: Sequence[Tool],
        max_steps: int = 10,
    ) -> None:
        self._provider = provider
        self._tools = {t.name: t for t in tools}
        self._max_steps = max_steps

    async def run(self, model: ModelName, task: str) -> AgentResult:
        """Drive the model/tool loop until done or max_steps is reached."""
        tool_lines = "\n".join(
            f"{t.name}({t.description.split(':', 1)[-1].strip()})"
            if ":" in t.description
            else f"{t.name}: {t.description}"
            for t in self._tools.values()
        )
        system_content = (
            f"Task: {task}\n\n"
            f"Available tools:\n{tool_lines}\n\n"
            "Reply with a SINGLE JSON object — either "
            '{"tool": "<name>", "args": {"<k>": "<v>", ...}} '
            'to call a tool, or {"done": "<answer>"} when finished. '
            "No other text outside the JSON object."
        )

        messages: list[Message] = [
            Message("system", system_content),
            Message("user", task),
        ]

        schema = action_schema(list(self._tools))

        steps = 0
        last_text = ""
        transcript: list[Step] = []
        _FORMAT_ERROR = 'Error: reply with a single JSON object {"tool": ...} or {"done": ...}'

        while steps < self._max_steps:
            reply = await self._provider.complete(model, messages, schema=schema)
            messages.append(reply)
            last_text = reply.content
            index = steps
            steps += 1

            # Parse the reply.
            try:
                payload = json.loads(reply.content)
                if not isinstance(payload, dict):
                    raise TypeError("not a JSON object")
            except (json.JSONDecodeError, TypeError):
                messages.append(Message("user", _FORMAT_ERROR))
                transcript.append(Step(index, reply.content, "error", observation=_FORMAT_ERROR))
                continue

            # Done branch.
            if "done" in payload:
                transcript.append(Step(index, reply.content, "done"))
                return AgentResult("done", str(payload["done"]), steps, tuple(transcript))

            # Tool-call branch.
            if "tool" in payload:
                tool_name = payload["tool"]
                tool_args = payload.get("args", {})

                if (
                    not isinstance(tool_name, str)
                    or tool_name not in self._tools
                    or not isinstance(tool_args, dict)
                ):
                    messages.append(Message("user", _FORMAT_ERROR))
                    transcript.append(
                        Step(index, reply.content, "error", observation=_FORMAT_ERROR)
                    )
                    continue

                try:
                    result = self._tools[tool_name].run(tool_args)
                    observation = f"Observation: {result}"
                    messages.append(Message("user", observation))
                    transcript.append(
                        Step(
                            index,
                            reply.content,
                            "tool",
                            tool=tool_name,
                            args=tool_args,
                            observation=observation,
                        )
                    )
                except (ToolError, WorkspaceError) as exc:
                    observation = f"Error: {exc}"
                    messages.append(Message("user", observation))
                    transcript.append(
                        Step(
                            index,
                            reply.content,
                            "tool",
                            tool=tool_name,
                            args=tool_args,
                            observation=observation,
                        )
                    )
                continue

            # Neither "tool" nor "done" key present.
            messages.append(Message("user", _FORMAT_ERROR))
            transcript.append(Step(index, reply.content, "error", observation=_FORMAT_ERROR))

        return AgentResult("max_steps", last_text, self._max_steps, tuple(transcript))
