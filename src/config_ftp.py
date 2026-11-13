"""FTP configuration reads and writes."""
from configparser import ConfigParser
from typing import Callable, Dict

from .constants import Config as ConfigConstants


def get_ftp_settings(config: ConfigParser) -> Dict:
    """Read FTP settings with the same defaults and types as Config."""
    return {
        "enabled": config.getboolean(
            ConfigConstants.SECTION_FTP,
            ConfigConstants.KEY_FTP_ENABLED,
            fallback=False,
        ),
        "host": config.get(
            ConfigConstants.SECTION_FTP,
            ConfigConstants.KEY_FTP_HOST,
            fallback=ConfigConstants.DEFAULT_FTP_HOST,
        ),
        "port": config.getint(
            ConfigConstants.SECTION_FTP,
            ConfigConstants.KEY_FTP_PORT,
            fallback=int(ConfigConstants.DEFAULT_FTP_PORT),
        ),
        "username": config.get(
            ConfigConstants.SECTION_FTP,
            ConfigConstants.KEY_FTP_USERNAME,
            fallback=ConfigConstants.DEFAULT_FTP_USERNAME,
        ),
        "password": config.get(
            ConfigConstants.SECTION_FTP,
            ConfigConstants.KEY_FTP_PASSWORD,
            fallback=ConfigConstants.DEFAULT_FTP_PASSWORD,
        ),
        "remote_path": config.get(
            ConfigConstants.SECTION_FTP,
            ConfigConstants.KEY_FTP_REMOTE_PATH,
            fallback=ConfigConstants.DEFAULT_FTP_REMOTE_PATH,
        ),
        "passive_mode": config.getboolean(
            ConfigConstants.SECTION_FTP,
            ConfigConstants.KEY_FTP_PASSIVE_MODE,
            fallback=True,
        ),
        "timeout": config.getint(
            ConfigConstants.SECTION_FTP,
            ConfigConstants.KEY_FTP_TIMEOUT,
            fallback=int(ConfigConstants.DEFAULT_FTP_TIMEOUT),
        ),
    }


def set_ftp_settings(
    config: ConfigParser,
    settings: Dict,
    save_config: Callable[[], None],
) -> None:
    """Update provided FTP settings and persist the configuration."""
    section = ConfigConstants.SECTION_FTP
    if section not in config:
        config[section] = {}

    values = {
        "enabled": ConfigConstants.KEY_FTP_ENABLED,
        "host": ConfigConstants.KEY_FTP_HOST,
        "port": ConfigConstants.KEY_FTP_PORT,
        "username": ConfigConstants.KEY_FTP_USERNAME,
        "password": ConfigConstants.KEY_FTP_PASSWORD,
        "remote_path": ConfigConstants.KEY_FTP_REMOTE_PATH,
        "passive_mode": ConfigConstants.KEY_FTP_PASSIVE_MODE,
        "timeout": ConfigConstants.KEY_FTP_TIMEOUT,
    }
    for key, config_key in values.items():
        if key not in settings:
            continue
        value = settings[key]
        if key in ("enabled", "passive_mode"):
            value = str(value).lower()
        elif key in ("port", "timeout"):
            value = str(value)
        config[section][config_key] = value

    save_config()
