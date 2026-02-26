from __future__ import annotations

import os
import configparser
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from .bot.command_processor import BotConfig
from .constants import Bot as BotConstants
from .constants import Config as ConfigConstants


class Config:
    """Handle configuration settings for the task scheduler."""

    _instance = None

    def __new__(cls):
        """Ensure singleton pattern for configuration."""
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize configuration if not already initialized."""
        if self._initialized:
            return

        self.config = configparser.ConfigParser()
        self.config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.ini"
        )

        # Load or create default configuration
        if os.path.exists(self.config_path):
            self.config.read(self.config_path)
        else:
            self._create_default_config()

        self._initialized = True

    def _create_default_config(self):
        """Create default configuration file."""
        self.config[ConfigConstants.SECTION_LOGGING] = {
            ConfigConstants.KEY_LEVEL: ConfigConstants.DEFAULT_LEVEL,
            ConfigConstants.KEY_DETAILED_ARGS: ConfigConstants.DEFAULT_DETAILED,
        }

        self.config[ConfigConstants.SECTION_STATUS_PAGE] = {
            ConfigConstants.KEY_OUTPUT_TYPE: ConfigConstants.DEFAULT_OUTPUT_TYPE,
            ConfigConstants.KEY_OUTPUT_PATH: ConfigConstants.DEFAULT_OUTPUT_PATH,
            ConfigConstants.KEY_PHP_PASSWORD: ConfigConstants.DEFAULT_PHP_PASSWORD,
            ConfigConstants.KEY_PHP_LOGIN_LIBRARY_PATH: ConfigConstants.DEFAULT_PHP_LOGIN_LIBRARY_PATH,
        }

        self.config[ConfigConstants.SECTION_FTP] = {
            ConfigConstants.KEY_FTP_ENABLED: ConfigConstants.DEFAULT_FTP_ENABLED,
            ConfigConstants.KEY_FTP_HOST: ConfigConstants.DEFAULT_FTP_HOST,
            ConfigConstants.KEY_FTP_PORT: ConfigConstants.DEFAULT_FTP_PORT,
            ConfigConstants.KEY_FTP_USERNAME: ConfigConstants.DEFAULT_FTP_USERNAME,
            ConfigConstants.KEY_FTP_PASSWORD: ConfigConstants.DEFAULT_FTP_PASSWORD,
            ConfigConstants.KEY_FTP_REMOTE_PATH: ConfigConstants.DEFAULT_FTP_REMOTE_PATH,
            ConfigConstants.KEY_FTP_PASSIVE_MODE: ConfigConstants.DEFAULT_FTP_PASSIVE_MODE,
            ConfigConstants.KEY_FTP_TIMEOUT: ConfigConstants.DEFAULT_FTP_TIMEOUT,
            ConfigConstants.KEY_FTP_SYNC_INTERVAL: ConfigConstants.DEFAULT_FTP_SYNC_INTERVAL,
        }

        self.config[BotConstants.SECTION] = {
            BotConstants.KEY_TYPE: BotConstants.DEFAULT_TYPE,
            BotConstants.KEY_ALLOW_ADD: BotConstants.DEFAULT_ALLOW_ADD,
            BotConstants.KEY_ALLOW_EDIT: BotConstants.DEFAULT_ALLOW_EDIT,
            BotConstants.KEY_ALLOW_DELETE: BotConstants.DEFAULT_ALLOW_DELETE,
        }

        with open(self.config_path, "w") as configfile:
            self.config.write(configfile)

    def get_logging_level(self) -> str:
        """Get the current logging level."""
        return self.config.get(
            ConfigConstants.SECTION_LOGGING,
            ConfigConstants.KEY_LEVEL,
            fallback=ConfigConstants.DEFAULT_LEVEL,
        )

    def set_logging_level(self, level: str):
        """
        Set the logging level.

        Args:
            level: One of DEBUG, INFO, WARNING, ERROR
        """
        if level not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            raise ValueError("Invalid logging level")

        self.config[ConfigConstants.SECTION_LOGGING][ConfigConstants.KEY_LEVEL] = level
        self._save_config()

    def is_detailed_logging_enabled(self) -> bool:
        """Check if detailed argument logging is enabled."""
        return self.config.getboolean(
            ConfigConstants.SECTION_LOGGING,
            ConfigConstants.KEY_DETAILED_ARGS,
            fallback=False,
        )

    def set_detailed_logging(self, enabled: bool):
        """
        Enable or disable detailed argument logging.

        Args:
            enabled: True to enable detailed logging, False to disable
        """
        self.config[ConfigConstants.SECTION_LOGGING][
            ConfigConstants.KEY_DETAILED_ARGS
        ] = str(enabled).lower()
        self._save_config()

    def _save_config(self):
        """Save current configuration to file."""
        with open(self.config_path, "w") as configfile:
            self.config.write(configfile)

    # StatusPage configuration methods
    def get_output_type(self) -> str:
        """Get the status page output type (html or php)."""
        return self.config.get(
            ConfigConstants.SECTION_STATUS_PAGE,
            ConfigConstants.KEY_OUTPUT_TYPE,
            fallback=ConfigConstants.DEFAULT_OUTPUT_TYPE,
        )

    def set_output_type(self, output_type: str):
        """Set the status page output type."""
        if output_type not in ["html", "php"]:
            raise ValueError("Invalid output type. Must be 'html' or 'php'")
        self._ensure_section(ConfigConstants.SECTION_STATUS_PAGE)
        self.config[ConfigConstants.SECTION_STATUS_PAGE][
            ConfigConstants.KEY_OUTPUT_TYPE
        ] = output_type
        self._save_config()

    def get_output_path(self) -> str:
        """Get the status page output path."""
        return self.config.get(
            ConfigConstants.SECTION_STATUS_PAGE,
            ConfigConstants.KEY_OUTPUT_PATH,
            fallback=ConfigConstants.DEFAULT_OUTPUT_PATH,
        )

    def set_output_path(self, path: str):
        """Set the status page output path."""
        self._ensure_section(ConfigConstants.SECTION_STATUS_PAGE)
        self.config[ConfigConstants.SECTION_STATUS_PAGE][
            ConfigConstants.KEY_OUTPUT_PATH
        ] = path
        self._save_config()

    def get_php_password(self) -> str:
        """Get the PHP login password."""
        return self.config.get(
            ConfigConstants.SECTION_STATUS_PAGE,
            ConfigConstants.KEY_PHP_PASSWORD,
            fallback=ConfigConstants.DEFAULT_PHP_PASSWORD,
        )

    def set_php_password(self, password: str):
        """Set the PHP login password."""
        self._ensure_section(ConfigConstants.SECTION_STATUS_PAGE)
        self.config[ConfigConstants.SECTION_STATUS_PAGE][
            ConfigConstants.KEY_PHP_PASSWORD
        ] = password
        self._save_config()

    def get_php_login_library_path(self) -> str:
        """Get the path to php-simple-login library."""
        return self.config.get(
            ConfigConstants.SECTION_STATUS_PAGE,
            ConfigConstants.KEY_PHP_LOGIN_LIBRARY_PATH,
            fallback=ConfigConstants.DEFAULT_PHP_LOGIN_LIBRARY_PATH,
        )

    def set_php_login_library_path(self, path: str):
        """Set the path to php-simple-login library."""
        self._ensure_section(ConfigConstants.SECTION_STATUS_PAGE)
        self.config[ConfigConstants.SECTION_STATUS_PAGE][
            ConfigConstants.KEY_PHP_LOGIN_LIBRARY_PATH
        ] = path
        self._save_config()

    # FTP configuration methods
    def is_ftp_enabled(self) -> bool:
        """Check if FTP sync is enabled."""
        return self.config.getboolean(
            ConfigConstants.SECTION_FTP, ConfigConstants.KEY_FTP_ENABLED, fallback=False
        )

    def get_ftp_settings(self) -> Dict:
        """Get all FTP settings as a dictionary."""
        return {
            "enabled": self.is_ftp_enabled(),
            "host": self.config.get(
                ConfigConstants.SECTION_FTP,
                ConfigConstants.KEY_FTP_HOST,
                fallback=ConfigConstants.DEFAULT_FTP_HOST,
            ),
            "port": self.config.getint(
                ConfigConstants.SECTION_FTP,
                ConfigConstants.KEY_FTP_PORT,
                fallback=int(ConfigConstants.DEFAULT_FTP_PORT),
            ),
            "username": self.config.get(
                ConfigConstants.SECTION_FTP,
                ConfigConstants.KEY_FTP_USERNAME,
                fallback=ConfigConstants.DEFAULT_FTP_USERNAME,
            ),
            "password": self.config.get(
                ConfigConstants.SECTION_FTP,
                ConfigConstants.KEY_FTP_PASSWORD,
                fallback=ConfigConstants.DEFAULT_FTP_PASSWORD,
            ),
            "remote_path": self.config.get(
                ConfigConstants.SECTION_FTP,
                ConfigConstants.KEY_FTP_REMOTE_PATH,
                fallback=ConfigConstants.DEFAULT_FTP_REMOTE_PATH,
            ),
            "passive_mode": self.config.getboolean(
                ConfigConstants.SECTION_FTP,
                ConfigConstants.KEY_FTP_PASSIVE_MODE,
                fallback=True,
            ),
            "timeout": self.config.getint(
                ConfigConstants.SECTION_FTP,
                ConfigConstants.KEY_FTP_TIMEOUT,
                fallback=int(ConfigConstants.DEFAULT_FTP_TIMEOUT),
            ),
        }

    def set_ftp_settings(self, settings: Dict):
        """Set FTP settings from a dictionary."""
        self._ensure_section(ConfigConstants.SECTION_FTP)
        if "enabled" in settings:
            self.config[ConfigConstants.SECTION_FTP][
                ConfigConstants.KEY_FTP_ENABLED
            ] = str(settings["enabled"]).lower()
        if "host" in settings:
            self.config[ConfigConstants.SECTION_FTP][ConfigConstants.KEY_FTP_HOST] = (
                settings["host"]
            )
        if "port" in settings:
            self.config[ConfigConstants.SECTION_FTP][ConfigConstants.KEY_FTP_PORT] = (
                str(settings["port"])
            )
        if "username" in settings:
            self.config[ConfigConstants.SECTION_FTP][
                ConfigConstants.KEY_FTP_USERNAME
            ] = settings["username"]
        if "password" in settings:
            self.config[ConfigConstants.SECTION_FTP][
                ConfigConstants.KEY_FTP_PASSWORD
            ] = settings["password"]
        if "remote_path" in settings:
            self.config[ConfigConstants.SECTION_FTP][
                ConfigConstants.KEY_FTP_REMOTE_PATH
            ] = settings["remote_path"]
        if "passive_mode" in settings:
            self.config[ConfigConstants.SECTION_FTP][
                ConfigConstants.KEY_FTP_PASSIVE_MODE
            ] = str(settings["passive_mode"]).lower()
        if "timeout" in settings:
            self.config[ConfigConstants.SECTION_FTP][
                ConfigConstants.KEY_FTP_TIMEOUT
            ] = str(settings["timeout"])
        self._save_config()

    def get_ftp_sync_interval(self) -> int:
        """Get minimum minutes between FTP syncs (0 = sync every time)."""
        return self.config.getint(
            ConfigConstants.SECTION_FTP,
            ConfigConstants.KEY_FTP_SYNC_INTERVAL,
            fallback=int(ConfigConstants.DEFAULT_FTP_SYNC_INTERVAL),
        )

    # Bot configuration methods
    def get_bot_type(self) -> str:
        """Get the configured bot type (none, telegram, or xmpp)."""
        return self.config.get(
            BotConstants.SECTION,
            BotConstants.KEY_TYPE,
            fallback=BotConstants.DEFAULT_TYPE,
        )

    def get_bot_setting(self, key: str, fallback: str = "") -> str:
        """Get a bot-specific setting value.

        Args:
            key: The configuration key to retrieve.
            fallback: Value to return if the key is not found.
        """
        return self.config.get(BotConstants.SECTION, key, fallback=fallback)

    def is_bot_command_allowed(self, command: str) -> bool:
        """Check if a bot command is allowed.

        Args:
            command: The command key to check (e.g., allow_add, allow_edit, allow_delete).
        """
        return self.config.getboolean(BotConstants.SECTION, command, fallback=False)

    def get_bot_config(self) -> "BotConfig":
        """Get bot configuration as a BotConfig DTO."""
        from .bot.command_processor import BotConfig

        return BotConfig(
            allow_add=self.is_bot_command_allowed(BotConstants.KEY_ALLOW_ADD),
            allow_edit=self.is_bot_command_allowed(BotConstants.KEY_ALLOW_EDIT),
            allow_delete=self.is_bot_command_allowed(BotConstants.KEY_ALLOW_DELETE),
        )

    def _ensure_section(self, section: str):
        """Ensure a configuration section exists."""
        if section not in self.config:
            self.config[section] = {}
