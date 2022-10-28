import sys
from typing import Iterable

import pytest
from _pytest.main import Session
from _pytest.terminal import _plugin_nameversions
from rich.columns import Columns
from rich.console import Group
from rich.panel import Panel


def generate_header_panel(
    session: Session, title: str = "pytest session starts"
) -> Panel:
    columns = [
        _generate_sysinfo_col(),
        _generate_root_col(session),
        *_generate_plugins_col(session),
    ]

    return Panel(Group(*columns), title=title)


def _generate_sysinfo_col() -> Columns:
    column = Columns(
        [
            f"platform [green]{sys.platform}",
            f"pytest [cyan]{pytest.__version__}",
            f"python [cyan]{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        ]
    )

    pypy_version_info = getattr(sys, "pypy_version_info", None)
    if pypy_version_info is not None:
        column.add_renderable(f"pypy [cyan]{'.'.join(map(str, pypy_version_info[:3]))}")

    return column


def _generate_root_col(session: Session) -> Columns:
    return Columns([f"root [cyan][bold]{session.config.rootpath}"])


def _generate_plugins_col(session: Session) -> Iterable[Columns]:
    plugins = session.config.pluginmanager.list_plugin_distinfo()

    if plugins:
        yield Columns(
            [
                f"plugins [cyan]{', '.join(_plugin_nameversions(plugins))}",
            ]
        )
