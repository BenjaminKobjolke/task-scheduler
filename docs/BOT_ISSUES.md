# Bot Issues — XMPP Reconnection & pyftpsync Errors

## Issue 1: XMPP Bot Loses Connection and Never Recovers

### Symptom

The XMPP bot connects successfully on startup but after a network interruption or server restart, it produces a flood of log messages and stays permanently offline:

```
ERROR - Reconnection timed out
INFO  - Disconnected from XMPP server
ERROR - Reconnection timed out
INFO  - Disconnected from XMPP server
(repeated 50+ times within milliseconds)
```

The health monitor reports the bot thread as alive, so no restart is attempted. The bot stays silently disconnected until the entire scheduler is restarted.

### Root Cause (found 2026-03-22)

A chain of three bugs across three repositories:

1. **xmpp-bot**: `_disconnect_requested` flag was never reset during `initialize()`. After the health monitor called `disconnect()` then `initialize()`, the flag stayed `True`, permanently suppressing auto-reconnect in `_on_disconnected()`.

2. **bot-commander**: `XmppAdapter.shutdown()` called `XmppBot.disconnect()` directly from the main thread, but the bot's event loop and reconnect loop ran in a separate daemon thread. This cross-thread access caused race conditions with the reconnect loop.

3. **task-scheduler**: `BotHealthMonitor.is_alive()` only checked `thread.is_alive()`. When the bot thread was running but the XMPP connection was dead (due to bug #1), the health monitor saw the bot as healthy and took no action.

### Timeline of Fix Attempts

#### Attempt 1 — Auto-reconnect with exponential backoff
- **xmpp-bot** `37a47a0` (2026-02-28)
- Added `_auto_reconnect()` with exponential backoff (5s → 300s cap)
- Added XEP-0199 XMPP Ping for keepalive dead-connection detection
- **Result**: Worked initially but broke under sustained disconnections

#### Attempt 2 — Retry after timeout and exceptions
- **xmpp-bot** `7d80986` (2026-03-07)
- Added retry logic after timeouts and general exceptions
- Auth failures still stop retries (credentials won't fix themselves)
- Spawned new `_auto_reconnect()` coroutines via `ensure_future` on failures
- **Result**: Caused exponential growth of reconnect coroutines (2^N cascade)

#### Attempt 3 — Prevent exponential reconnect coroutine cascade
- **xmpp-bot** `f83f704` (2026-03-20)
- Replaced recursive `ensure_future` spawning with a `while` loop in `_reconnect_loop()`
- Added `_reconnecting` guard flag to prevent concurrent reconnects
- Added `_cleanup_client()` helper to safely disconnect without triggering reconnect events
- **Result**: Fixed the cascade but race condition remained — multiple disconnect events in the same event-loop tick could still spawn duplicate coroutines

#### Attempt 4 — Eliminate check-then-act race in reconnect guard
- **xmpp-bot** `86f416b` (2026-03-21)
- Set `_reconnecting` flag synchronously in `_on_disconnected()` BEFORE `ensure_future()` schedules the coroutine
- Introduced `_reconnect_task` as `asyncio.Task` for deterministic cancellation
- Removed event handlers from old clients in `_cleanup_client()` to prevent stale disconnect events
- Caught `CancelledError` explicitly in `_auto_reconnect()`
- **Result**: Fixed the race condition for concurrent events, but the core bug (`_disconnect_requested` never reset) was still present

#### Attempt 5 — Thread-safe disconnect and health monitor improvements
- **bot-commander** `09c3c78` (2026-02-28): Changed disconnect to synchronous call
- **bot-commander** `507597e` (2026-03-02): Added error handling to event loop daemon thread
- **task-scheduler** `f366016` (2026-03-02): Added `BotHealthMonitor` with thread health checks
- **Result**: Health monitor could detect thread death but not silent disconnects. Synchronous disconnect call still ran from wrong thread.

#### Attempt 6 — Root cause fix (2026-03-22)
- **xmpp-bot** `c3e3c6b`: Reset `_disconnect_requested`, `_reconnecting`, and `_reconnect_delay` in `initialize()`. Also clean up timed-out clients immediately in reconnect loop.
- **bot-commander** `0a280eb`: Thread-safe `shutdown()` — schedule disconnect on the bot's own event loop via `run_coroutine_threadsafe` with 10-second timeout fallback.
- **task-scheduler** `6579250`: Health monitor now checks both `thread.is_alive()` AND `XmppBot.is_connected`. Resets `reconnect_attempts` when bot is fully healthy. Distinguishes "thread dead" from "alive but disconnected" in log messages.
- **Result**: Pending validation in production.

---

## Issue 2: pyftpsync `__del__` Errors

### Symptom

After FTP sync completes, stderr shows noisy errors during garbage collection:

```
Exception ignored in: <function _Target.__del__ at 0x...>
  ...
  File "ftpsync/ftp_target.py", line 357, in _unlock
    self.ftp.delete(DirMetadata.LOCK_FILE_NAME)
ftplib.error_perm: 550 .pyftpsync-lock.json: No such file or directory
```

This repeats for both `_Target.__del__` and `BaseSynchronizer.__del__`.

### Root Cause

pyftpsync's `__del__` destructors attempt cleanup (lock file deletion, FTP quit) during garbage collection. When `syncer.run()` calls `close()` internally in its `finally` block, if `_unlock()` fails with a 550 error (lock file already gone), the exception prevents `super().close()` from running, leaving `connected=True`. Then `__del__` retries `close()` and hits the same error.

### Timeline of Fix Attempts

#### Attempt 1 — Explicit close with error suppression
- **task-scheduler** `0ae07ff` (2026-03-19)
- Added try/finally around `syncer.run()` to call `syncer.close()` explicitly
- Suppressed `ftplib.error_perm` during `close()`
- **Result**: `__del__` destructors still fired during garbage collection

#### Attempt 2 — Neutralize remote.close with no-op lambda
- **task-scheduler** `b37db4d` (2026-03-19)
- Replaced `remote.close` with a no-op lambda after explicit `syncer.close()`
- **Result**: Double-close errors persisted — `BaseSynchronizer.__del__` also calls close

#### Attempt 3 — Remove redundant close, suppress stdout
- **task-scheduler** `18f9eba` (2026-03-19)
- Set `verbose=0` to suppress progress output
- Removed redundant `syncer.close()` call (run() already closes internally)
- Removed the lambda hack
- **Result**: `__del__` errors returned since targets weren't neutralized

#### Attempt 4 — Neutralize target state flags
- **task-scheduler** `dc5100d` (2026-03-20)
- After `syncer.run()`, set `remote.lock_data = False`, `remote.connected = False`, `remote.ftp_socket_connected = False`, `local.connected = False`
- **Result**: Failed when `syncer.run()` itself raised from its internal `close()` — the 550 error propagated from `run()`'s `finally` block, skipping the neutralization code entirely

#### Attempt 5 — Lambda no-ops in finally block (2026-03-22)
- **task-scheduler** `6579250`
- Moved neutralization to a `finally` block that runs whether `run()` succeeds or raises
- Replaced `close` methods with lambda no-ops instead of manipulating internal flags
- **Result**: Pending validation in production.

### Why Flag-Based Neutralization Failed

The pyftpsync `close()` chain:

```
FTPTarget.close()
  → _unlock(closing=True)     # 550 error raised here
  → ftp.quit()                # NEVER REACHED
  → super().close()           # NEVER REACHED — connected stays True
```

When `_unlock()` raises, `connected` is never set to `False`. Our neutralization code after `syncer.run()` was also skipped because the 550 error propagated from `run()`'s internal `finally` block. Using a `finally` block with method replacement ensures neutralization runs regardless of how `run()` exits.
