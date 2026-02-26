"""Tests for bot configuration methods in config module."""
import configparser
import os

import pytest

import src.config as config_module
from src.bot.types import BotConfig
from src.constants import Bot as BotConstants


@pytest.fixture(autouse=True)
def reset_config_singleton():
    """Reset the Config singleton before each test."""
    config_module.Config._instance = None
    yield
    config_module.Config._instance = None


@pytest.fixture
def config_with_defaults(tmp_path):
    """Create a Config instance with default config in a temp directory."""
    config_path = os.path.join(str(tmp_path), "config.ini")
    config = config_module.Config()
    config.config_path = config_path
    config.config = configparser.ConfigParser()
    config._create_default_config()
    return config


@pytest.fixture
def config_with_telegram(tmp_path):
    """Create a Config instance with Telegram bot settings."""
    config_path = os.path.join(str(tmp_path), "config.ini")
    config = config_module.Config()
    config.config_path = config_path
    config.config = configparser.ConfigParser()
    config._create_default_config()

    # Override with Telegram settings
    config.config[BotConstants.SECTION][BotConstants.KEY_TYPE] = BotConstants.TYPE_TELEGRAM
    config.config[BotConstants.SECTION][BotConstants.KEY_BOT_TOKEN] = "test-token-123"
    config.config[BotConstants.SECTION][BotConstants.KEY_CHANNEL_ID] = "chan-456"
    config.config[BotConstants.SECTION][BotConstants.KEY_ALLOWED_USER_IDS] = "111,222"
    return config


@pytest.fixture
def config_with_xmpp(tmp_path):
    """Create a Config instance with XMPP bot settings."""
    config_path = os.path.join(str(tmp_path), "config.ini")
    config = config_module.Config()
    config.config_path = config_path
    config.config = configparser.ConfigParser()
    config._create_default_config()

    # Override with XMPP settings
    config.config[BotConstants.SECTION][BotConstants.KEY_TYPE] = BotConstants.TYPE_XMPP
    config.config[BotConstants.SECTION][BotConstants.KEY_JID] = "bot@example.com"
    config.config[BotConstants.SECTION][BotConstants.KEY_PASSWORD] = "secret"
    config.config[BotConstants.SECTION][BotConstants.KEY_DEFAULT_RECEIVER] = "user@example.com"
    config.config[BotConstants.SECTION][BotConstants.KEY_ALLOWED_JIDS] = "user@example.com,admin@example.com"
    return config


class TestDefaultBotConfig:
    """Tests for default bot configuration values."""

    def test_default_bot_type_is_none(self, config_with_defaults) -> None:
        assert config_with_defaults.get_bot_type() == BotConstants.TYPE_NONE

    def test_default_config_has_bot_section(self, config_with_defaults) -> None:
        assert BotConstants.SECTION in config_with_defaults.config

    def test_default_allow_add_is_true(self, config_with_defaults) -> None:
        assert config_with_defaults.is_bot_command_allowed(BotConstants.KEY_ALLOW_ADD) is True

    def test_default_allow_edit_is_true(self, config_with_defaults) -> None:
        assert config_with_defaults.is_bot_command_allowed(BotConstants.KEY_ALLOW_EDIT) is True

    def test_default_allow_delete_is_true(self, config_with_defaults) -> None:
        assert config_with_defaults.is_bot_command_allowed(BotConstants.KEY_ALLOW_DELETE) is True


class TestGetBotType:
    """Tests for get_bot_type method."""

    def test_returns_none_for_default(self, config_with_defaults) -> None:
        assert config_with_defaults.get_bot_type() == BotConstants.TYPE_NONE

    def test_returns_telegram_when_configured(self, config_with_telegram) -> None:
        assert config_with_telegram.get_bot_type() == BotConstants.TYPE_TELEGRAM

    def test_returns_xmpp_when_configured(self, config_with_xmpp) -> None:
        assert config_with_xmpp.get_bot_type() == BotConstants.TYPE_XMPP


class TestGetBotSetting:
    """Tests for get_bot_setting method."""

    def test_get_telegram_token(self, config_with_telegram) -> None:
        assert config_with_telegram.get_bot_setting(BotConstants.KEY_BOT_TOKEN) == "test-token-123"

    def test_get_telegram_channel_id(self, config_with_telegram) -> None:
        assert config_with_telegram.get_bot_setting(BotConstants.KEY_CHANNEL_ID) == "chan-456"

    def test_get_telegram_allowed_user_ids(self, config_with_telegram) -> None:
        assert config_with_telegram.get_bot_setting(BotConstants.KEY_ALLOWED_USER_IDS) == "111,222"

    def test_get_xmpp_jid(self, config_with_xmpp) -> None:
        assert config_with_xmpp.get_bot_setting(BotConstants.KEY_JID) == "bot@example.com"

    def test_get_xmpp_password(self, config_with_xmpp) -> None:
        assert config_with_xmpp.get_bot_setting(BotConstants.KEY_PASSWORD) == "secret"

    def test_get_xmpp_default_receiver(self, config_with_xmpp) -> None:
        assert config_with_xmpp.get_bot_setting(BotConstants.KEY_DEFAULT_RECEIVER) == "user@example.com"

    def test_get_xmpp_allowed_jids(self, config_with_xmpp) -> None:
        assert config_with_xmpp.get_bot_setting(BotConstants.KEY_ALLOWED_JIDS) == "user@example.com,admin@example.com"

    def test_get_missing_setting_returns_fallback(self, config_with_defaults) -> None:
        assert config_with_defaults.get_bot_setting(BotConstants.KEY_BOT_TOKEN) == ""

    def test_get_missing_setting_custom_fallback(self, config_with_defaults) -> None:
        assert config_with_defaults.get_bot_setting(BotConstants.KEY_BOT_TOKEN, fallback="default") == "default"


