"""Tests for single-instance protection via filelock."""

import os

import pytest
from filelock import FileLock, Timeout

from src.constants import Messages, Paths


class TestLockConstants:
    """Tests for lock-related constants."""

    def test_lock_file_defined(self):
        assert Paths.LOCK_FILE == "scheduler.lock"

    def test_lock_path_under_data_dir(self):
        lock_path = os.path.join(Paths.DATA_DIR, Paths.LOCK_FILE)
        assert lock_path == os.path.join("data", "scheduler.lock")

    def test_already_running_message_defined(self):
        assert "already running" in Messages.ALREADY_RUNNING.lower()


class TestSingleInstanceLock:
    """Tests for non-blocking FileLock acquisition semantics."""

    def test_acquire_succeeds_when_free(self, tmp_path):
        lock_path = str(tmp_path / Paths.LOCK_FILE)
        lock = FileLock(lock_path)
        lock.acquire(timeout=0)
        try:
            assert lock.is_locked
        finally:
            lock.release()

    def test_second_acquire_raises_timeout(self, tmp_path):
        lock_path = str(tmp_path / Paths.LOCK_FILE)
        first = FileLock(lock_path)
        first.acquire(timeout=0)
        try:
            second = FileLock(lock_path)
            with pytest.raises(Timeout):
                second.acquire(timeout=0)
        finally:
            first.release()

    def test_release_allows_reacquire(self, tmp_path):
        lock_path = str(tmp_path / Paths.LOCK_FILE)
        first = FileLock(lock_path)
        first.acquire(timeout=0)
        first.release()

        second = FileLock(lock_path)
        second.acquire(timeout=0)
        try:
            assert second.is_locked
        finally:
            second.release()
