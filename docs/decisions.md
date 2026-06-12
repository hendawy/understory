# Design decisions

Short rationale for choices that might otherwise look like antipatterns.

## Interfaces use `typing.Protocol`, not `ABC`

Domain interfaces (`ChatProvider`, `ConversationStore`, `Workspace`, `Tool`) are
`Protocol`s. This can look odd next to "code to interfaces" — here's why it *is*
that, done well:

- **Dependency direction.** Consumers (`ChatService`, `AgentRunner`) depend on the
  protocol in `domain`. Implementations conform by shape; `infrastructure` never has
  to be imported by `domain`. Dependencies point inward, per the layering rule.
- **Free test doubles.** Fakes (`FakeProvider`, `ScriptedProvider`) satisfy a protocol
  without inheriting anything or a mock framework.
- **Swappable providers.** Anything with the right methods fits. Ollama is just one
  implementation of `ChatProvider`.

### But we still inherit explicitly

Pure structural typing only errors at the *call site*. So implementations also
inherit their protocol (`LocalFilesystemWorkspace(Workspace)`), which makes the type
checker verify conformance at the class definition — ABC-style safety, without losing
structural flexibility for fakes.

### When to use `ABC` instead

If an interface ever needs shared concrete methods or runtime `isinstance` checks,
switch that one to `ABC`. Our interfaces are pure contracts, so `Protocol` is the
lighter, correct tool.
