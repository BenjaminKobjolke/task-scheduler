"""Lifecycle commands: ask a running scheduler instance to shut down."""

import sys

from src.cli_output import CliOutput
from src.constants import Defaults, Messages
from src.instance_controller import InstanceController


def handle_shutdown(cli: CliOutput) -> None:
    """Ask a running scheduler instance to stop and wait for it to exit."""
    controller = InstanceController()

    if not controller.is_running():
        cli.info(Messages.NO_INSTANCE_RUNNING)
        return

    cli.info(Messages.SHUTDOWN_SENT)
    if controller.stop_running():
        cli.info(Messages.SHUTDOWN_CONFIRMED)
    else:
        cli.error(
            Messages.SHUTDOWN_TIMEOUT.format(seconds=Defaults.SHUTDOWN_WAIT_SECONDS)
        )
        sys.exit(1)
