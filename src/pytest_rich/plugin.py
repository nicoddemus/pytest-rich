"""
Proof of concept for pytest + rich integration.
"""
import datetime
import sys

import pytest

from pytest_rich.terminal import RichTerminalReporter


def pytest_addoption(parser):
    group = parser.getgroup("rich", "pytest-rich", after="terminal reporting")
    group.addoption(
        "--rich",
        action="store_true",
        default=False,
        help="Enable rich terminal reporting using pytest-rich",
    )
    group.addoption(
        "--rich-capture",
        action="store_true",
        default=False,
        help="Capture terminal output using rich",
    )
    group.addoption(
        "--rich-capture-file-name",
        action="store",
        default=f"{__name__.split('.')[0]}-{datetime.datetime.now().isoformat().replace(':', '.')}",
        help="File name to use for rich terminal capture (only if --rich-capture is also enabled). Default is <module name>-<datetime>",
    )
    group.addoption(
        "--rich-capture-file-type",
        action="store",
        choices=["svg", "html", "txt"],
        default="svg",
        help="File type to use for rich terminal capture (only if --rich-capture is also enabled). Default: svg.",
    )


@pytest.hookimpl(trylast=True)
def pytest_configure(config):
    if sys.stdout.isatty() and config.getoption("rich"):
        standard_reporter = config.pluginmanager.getplugin("terminalreporter")
        config.pluginmanager.unregister(standard_reporter)
        config.pluginmanager.register(
            RichTerminalReporter(config), "rich-terminal-reporter"
        )
