"""Server-rendered HTML trace UI for inspecting recorded agent sessions."""

from __future__ import annotations

import html
from collections.abc import Callable

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response
from starlette.routing import Route

from understory.domain.trace import Session, Step, TraceStore

_STYLE = """
<style>
  body { font-family: system-ui, sans-serif; margin: 2rem; color: #111; }
  h1 { font-size: 1.4rem; margin-bottom: 1rem; }
  table { border-collapse: collapse; width: 100%; }
  th, td { border: 1px solid #ccc; padding: .4rem .6rem; text-align: left; }
  th { background: #f4f4f4; }
  tr:hover td { background: #fafafa; }
  .step { border: 1px solid #ddd; margin: .5rem 0; padding: .5rem; border-radius: 4px; }
  .kind-tool { border-left: 4px solid #2980b9; }
  .kind-done { border-left: 4px solid #27ae60; }
  .kind-error { border-left: 4px solid #e74c3c; }
  pre { white-space: pre-wrap; word-break: break-all; margin: .2rem 0; font-size: .85rem; }
  a { color: #2980b9; }
  .label { font-weight: bold; color: #555; }
  .meta { color: #666; font-size: .9rem; margin-bottom: 1rem; }
</style>
"""


def _page(title: str, body: str) -> str:
    t = html.escape(title)
    return (
        f"<!doctype html><html><head><meta charset=utf-8>"
        f"<title>{t}</title>{_STYLE}</head><body>{body}</body></html>"
    )


def _render_step(step: Step) -> str:
    kind = html.escape(step.kind)
    parts = [
        f'<div class="step kind-{kind}">',
        f'<span class="label">#{html.escape(str(step.index))} [{kind}]</span>',
    ]
    if step.tool is not None:
        parts.append(f' &nbsp;<span class="label">tool:</span> {html.escape(step.tool)}')
    if step.args is not None:
        args_text = ", ".join(
            f"{html.escape(k)}={html.escape(str(v))}" for k, v in step.args.items()
        )
        parts.append(f'<br><span class="label">args:</span> {args_text}')
    if step.observation is not None:
        obs = html.escape(step.observation)
        parts.append(f'<br><span class="label">observation:</span> <pre>{obs}</pre>')
    parts.append(f'<br><span class="label">reply:</span> <pre>{html.escape(step.reply)}</pre>')
    parts.append("</div>")
    return "".join(parts)


def _render_index(sessions: list[Session], url_for_session: Callable[[str], str]) -> str:
    """Render the session list page.

    *url_for_session* is a callable that accepts a session id and returns the
    absolute (mount-aware) URL string for that session's detail page.
    """
    if not sessions:
        rows = "<tr><td colspan=5>No sessions recorded yet.</td></tr>"
    else:
        rows = "".join(
            "<tr>"
            f'<td><a href="{html.escape(str(url_for_session(s.id)))}">'
            f"{html.escape(s.title)}"
            f"</a><br><small>{html.escape(s.id)}</small></td>"
            f"<td>{html.escape(s.model)}</td>"
            f"<td>{html.escape(s.status)}</td>"
            f"<td>{html.escape(str(len(s.steps)))}</td>"
            f"<td>{html.escape(s.task[:80])}</td>"
            "</tr>"
            for s in sessions
        )
    table = (
        "<table>"
        "<tr><th>Session</th><th>Model</th><th>Status</th><th>Steps</th><th>Task</th></tr>"
        f"{rows}"
        "</table>"
    )
    return _page("Understory Sessions", f"<h1>Sessions</h1>{table}")


def _render_detail(session: Session) -> str:
    """Render the detail page for a single session."""
    header = (
        f'<div class="meta">'
        f"<b>Model:</b> {html.escape(session.model)} &nbsp;"
        f"<b>Status:</b> {html.escape(session.status)} &nbsp;"
        f"<b>Workspace:</b> {html.escape(session.workspace_path)}"
        f"</div>"
        f"<p><b>Task:</b> {html.escape(session.task)}</p>"
    )
    steps_html = "".join(_render_step(s) for s in session.steps)
    title_escaped = html.escape(session.title)
    id_escaped = html.escape(session.id)
    body = (
        f"<h1>{title_escaped}</h1>"
        f'<p class="meta"><b>Session ID:</b> {id_escaped}</p>'
        f"{header}{steps_html}"
    )
    return _page(session.title, body)


def build_web_app(store: TraceStore) -> Starlette:
    """Return a Starlette app that renders trace sessions as HTML pages."""

    async def index(request: Request) -> Response:
        def url_for_session(session_id: str) -> str:
            return str(request.url_for("session_detail", session_id=session_id))

        return HTMLResponse(_render_index(list(store.list()), url_for_session))

    async def detail(request: Request) -> Response:
        sid = request.path_params["session_id"]
        session = store.get(sid)
        if session is None:
            return HTMLResponse("<h1>Session not found</h1>", status_code=404)
        return HTMLResponse(_render_detail(session))

    return Starlette(
        routes=[
            Route("/", index),
            Route("/{session_id}", detail, name="session_detail"),
        ]
    )
