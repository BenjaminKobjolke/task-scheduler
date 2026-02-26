"""FTP synchronization for status page uploads."""

from ftpsync.ftp_target import FTPTarget
from ftpsync.synchronizers import UploadSynchronizer
from ftpsync.targets import FsTarget

from .logger import Logger
from .config import Config


class FtpSyncer:
    """Handles FTP upload of status page files."""

    def __init__(self):
        """Initialize FTP syncer with settings from config."""
        self.logger = Logger("FtpSyncer")
        self.config = Config()

    def sync(self, local_path: str) -> bool:
        """
        Upload local directory to FTP server.

        Args:
            local_path: Local directory to upload

        Returns:
            True if sync was successful, False otherwise
        """
        settings = self.config.get_ftp_settings()

        if not settings["enabled"]:
            self.logger.debug("FTP sync is disabled")
            return False

        if not settings["host"]:
            self.logger.warning("FTP host not configured")
            return False

        try:
            self.logger.info(
                f"Starting FTP sync to {settings['host']}:{settings['remote_path']}"
            )

            local = FsTarget(str(local_path))

            remote = FTPTarget(
                path=settings["remote_path"],
                host=settings["host"],
                port=settings["port"],
                username=settings["username"],
                password=settings["password"],
                timeout=settings["timeout"],
                extra_opts={"create_folder": True},
            )

            opts = {
                "resolve": "local",  # Local files win (overwrite remote)
                "delete": False,  # Don't delete remote files not in local
            }

            syncer = UploadSynchronizer(local, remote, opts)
            syncer.run()

            self.logger.info("FTP sync completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"FTP sync failed: {str(e)}")
            return False
