"""
Proof of concept for pytest + rich integration.
"""
import sys

import pytest

from pytest_rich.terminal import RichTerminalReporter


def pytest_addoption(parser):
    parser.addoption("--rich", action="store_true", default=False)


@pytest.hookimpl(trylast=True)
def pytest_configure(config):
    if sys.stdout.isatty() and config.getoption("rich"):
        standard_reporter = config.pluginmanager.getplugin("terminalreporter")
        config.pluginmanager.unregister(standard_reporter)
        config.pluginmanager.register(
            RichTerminalReporter(config), "rich-terminal-reporter"
        )
