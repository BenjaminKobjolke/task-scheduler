"""Tests for config module."""

import os
import tempfile
import configparser
import pytest

# We need to reset the singleton for each test
# Import the module itself to access the class
import src.config as config_module


@pytest.fixture(autouse=True)
def reset_config_singleton():
    """Reset the Config singleton before each test."""
    config_module.Config._instance = None
    yield
    config_module.Config._instance = None


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory with a config file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestConfigDefaults:
    """Tests for default configuration values."""

    def test_default_logging_level(self, temp_config_dir, monkeypatch):
        # Point the config to a temp location
        config_path = os.path.join(temp_config_dir, "config.ini")

        # Create fresh config with new path
        config = config_module.Config()
        config.config_path = config_path
        config.config = configparser.ConfigParser()
        config._create_default_config()

        assert config.get_logging_level() == "INFO"

    def test_default_detailed_logging_disabled(self, temp_config_dir):
        config_path = os.path.join(temp_config_dir, "config.ini")

        config = config_module.Config()
        config.config_path = config_path
        config.config = configparser.ConfigParser()
        config._create_default_config()

        assert config.is_detailed_logging_enabled() is False


class TestConfigSetLoggingLevel:
    """Tests for set_logging_level method."""

    def test_set_valid_level(self, temp_config_dir):
        config_path = os.path.join(temp_config_dir, "config.ini")

        config = config_module.Config()
        config.config_path = config_path
        config._initialized = False
        config.__init__()

        config.set_logging_level("DEBUG")
        assert config.get_logging_level() == "DEBUG"

    def test_set_invalid_level(self, temp_config_dir):
        config_path = os.path.join(temp_config_dir, "config.ini")

        config = config_module.Config()
        config.config_path = config_path
        config._initialized = False
        config.__init__()

        with pytest.raises(ValueError, match="Invalid logging level"):
            config.set_logging_level("INVALID")


class TestConfigSetDetailedLogging:
    """Tests for set_detailed_logging method."""

    def test_enable_detailed_logging(self, temp_config_dir):
        config_path = os.path.join(temp_config_dir, "config.ini")

        config = config_module.Config()
        config.config_path = config_path
        config._initialized = False
        config.__init__()

        config.set_detailed_logging(True)
        assert config.is_detailed_logging_enabled() is True

    def test_disable_detailed_logging(self, temp_config_dir):
        config_path = os.path.join(temp_config_dir, "config.ini")

        config = config_module.Config()
        config.config_path = config_path
        config._initialized = False
        config.__init__()

        config.set_detailed_logging(True)
        config.set_detailed_logging(False)
        assert config.is_detailed_logging_enabled() is False


class TestConfigPersistence:
    """Tests for configuration persistence."""

    def test_config_saved_to_file(self, temp_config_dir):
        config_path = os.path.join(temp_config_dir, "config.ini")

        # Create fresh config instance
        config = config_module.Config()
        # Override the path before initialization
        original_path = config.config_path
        config.config_path = config_path
        config.config = configparser.ConfigParser()
        config._create_default_config()

        config.set_logging_level("WARNING")

        # Read the file directly to verify persistence
        parser = configparser.ConfigParser()
        parser.read(config_path)

        assert parser.get("Logging", "level") == "WARNING"

        # Restore original path
        config.config_path = original_path
