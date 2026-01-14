"""PHP Simple Login library handler for status page authentication."""

import os
import shutil
from .logger import Logger
from .config import Config


class PhpLoginHandler:
    """Handles copying and configuring the php-simple-login library."""

    PHP_AUTH_HEADER = '''<?php
require_once __DIR__ . '/simple-login-config.php';
require_once __DIR__ . '/lib/simple-login/Session.php';
require_once __DIR__ . '/lib/simple-login/SimpleLogin.php';

use BenjaminKobjolke\\SimpleLogin\\SimpleLogin;
SimpleLogin::requireAuth();
?>
'''

    def __init__(self):
        """Initialize the PHP login handler."""
        self.logger = Logger("PhpLoginHandler")
        self.config = Config()

    def setup_php_login(self, output_dir: str) -> bool:
        """
        Set up PHP login files in the output directory.

        Args:
            output_dir: The directory where PHP files will be created

        Returns:
            True if setup was successful, False otherwise
        """
        try:
            library_path = self.config.get_php_login_library_path()
            if not library_path:
                self.logger.error("PHP login library path not configured")
                return False

            src_dir = os.path.join(library_path, "src")
            if not os.path.exists(src_dir):
                self.logger.error(f"PHP login library not found at: {src_dir}")
                return False

            # Create lib/simple-login directory
            lib_dir = os.path.join(output_dir, "lib", "simple-login")
            os.makedirs(lib_dir, exist_ok=True)

            # Copy PHP library files
            files_to_copy = ["SimpleLogin.php", "Session.php"]
            for filename in files_to_copy:
                src_file = os.path.join(src_dir, filename)
                dst_file = os.path.join(lib_dir, filename)
                if os.path.exists(src_file):
                    shutil.copy2(src_file, dst_file)
                    self.logger.info(f"Copied {filename} to {lib_dir}")
                else:
                    self.logger.warning(f"PHP library file not found: {src_file}")

            # Generate config file
            self._generate_config_file(output_dir)

            return True
        except Exception as e:
            self.logger.error(f"Error setting up PHP login: {str(e)}")
            return False

    def _generate_config_file(self, output_dir: str):
        """Generate the PHP config file with password."""
        password = self.config.get_php_password()
        config_content = f"""<?php
define('SIMPLE_LOGIN_PASSWORD', '{password}');
"""
        config_path = os.path.join(output_dir, "simple-login-config.php")
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        self.logger.info(f"Generated PHP config at {config_path}")

    def wrap_html_with_php(self, html_content: str) -> str:
        """
        Wrap HTML content with PHP authentication header.

        Args:
            html_content: The original HTML content

        Returns:
            HTML content wrapped with PHP authentication
        """
        return self.PHP_AUTH_HEADER + html_content

    def get_file_extension(self) -> str:
        """Get the appropriate file extension based on output type."""
        output_type = self.config.get_output_type()
        return ".php" if output_type == "php" else ".html"
