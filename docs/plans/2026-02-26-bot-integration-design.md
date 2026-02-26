# Bot Integration for Task Scheduler

## Context

The task-scheduler currently only supports CLI interaction. Users want to remotely list, execute, and manage tasks via messaging bots. Two bot libraries are available: [telegram-bot](https://github.com/BenjaminKobjolke/telegram-bot) and [xmpp-bot](https://github.com/BenjaminKobjolke/xmpp-bot). The user configures one in `config.ini` and can send commands to manage tasks from their phone/desktop messenger.

## Architecture: Message Bus Pattern

Thin bot adapters normalize messages into `BotMessage` DTOs. A bot-agnostic `CommandProcessor` handles all command logic and returns `BotResponse` strings. Adapters never touch commands; processor never touches bot APIs.

```
Bot receives message
  -> Adapter normalizes to BotMessage(user_id, text)
  -> BotManager passes to CommandProcessor.process()
  -> CommandProcessor returns BotResponse(text)
  -> BotManager calls adapter.reply(user_id, text)
```

## File Structure

```
src/bot/
  __init__.py                  # Exports BotManager
  constants.py                 # Bot config keys, command names, response messages
  types.py                     # BotMessage, BotResponse, BotConfig dataclasses
  command_processor.py          # process(BotMessage) -> BotResponse, all command handlers
  conversation.py               # AddWizard, EditWizard, ConfirmationState machines
  formatters.py                 # Compact task/history formatting for chat
  adapters/
    __init__.py
    base.py                    # BotAdapter ABC
    telegram_adapter.py        # Wraps TelegramBot singleton
    xmpp_adapter.py            # Wraps XmppBot singleton with async bridge thread
  bot_manager.py               # Factory + lifecycle manager
tools/
  install_telegram_bot.bat     # uv add --editable telegram-bot path
  install_xmpp_bot.bat         # uv add --editable xmpp-bot path
```

## Configuration (config.ini)

All settings in `config.ini` `[Bot]` section.

**For Telegram:**
```ini
[Bot]
type = telegram
bot_token = your_token_here
channel_id = @your_channel
allowed_user_ids = 123456,789012
allow_add = true
allow_edit = true
allow_delete = true
```

**For XMPP:**
```ini
[Bot]
type = xmpp
jid = bot@xmpp.domain.tld
password = secret
default_receiver = user@xmpp.domain.tld
allowed_jids = admin@xmpp.domain.tld,user@xmpp.domain.tld
allow_add = true
allow_edit = true
allow_delete = true
```

## Commands

| Command | Description | Confirmation | Disableable |
|---------|-------------|-------------|-------------|
| `/help` | Show available commands | No | No |
| `/list [filter]` | List tasks (optional name filter) | No | No |
| `/run <id>` | Execute task, report success/failure | No | No |
| `/history [n]` | Show last N executions (default 10) | No | No |
| `/add` | Conversational wizard to add task | Confirm at end | Yes |
| `/edit <id>` | Conversational wizard to edit task | Confirm at end | Yes |
| `/delete <id>` | Delete a task | Yes/No prompt | Yes |
| `/cancel` | Cancel current wizard/confirmation | No | No |

## Conversational Wizards

**Add wizard** (`/add`):
1. "Enter script path (or prefix with 'uv:' for uv command project):"
2. If uv project: "Enter command name:"
3. "Enter task name:"
4. "Enter interval in minutes:"
5. "Enter start time (HH:MM) or 'skip':"
6. "Enter arguments or 'skip':"
7. Summary -> "Reply 'yes' to add or 'no' to cancel"

**Edit wizard** (`/edit <id>`):
1. Show current task details
2. For each field: "Enter new value or 'skip' to keep current:"
3. Summary of changes -> "Reply 'yes' to save or 'no' to cancel"

**State management:** `dict[str, ConversationState]` in CommandProcessor keyed by user_id. States expire after 5 minutes. `/cancel` clears state.