class TestIsBotCommandAllowed:
    """Tests for is_bot_command_allowed method."""

    def test_allow_add_true_by_default(self, config_with_defaults) -> None:
        assert config_with_defaults.is_bot_command_allowed(BotConstants.KEY_ALLOW_ADD) is True

    def test_allow_edit_true_by_default(self, config_with_defaults) -> None:
        assert config_with_defaults.is_bot_command_allowed(BotConstants.KEY_ALLOW_EDIT) is True

    def test_allow_delete_true_by_default(self, config_with_defaults) -> None:
        assert config_with_defaults.is_bot_command_allowed(BotConstants.KEY_ALLOW_DELETE) is True

    def test_allow_add_disabled(self, config_with_defaults) -> None:
        config_with_defaults.config[BotConstants.SECTION][BotConstants.KEY_ALLOW_ADD] = "false"
        assert config_with_defaults.is_bot_command_allowed(BotConstants.KEY_ALLOW_ADD) is False

    def test_allow_edit_disabled(self, config_with_defaults) -> None:
        config_with_defaults.config[BotConstants.SECTION][BotConstants.KEY_ALLOW_EDIT] = "false"
        assert config_with_defaults.is_bot_command_allowed(BotConstants.KEY_ALLOW_EDIT) is False

    def test_allow_delete_disabled(self, config_with_defaults) -> None:
        config_with_defaults.config[BotConstants.SECTION][BotConstants.KEY_ALLOW_DELETE] = "false"
        assert config_with_defaults.is_bot_command_allowed(BotConstants.KEY_ALLOW_DELETE) is False

    def test_unknown_command_returns_false(self, config_with_defaults) -> None:
        assert config_with_defaults.is_bot_command_allowed("allow_unknown") is False


class TestGetBotConfig:
    """Tests for get_bot_config method."""

    def test_returns_bot_config_dto(self, config_with_defaults) -> None:
        bot_config = config_with_defaults.get_bot_config()
        assert isinstance(bot_config, BotConfig)

    def test_default_bot_config_values(self, config_with_defaults) -> None:
        bot_config = config_with_defaults.get_bot_config()
        assert bot_config.bot_type == BotConstants.TYPE_NONE
        assert bot_config.allow_add is True
        assert bot_config.allow_edit is True
        assert bot_config.allow_delete is True

    def test_telegram_bot_config(self, config_with_telegram) -> None:
        bot_config = config_with_telegram.get_bot_config()
        assert bot_config.bot_type == BotConstants.TYPE_TELEGRAM
        assert bot_config.allow_add is True
        assert bot_config.allow_edit is True
        assert bot_config.allow_delete is True

    def test_bot_config_with_disabled_commands(self, config_with_defaults) -> None:
        config_with_defaults.config[BotConstants.SECTION][BotConstants.KEY_ALLOW_ADD] = "false"
        config_with_defaults.config[BotConstants.SECTION][BotConstants.KEY_ALLOW_DELETE] = "false"
        bot_config = config_with_defaults.get_bot_config()
        assert bot_config.allow_add is False
        assert bot_config.allow_edit is True
        assert bot_config.allow_delete is False

    def test_bot_config_is_frozen(self, config_with_defaults) -> None:
        bot_config = config_with_defaults.get_bot_config()
        with pytest.raises(AttributeError):
            bot_config.bot_type = "telegram"  # type: ignore[misc]


class TestBotConfigPersistence:
    """Tests for bot config persistence in default config file."""

    def test_bot_section_persisted_to_file(self, tmp_path) -> None:
        config_path = os.path.join(str(tmp_path), "config.ini")
        config = config_module.Config()
        config.config_path = config_path
        config.config = configparser.ConfigParser()
        config._create_default_config()

        # Read the file directly
        parser = configparser.ConfigParser()
        parser.read(config_path)

        assert BotConstants.SECTION in parser
        assert parser.get(BotConstants.SECTION, BotConstants.KEY_TYPE) == BotConstants.DEFAULT_TYPE
        assert parser.get(BotConstants.SECTION, BotConstants.KEY_ALLOW_ADD) == BotConstants.DEFAULT_ALLOW_ADD
        assert parser.get(BotConstants.SECTION, BotConstants.KEY_ALLOW_EDIT) == BotConstants.DEFAULT_ALLOW_EDIT
        assert parser.get(BotConstants.SECTION, BotConstants.KEY_ALLOW_DELETE) == BotConstants.DEFAULT_ALLOW_DELETE
