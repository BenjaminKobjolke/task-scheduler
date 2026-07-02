# Bot Integration

Remotely manage scheduled tasks from a Telegram or XMPP messenger. The bot is
**not a separate process** — it runs inside the scheduler (`python main.py` /
`start.bat`) and starts automatically when configured.

## How it works

```
start.bat  ->  main.py  ->  scheduler.start()  ->  bot_manager.start()
```

1. `main.py` reads `config.ini` `[Bot]` → `type` (`none` | `telegram` | `xmpp`).
2. If `type` is not `none`, it imports `BotManager` from the external
   `bot-commander` package and builds a `TaskCommandProcessor`
   (`src/bot/command_processor.py`).
3. After `scheduler.start()`, `bot_manager.start()` connects the bot on a
   background thread. Incoming messages are dispatched to the processor's
   command handlers.
4. A `BotHealthMonitor` (`src/bot_health.py`) polls every
   `HEALTH_CHECK_INTERVAL_SECONDS` (30s) from the main loop; if the bot thread
   dies or disconnects it auto-reconnects up to `MAX_RECONNECT_ATTEMPTS` (5).

Bot activity logs to `logs/bot_YYYYMMDD.log`.

### Relevant files

- `main.py` — bootstraps the bot inside the scheduler loop (~line 372–433)
- `src/bot/command_processor.py` — `TaskCommandProcessor`: commands, wizards, permissions
- `src/bot/conversation.py` — add/edit/delete interactive wizards
- `src/bot/interaction_handler.py` — relays script prompts/output to the chat
- `src/bot/constants.py` — command names, aliases, message templates
- `src/bot_health.py` — reconnect/health monitor
- `src/config.py` — reads the `[Bot]` config section
- External: [`bot-commander`](https://github.com/BenjaminKobjolke/bot-commander) (framework), [`xmpp-bot`](https://github.com/BenjaminKobjolke/xmpp-bot) (XMPP transport)

## Setup

### 1. Install the bot dependency

Bot support ships as an optional extra — a base `uv sync` does **not** install it.

Telegram:

```bash
uv sync --extra bot
```

XMPP (requires the Rust compiler on Windows — the XMPP dep compiles native code):

```bash
tools\install_xmpp_bot.bat      # runs: uv sync --extra xmpp
```

`install_xmpp_bot.bat` checks for `rustc` first and aborts with instructions
(https://rustup.rs/) if missing.

> If `type` is set but the extra is not installed, the scheduler logs a warning
> and continues without the bot. If only `bot-commander` is installed but the
> XMPP transport (`xmpp-bot`) is missing, the import succeeds but the bot fails
> to start at runtime — check `logs/bot_*.log` for `Bot failed to start`.

### 2. Configure `config.ini`

Add a `[Bot]` section.

XMPP:

```ini
[Bot]
type = xmpp
jid = bot-account@your-server
password = your-bot-password
default_receiver = you@your-server
allowed_jids = you@your-server
allow_add = true
allow_edit = true
allow_delete = true
```

| Key                | Meaning                                                        |
|--------------------|---------------------------------------------------------------|
| `type`             | `none` (disabled), `telegram`, or `xmpp`                      |
| `jid` / `password` | Bot account credentials (XMPP)                               |
| `default_receiver` | Where unsolicited notifications are sent                      |
| `allowed_jids`     | Comma-separated users allowed to command the bot             |
| `allow_add`        | Permit the `/add` command (default `false`)                  |
| `allow_edit`       | Permit the `/edit` command (default `false`)                 |
| `allow_delete`     | Permit the `/delete` command (default `false`)               |

Telegram uses the same `type = telegram` plus the token/receiver keys read by
`bot-commander`.

### 3. Start

```bash
start.bat        # or: python main.py
```

The bot comes up with the scheduler. Message it `/help` to confirm.

## Commands

Commands work with or without the leading `/`. Short aliases in parentheses.

| Command             | Alias | Action                                    |
|---------------------|-------|-------------------------------------------|
| `/list [filter]`    | `l`   | List tasks (optional name filter)         |
| `/run <id>`         | `r`   | Run a task now (background, notifies)     |
| `/history [n]`      | `hi`  | Show last `n` executions (default 10)     |
| `/add`              | `a`   | Add a task (interactive wizard)           |
| `/edit <id>`        | `e`   | Edit a task (interactive wizard)          |
| `/delete <id>`      | `d`   | Delete a task (confirm y/yes)             |
| `/cancel`           | `c`   | Cancel current operation                  |
| `/help`             | `h`   | Show help                                 |

`/add`, `/edit`, `/delete` require the matching `allow_*` permission to be
`true` in `config.ini`; otherwise the bot replies that the command is disabled.

Interactive scripts run via `/run` can prompt the user in chat — replies are
relayed back to the script (timeout from `[Interactive] timeout`).
