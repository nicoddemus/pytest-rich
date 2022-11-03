"""
Proof of concept for pytest + rich integration.
"""
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
        action="store",
        nargs="?",
        type=str,
        const="",
        help="Capture terminal output using rich. Takes an optional string to supply the file name and/or type.\n"
        "File name: defaults to 'pytest_rich' plus a UTC timestamp\n"
        "File types: 'svg' (default), 'html', 'txt' \n"
        "Examples:\n"
        "--rich-capture         => 'pytest_rich-20200101_000000.svg'\n"
        "--rich-capture=out     => 'out.svg'\n"
        "--rich-capture=out.txt => 'out.txt'\n"
        "--rich-capture=.txt    => 'pytest_rich-20200101_000000.txt'\n"
        "--rich-capture=txt     => 'pytest_rich-20200101_000000.txt'\n",
    )


@pytest.hookimpl(trylast=True)
def pytest_configure(config):
    if sys.stdout.isatty() and config.getoption("rich"):
        standard_reporter = config.pluginmanager.getplugin("terminalreporter")
        config.pluginmanager.unregister(standard_reporter)
        config.pluginmanager.register(
            RichTerminalReporter(config), "rich-terminal-reporter"
        )
