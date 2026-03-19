"""Tests for FTP syncer lock file cleanup."""

import ftplib
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


class TestFtpSyncerClose:
    """Tests that syncer is explicitly closed after run."""

    @patch("src.ftp_syncer.UploadSynchronizer", spec=True)
    @patch("src.ftp_syncer.FTPTarget", spec=True)
    @patch("src.ftp_syncer.FsTarget", spec=True)
    def test_syncer_close_called_after_run(
        self, mock_fs, mock_ftp, mock_syncer_cls, ftp_settings
    ):
        """Syncer.close() must be called after syncer.run() completes."""
        mock_syncer = MagicMock()
        mock_syncer_cls.return_value = mock_syncer

        syncer_obj = FtpSyncer()
        with patch.object(syncer_obj.config, "get_ftp_settings", return_value=ftp_settings):
            with patch.object(syncer_obj.config, "is_console_logging_enabled", return_value=True):
                syncer_obj.sync("/local/path")

        mock_syncer.run.assert_called_once()
        mock_syncer.close.assert_called_once()

    @patch("src.ftp_syncer.UploadSynchronizer", spec=True)
    @patch("src.ftp_syncer.FTPTarget", spec=True)
    @patch("src.ftp_syncer.FsTarget", spec=True)
    def test_syncer_close_called_when_console_suppressed(
        self, mock_fs, mock_ftp, mock_syncer_cls, ftp_settings
    ):
        """Syncer.close() must be called even when stdout is suppressed."""
        mock_syncer = MagicMock()
        mock_syncer_cls.return_value = mock_syncer

        syncer_obj = FtpSyncer()
        with patch.object(syncer_obj.config, "get_ftp_settings", return_value=ftp_settings):
            with patch.object(syncer_obj.config, "is_console_logging_enabled", return_value=False):
                syncer_obj.sync("/local/path")

        mock_syncer.run.assert_called_once()
        mock_syncer.close.assert_called_once()

    @patch("src.ftp_syncer.UploadSynchronizer", spec=True)
    @patch("src.ftp_syncer.FTPTarget", spec=True)
    @patch("src.ftp_syncer.FsTarget", spec=True)
    def test_syncer_close_lock_file_error_suppressed(
        self, mock_fs, mock_ftp, mock_syncer_cls, ftp_settings
    ):
        """Lock file 550 error during close() should be suppressed."""
        mock_syncer = MagicMock()
        mock_syncer.close.side_effect = ftplib.error_perm("550 No such file")
        mock_syncer_cls.return_value = mock_syncer

        syncer_obj = FtpSyncer()
        with patch.object(syncer_obj.config, "get_ftp_settings", return_value=ftp_settings):
            with patch.object(syncer_obj.config, "is_console_logging_enabled", return_value=True):
                result = syncer_obj.sync("/local/path")

        assert result is True

    @patch("src.ftp_syncer.UploadSynchronizer", spec=True)
    @patch("src.ftp_syncer.FTPTarget", spec=True)
    @patch("src.ftp_syncer.FsTarget", spec=True)
    def test_syncer_close_called_even_when_run_fails(
        self, mock_fs, mock_ftp, mock_syncer_cls, ftp_settings
    ):
        """Syncer.close() must be called even if run() raises."""
        mock_syncer = MagicMock()
        mock_syncer.run.side_effect = Exception("upload failed")
        mock_syncer_cls.return_value = mock_syncer

        syncer_obj = FtpSyncer()
        with patch.object(syncer_obj.config, "get_ftp_settings", return_value=ftp_settings):
            with patch.object(syncer_obj.config, "is_console_logging_enabled", return_value=True):
                result = syncer_obj.sync("/local/path")

        assert result is False
        mock_syncer.close.assert_called_once()

    @patch("src.ftp_syncer.UploadSynchronizer", spec=True)
    @patch("src.ftp_syncer.FTPTarget", spec=True)
    @patch("src.ftp_syncer.FsTarget", spec=True)
    def test_remote_close_neutralized_after_sync(
        self, mock_fs, mock_ftp, mock_syncer_cls, ftp_settings
    ):
        """remote.close should be a no-op after sync to prevent __del__ errors."""
        mock_syncer = MagicMock()
        mock_remote = mock_ftp.return_value
        mock_syncer_cls.return_value = mock_syncer

        syncer_obj = FtpSyncer()
        with patch.object(syncer_obj.config, "get_ftp_settings", return_value=ftp_settings):
            with patch.object(syncer_obj.config, "is_console_logging_enabled", return_value=True):
                syncer_obj.sync("/local/path")

        # remote.close was replaced with a no-op lambda after explicit
        # syncer.close(), so __del__ won't try to delete the lock file again
        assert not isinstance(mock_remote.close, MagicMock)
