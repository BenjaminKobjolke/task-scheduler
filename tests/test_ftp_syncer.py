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
        with patch.object(syncer_obj.config, "get_ftp_settings", return_value=ftp_settings):
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
        with patch.object(syncer_obj.config, "get_ftp_settings", return_value=ftp_settings):
            with patch.object(syncer_obj.logger, "info") as mock_info:
                syncer_obj.sync("/local/path")

        # Check that at least one info call mentions sync stats
        info_messages = [str(call) for call in mock_info.call_args_list]
        assert any("3/16" in msg for msg in info_messages)

    @patch("src.ftp_syncer.UploadSynchronizer", spec=True)
    @patch("src.ftp_syncer.FTPTarget", spec=True)
    @patch("src.ftp_syncer.FsTarget", spec=True)
    def test_run_called_without_explicit_close(
        self, mock_fs, mock_ftp, mock_syncer_cls, ftp_settings
    ):
        """syncer.close() should NOT be called explicitly (run() handles it)."""
        mock_syncer = MagicMock()
        mock_syncer.get_stats.return_value = {
            "entries_touched": 0,
            "entries_seen": 0,
            "local_dirs": 0,
        }
        mock_syncer_cls.return_value = mock_syncer

        syncer_obj = FtpSyncer()
        with patch.object(syncer_obj.config, "get_ftp_settings", return_value=ftp_settings):
            syncer_obj.sync("/local/path")

        mock_syncer.run.assert_called_once()
        mock_syncer.close.assert_not_called()

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
        with patch.object(syncer_obj.config, "get_ftp_settings", return_value=ftp_settings):
            result = syncer_obj.sync("/local/path")

        assert result is False
