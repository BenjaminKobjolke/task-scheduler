"""Tests for InstanceController single-instance + stop-request handling."""

import os

from src.constants import Paths
from src.instance_controller import InstanceController


class TestAcquireRelease:
    """Lock acquisition semantics."""

    def test_fresh_controller_not_running(self, tmp_path):
        ctrl = InstanceController(data_dir=str(tmp_path))
        assert ctrl.is_running() is False

    def test_try_acquire_succeeds_when_free(self, tmp_path):
        ctrl = InstanceController(data_dir=str(tmp_path))
        assert ctrl.try_acquire() is True
        ctrl.release()

    def test_second_controller_sees_running(self, tmp_path):
        holder = InstanceController(data_dir=str(tmp_path))
        assert holder.try_acquire() is True
        try:
            probe = InstanceController(data_dir=str(tmp_path))
            assert probe.is_running() is True
            assert probe.try_acquire() is False
        finally:
            holder.release()

    def test_release_allows_reacquire(self, tmp_path):
        first = InstanceController(data_dir=str(tmp_path))
        assert first.try_acquire() is True
        first.release()

        second = InstanceController(data_dir=str(tmp_path))
        assert second.try_acquire() is True
        second.release()

    def test_creates_data_dir(self, tmp_path):
        target = tmp_path / "nested" / "data"
        InstanceController(data_dir=str(target))
        assert target.is_dir()


class TestStopRequest:
    """Stop-request flag file handling."""

    def test_request_and_clear(self, tmp_path):
        ctrl = InstanceController(data_dir=str(tmp_path))
        assert ctrl.shutdown_requested() is False

        ctrl.request_shutdown()
        assert ctrl.shutdown_requested() is True
        assert os.path.exists(os.path.join(str(tmp_path), Paths.SHUTDOWN_REQUEST))

        ctrl.clear_request()
        assert ctrl.shutdown_requested() is False

    def test_clear_request_idempotent(self, tmp_path):
        ctrl = InstanceController(data_dir=str(tmp_path))
        ctrl.clear_request()  # no flag present — must not raise
        assert ctrl.shutdown_requested() is False


class TestWaitUntilStopped:
    """wait_until_stopped polling behaviour."""

    def test_returns_true_when_nothing_running(self, tmp_path):
        ctrl = InstanceController(data_dir=str(tmp_path))
        assert ctrl.wait_until_stopped(timeout=1, poll=0.05) is True

    def test_returns_false_while_held(self, tmp_path):
        holder = InstanceController(data_dir=str(tmp_path))
        assert holder.try_acquire() is True
        try:
            probe = InstanceController(data_dir=str(tmp_path))
            assert probe.wait_until_stopped(timeout=0.3, poll=0.05) is False
        finally:
            holder.release()


class TestStopRunning:
    """stop_running combines request_shutdown + wait_until_stopped."""

    def test_writes_flag_and_returns_true_when_idle(self, tmp_path):
        ctrl = InstanceController(data_dir=str(tmp_path))
        assert ctrl.stop_running(timeout=1, poll=0.05) is True
        assert ctrl.shutdown_requested() is True

    def test_returns_false_while_held(self, tmp_path):
        holder = InstanceController(data_dir=str(tmp_path))
        assert holder.try_acquire() is True
        try:
            probe = InstanceController(data_dir=str(tmp_path))
            assert probe.stop_running(timeout=0.3, poll=0.05) is False
        finally:
            holder.release()
