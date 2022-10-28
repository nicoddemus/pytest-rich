import sys

import pytest
from _pytest.main import Session
from _pytest.terminal import _plugin_nameversions
from attrs import define
from attrs import field
from rich.columns import Columns
from rich.console import Console
from rich.console import ConsoleOptions
from rich.console import Group
from rich.console import RenderResult
from rich.panel import Panel


@define
class RichTerminalHeader:
    session: Session
    title: str = "pytest session starts"
    columns: list = field(factory=list)

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        self._generate_sysinfo_col()
        self._generate_root_col()
        self._generate_plugins_col()

        yield Panel(Group(*self.columns), title=self.title)

    def _generate_sysinfo_col(self) -> None:
        self.columns.append(
            Columns(
                [
                    f"platform [green]{sys.platform}",
                    f"pytest [cyan]{pytest.__version__}",
                    f"python [cyan]{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                ]
            )
        )

        if hasattr(sys, "pypy_version_info"):
            # mypy isn't happy with `sys.pypy_version_info` when running
            # on CPython, which is where we typically run mypy, so we need
            # to ignore it
            self.columns[-1].add_renderable(
                f"pypy [cyan]{'.'.join(map(str, sys.pypy_version_info[:3]))}"  # type: ignore [attr-defined]
            )

    def _generate_root_col(self) -> None:
        root = self.session.config.rootpath

        self.columns.append(Columns([f"root [cyan][bold]{root}"]))

    def _generate_plugins_col(self) -> None:
        plugins = self.session.config.pluginmanager.list_plugin_distinfo()

        if plugins:
            self.columns.append(
                Columns(
                    [
                        f"plugins [cyan]{', '.join(_plugin_nameversions(plugins))}",
                    ]
                )
            )
