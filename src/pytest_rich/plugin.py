"""
Proof of concept for pytest + rich integration.
"""
import sys

import pytest

from pytest_rich.terminal import RichTerminalReporter


def pytest_addoption(parser):
    parser.addoption("--rich", action="store_true", default=False)


@pytest.mark.trylast
def pytest_configure(config):
    if sys.stdout.isatty() and config.getoption("rich"):
        # Get the standard terminal reporter plugin and replace it with ours
        standard_reporter = config.pluginmanager.getplugin("terminalreporter")
        config.pluginmanager.unregister(standard_reporter)
        config.pluginmanager.register(
            RichTerminalReporter(config), "rich-terminal-reporter"
        )
