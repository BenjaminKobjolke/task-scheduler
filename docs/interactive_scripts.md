# Interactive Scripts — Asking the User via Chat

Scripts run by the scheduler can ask the user questions (yes/no, free text,
multiple choice). When a task is started with `/run` from the bot chat
(XMPP/Jabber or Telegram), the question appears in the chat and the user's reply
is sent back to the script. When started with `python main.py --run_id ID`, the
question is asked in the terminal instead.

The protocol is plain JSON lines over stdout/stdin, so it works from any
language (Python, batch, PowerShell, ...).

## When prompts work

| How the task runs                        | Prompts answered?                        |
|------------------------------------------|------------------------------------------|
| `/run <id>` in the bot chat              | Yes — in the chat                        |
| `python main.py --run_id ID`             | Yes — in the terminal                    |
| Regular interval schedule                | **No**                                   |
| Task with "launch in new process" set    | **No**                                   |

During a regular scheduled run the script's stdout only goes to the log and
nothing writes a reply to stdin. A script that waits for a reply there blocks
until the scheduler's script timeout (30 minutes) kills it. Only prompt in tasks
you trigger manually, or make prompting optional (e.g. a `--ask` argument you
pass only in a separate manually-run task).

The scheduler sets the environment variable `INTERACTIVE=1` for **every** script
it runs. It tells you the script runs under the scheduler — not that a reply
will come.

## Asking a question

Print **one JSON line** to stdout and flush:

```json
{"_interactive": true, "type": "confirm", "id": "deploy", "message": "Deploy to production?", "default": false}
```

| Field          | Required | Meaning                                                     |
|----------------|----------|-------------------------------------------------------------|
| `_interactive` | yes      | Must be literally `true`, otherwise the line is plain output |
| `type`         | yes      | `confirm`, `input`, `choice` or `output`                    |
| `id`           | yes*     | Your identifier, echoed back in the reply (*not for `output`) |
| `message`      | yes      | Question text shown to the user                             |
| `default`      | no       | Value used when the user does not answer in time            |
| `options`      | `choice` | List of option strings                                      |

Then read **one JSON line** from stdin:

```json
{"id": "deploy", "value": true}
```

| Field       | Present           | Meaning                                         |
|-------------|-------------------|-------------------------------------------------|
| `id`        | always            | The `id` of the question                        |
| `value`     | always            | The answer, or `null` on error                  |
| `timed_out` | only when true    | No reply in time; `value` is your `default`     |
| `error`     | only on error     | E.g. timeout without default, or user cancelled |

### Value types

| `type`    | `value`                | Chat reply accepted                                         |
|-----------|------------------------|-------------------------------------------------------------|
| `confirm` | bool                   | `y`, `yes`, `true`, `1` = true; anything else = false       |
| `input`   | string                 | Any text (trimmed)                                          |
| `choice`  | int, **0-based** index | Option number (1-based in chat); invalid → `default` or `0` |

`default` for `choice` is also a 0-based index.

### Display-only messages

```json
{"_interactive": true, "type": "output", "message": "Step 2/3 done"}
```

Shown to the user, no reply. Any other stdout/stderr line is relayed too, so a
plain `print()` works just as well. Chat output is batched and rate-limited.

## Timeout

The reply wait time is set in `config.ini`:

```ini
[Interactive]
timeout = 300
```

On timeout the script receives the `default` with `"timed_out": true`, or
`"value": null` with an `error` if there is no default. Always give a default
when a sensible one exists.

## Python helper

Copy into your script:

```python
import json
import sys
from typing import Any


def ask(
    type_: str,
    id_: str,
    message: str,
    default: Any = None,
    options: list[str] | None = None,
) -> Any:
    """Ask the user via the task scheduler. Returns the answer value."""
    request: dict[str, Any] = {
        "_interactive": True,
        "type": type_,
        "id": id_,
        "message": message,
    }
    if default is not None:
        request["default"] = default
    if options is not None:
        request["options"] = options
    print(json.dumps(request), flush=True)

    line = sys.stdin.readline()
    if not line:
        return default  # stdin closed
    reply = json.loads(line)
    if reply.get("error"):
        raise RuntimeError(reply["error"])
    return reply["value"]


if __name__ == "__main__":
    if not ask("confirm", "go", "Run the cleanup now?", default=False):
        print("Skipped.")
        sys.exit(0)

    name = ask("input", "name", "Which folder?", default="temp")
    mode = ask("choice", "mode", "Mode?", default=0, options=["dry run", "delete"])
    print(f"Cleaning {name} in mode {mode}")
```

## Batch / PowerShell

Same protocol: `echo` the JSON line, then read one line from stdin.

```powershell
Write-Output '{"_interactive": true, "type": "input", "id": "q", "message": "Your name?"}'
$reply = [Console]::In.ReadLine() | ConvertFrom-Json
Write-Output "Hello $($reply.value)"
```

## Implementation reference

- `src/interaction.py` — request/response types and parsing
- `src/script_runner.py` — `_run_interactive` stdout/stdin relay
- `src/bot/interaction_handler.py` — chat formatting and reply parsing
