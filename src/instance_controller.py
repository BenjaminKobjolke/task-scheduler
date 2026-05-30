"""Single-instance lock and graceful stop-request coordination.

Bundles everything needed to enforce one running scheduler and to ask a running
instance to shut down cleanly across processes. Uses an OS-level file lock
(released automatically on process exit, even on crash) plus a stop-request flag
file that the running loop polls.
"""

import os
import time

from filelock import FileLock, Timeout

from src.constants import Defaults, Paths


class InstanceController:
    """Owns the instance lock and the stop-request flag for the scheduler."""

    def __init__(self, data_dir: str = Paths.DATA_DIR) -> None:
        os.makedirs(data_dir, exist_ok=True)
        self._lock_path = os.path.join(data_dir, Paths.LOCK_FILE)
        self._request_path = os.path.join(data_dir, Paths.SHUTDOWN_REQUEST)
        self._lock = FileLock(self._lock_path)

    def try_acquire(self) -> bool:
        """Try to become the sole instance. True if the lock was acquired."""
        try:
            self._lock.acquire(timeout=0)
            return True
        except Timeout:
            return False

    def release(self) -> None:
        """Release the instance lock if held."""
        if self._lock.is_locked:
            self._lock.release()

    def is_running(self) -> bool:
        """True if another process currently holds the instance lock."""
        probe = FileLock(self._lock_path)
        try:
            probe.acquire(timeout=0)
        except Timeout:
            return True
        probe.release()
        return False

    def request_shutdown(self) -> None:
        """Write the stop-request flag that a running instance polls for."""
        with open(self._request_path, "w", encoding="utf-8") as flag:
            flag.write("stop")

    def shutdown_requested(self) -> bool:
        """True if a stop-request flag is present."""
        return os.path.exists(self._request_path)

    def clear_request(self) -> None:
        """Remove the stop-request flag if present."""
        if os.path.exists(self._request_path):
            os.remove(self._request_path)

    def wait_until_stopped(
        self,
        timeout: float = Defaults.SHUTDOWN_WAIT_SECONDS,
        poll: float = Defaults.SHUTDOWN_POLL_SECONDS,
    ) -> bool:
        """Poll until no instance is running or timeout elapses.

        Returns True if the instance stopped within the timeout.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not self.is_running():
                return True
            time.sleep(poll)
        return not self.is_running()
