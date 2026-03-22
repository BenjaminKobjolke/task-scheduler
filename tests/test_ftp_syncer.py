"""Tests for FTP syncer."""

from unittest.mock import MagicMock, patch

import pytest

from src.ftp_syncer import FtpSyncer


@pytest.fixture
def ftp_settings():
    """Return valid FTP settings for testing."""
    return {
        "enabled": True,
        "host": "ftp.example.com",
        "port": 21,
        "username": "user",
        "password": "pass",
        "remote_path": "/remote",
        "timeout": 30,
    }


class TestFtpSyncerVerbose:
    """Tests that pyftpsync verbose output is suppressed."""

    @patch("src.ftp_syncer.UploadSynchronizer", spec=True)
    @patch("src.ftp_syncer.FTPTarget", spec=True)
    @patch("src.ftp_syncer.FsTarget", spec=True)
    def test_verbose_zero_passed_to_synchronizer(
        self, mock_fs, mock_ftp, mock_syncer_cls, ftp_settings
    ):
        """UploadSynchronizer must receive verbose=0 to suppress stdout output."""
        mock_syncer = MagicMock()
        mock_syncer.get_stats.return_value = {
            "entries_touched": 0,
            "entries_seen": 0,
            "local_dirs": 0,
        }
        mock_syncer_cls.return_value = mock_syncer

        syncer_obj = FtpSyncer()
        with patch.object(
            syncer_obj.config, "get_ftp_settings", return_value=ftp_settings
        ):
            syncer_obj.sync("/local/path")

        _, kwargs = mock_syncer_cls.call_args
        opts = kwargs.get("options") or mock_syncer_cls.call_args[0][2]
        assert opts["verbose"] == 0


class TestFtpSyncerStats:
    """Tests that sync stats are logged after run."""

    @patch("src.ftp_syncer.UploadSynchronizer", spec=True)
    @patch("src.ftp_syncer.FTPTarget", spec=True)
    @patch("src.ftp_syncer.FsTarget", spec=True)
    def test_stats_logged_after_successful_sync(
        self, mock_fs, mock_ftp, mock_syncer_cls, ftp_settings
    ):
        """Sync stats should be logged via our logger after run() completes."""
        mock_syncer = MagicMock()
        mock_syncer.get_stats.return_value = {
            "entries_touched": 3,
            "entries_seen": 16,
            "local_dirs": 2,
        }
        mock_syncer_cls.return_value = mock_syncer

        syncer_obj = FtpSyncer()
        with patch.object(
            syncer_obj.config, "get_ftp_settings", return_value=ftp_settings
        ):
            with patch.object(syncer_obj.logger, "info") as mock_info:
                syncer_obj.sync("/local/path")

        # Check that at least one info call mentions sync stats
        info_messages = [str(call) for call in mock_info.call_args_list]
        assert any("3/16" in msg for msg in info_messages)

    @patch("src.ftp_syncer.UploadSynchronizer", spec=True)
    @patch("src.ftp_syncer.FTPTarget", spec=True)
    @patch("src.ftp_syncer.FsTarget", spec=True)
    def test_run_called_and_close_neutralized(
        self, mock_fs, mock_ftp, mock_syncer_cls, ftp_settings
    ):
        """run() should be called, and close replaced with no-op afterwards."""
        mock_syncer = MagicMock()
        mock_syncer.get_stats.return_value = {
            "entries_touched": 0,
            "entries_seen": 0,
            "local_dirs": 0,
        }
        mock_syncer_cls.return_value = mock_syncer

        syncer_obj = FtpSyncer()
        with patch.object(
            syncer_obj.config, "get_ftp_settings", return_value=ftp_settings
        ):
            syncer_obj.sync("/local/path")

        mock_syncer.run.assert_called_once()
        # close should be a no-op lambda, not the original MagicMock method
        assert not isinstance(mock_syncer.close, MagicMock)

    @patch("src.ftp_syncer.UploadSynchronizer", spec=True)
    @patch("src.ftp_syncer.FTPTarget", spec=True)
    @patch("src.ftp_syncer.FsTarget", spec=True)
    def test_close_methods_replaced_after_run(
        self, mock_fs_cls, mock_ftp_cls, mock_syncer_cls, ftp_settings
    ):
        """After run(), close methods must be replaced with no-ops."""
        mock_remote = MagicMock()
        mock_ftp_cls.return_value = mock_remote
        mock_local = MagicMock()
        mock_fs_cls.return_value = mock_local

        mock_syncer = MagicMock()
        mock_syncer.get_stats.return_value = {
            "entries_touched": 0,
            "entries_seen": 0,
            "local_dirs": 0,
        }
        mock_syncer_cls.return_value = mock_syncer

        syncer_obj = FtpSyncer()
        with patch.object(
            syncer_obj.config, "get_ftp_settings", return_value=ftp_settings
        ):
            syncer_obj.sync("/local/path")

        # close methods should be no-op lambdas — calling them should do nothing
        mock_remote.close()  # should not raise
        mock_local.close()
        mock_syncer.close()

    @patch("src.ftp_syncer.UploadSynchronizer", spec=True)
    @patch("src.ftp_syncer.FTPTarget", spec=True)
    @patch("src.ftp_syncer.FsTarget", spec=True)
    def test_neutralization_works_when_run_raises(
        self, mock_fs_cls, mock_ftp_cls, mock_syncer_cls, ftp_settings
    ):
        """When run() raises (e.g. 550 from _unlock), close methods must still be neutralized."""
        mock_remote = MagicMock()
        original_close = mock_remote.close
        mock_ftp_cls.return_value = mock_remote
        mock_local = MagicMock()
        mock_fs_cls.return_value = mock_local

        mock_syncer = MagicMock()
        mock_syncer.run.side_effect = Exception(
            "550 .pyftpsync-lock.json: No such file"
        )
        mock_syncer_cls.return_value = mock_syncer

        syncer_obj = FtpSyncer()
        with patch.object(
            syncer_obj.config, "get_ftp_settings", return_value=ftp_settings
        ):
            result = syncer_obj.sync("/local/path")

        assert result is False
        # Even though run() raised, close methods must be replaced with no-ops
        # so __del__ doesn't trigger the same error again
        assert mock_remote.close != original_close

    @patch("src.ftp_syncer.UploadSynchronizer", spec=True)
    @patch("src.ftp_syncer.FTPTarget", spec=True)
    @patch("src.ftp_syncer.FsTarget", spec=True)
    def test_run_failure_returns_false(
        self, mock_fs, mock_ftp, mock_syncer_cls, ftp_settings
    ):
        """When run() raises, sync() should return False."""
        mock_syncer = MagicMock()
        mock_syncer.run.side_effect = Exception("upload failed")
        mock_syncer_cls.return_value = mock_syncer

        syncer_obj = FtpSyncer()
        with patch.object(
            syncer_obj.config, "get_ftp_settings", return_value=ftp_settings
        ):
            result = syncer_obj.sync("/local/path")

        assert result is False
