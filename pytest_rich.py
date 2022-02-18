"""
Proof of concept for pytest + rich integration.
"""
import sys
import warnings
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Union

import attr
import pytest
from _pytest._code.code import ExceptionRepr
from rich.columns import Columns
from rich.console import Console
from rich.console import Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress
from rich.progress import SpinnerColumn
from rich.progress import TaskID
from rich.rule import Rule

if sys.version_info < (3, 8):
    from typing_extensions import Literal
else:
    from typing import Literal


def pytest_addoption(parser):
    parser.addoption("--rich", action="store_true", default=False)


@pytest.mark.trylast
def pytest_configure(config):

    if sys.stdout.isatty() and config.getoption("rich"):
        # Get the standard terminal reporter plugin and replace it with our
        standard_reporter = config.pluginmanager.getplugin("terminalreporter")
        config.pluginmanager.unregister(standard_reporter)
        config.pluginmanager.register(
            RichTerminalReporter(config), "rich-terminal-reporter"
        )


@attr.s(auto_attribs=True, hash=True)
class RichTerminalReporter:
    config: pytest.Config
    console: Console = attr.Factory(Console)

    Status = Literal["collected", "running", "success", "fail", "error"]

    def __attrs_post_init__(self):
        self.collect_progress: Optional[Progress] = None
        self.runtest_progress: Optional[Progress] = None
        self.total_items_collected = 0
        self.total_items_completed = 0
        self.items_per_file: Dict[Path, List[pytest.Item]] = {}
        self.status_per_item: Dict[str, RichTerminalReporter.Status] = {}
        self.items: Dict[str, pytest.Item] = {}
        self.runtest_tasks_per_file: Dict[Path, TaskID] = {}
        self.failed_reports: Dict[str, pytest.TestReport] = {}

        self.summary: Optional[Live] = None

    def pytest_collection(self) -> None:
        self.collect_progress = Progress(
            "[progress.description]{task.description}",
        )
        self.collect_task = self.collect_progress.add_task("[cyan][bold]Collecting")
        self.collect_progress.start()

    def pytest_collectreport(self, report: pytest.CollectReport) -> None:
        items = [x for x in report.result if isinstance(x, pytest.Item)]
        if items:
            for item in items:
                self.items_per_file.setdefault(item.path, []).append(item)
                self.status_per_item[item.nodeid] = "collected"
                self.items[item.nodeid] = item
            self.total_items_collected += len(items)
            self.collect_progress.update(
                self.collect_task,
                description=f"[cyan][bold]Collecting[/cyan] [magenta]{report.nodeid}[/magenta] ([green]{self.total_items_collected}[/green] total items)",
                refresh=True,
            )

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        self.collect_progress.update(
            self.collect_task,
            description=f"[cyan][bold]Collected [green]{self.total_items_collected} [cyan]items",
            completed=True,
        )
        self.collect_progress.stop()
        self.collect_progress = None
        self.collect_task = None

    def pytest_sessionstart(self, session: pytest.Session) -> None:
        py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        column1 = Columns(
            [
                f"platform [green]{sys.platform}",
                f"pytest [cyan]{pytest.__version__}",
                f"python [cyan]{py_version}",
            ]
        )
        column2 = Columns([f"root [cyan][bold]{session.config.rootpath}"])
        self.console.print(
            Panel(Group(column1, column2), title=f"pytest session starts")
        )

    def pytest_internalerror(self, excrepr: ExceptionRepr) -> None:
        ...

    def pytest_warning_recorded(
        self,
        warning_message: warnings.WarningMessage,
        nodeid: str,
    ) -> None:
        ...

    def pytest_deselected(self, items: Sequence[pytest.Item]) -> None:
        ...

    def pytest_plugin_registered(self, plugin) -> None:
        ...

    def pytest_runtest_logstart(
        self, nodeid: str, location: Tuple[str, Optional[int], str]
    ) -> None:
        if self.runtest_progress is None:
            self.runtest_progress = Progress(SpinnerColumn(), "{task.description}")
            self.runtest_progress.start()

            for fn in self.items_per_file:
                total_items = self.items_per_file[fn]
                task = self.runtest_progress.add_task(
                    str(fn.relative_to(self.config.rootpath)),
                    total=len(total_items),
                    visible=False,
                )
                self.runtest_tasks_per_file[fn] = task
            self.overall_progress_task = self.runtest_progress.add_task(
                "Progress", total=self.total_items_collected
            )

        self._update_task(nodeid)

    def _get_status_char(self, status: Status) -> str:
        # ["collected", "running", "success", "fail", "error"]
        if status == "collected":
            return ""
        elif status == "running":
            return ""
        elif status == "success":
            return "[green]✔[/green]"
        elif status == "fail":
            return "[red]❌[/red]"
        elif status == "error":
            return "[red]E[/red]"
        else:
            assert 0

    def _update_task(self, nodeid: str):
        base_fn = nodeid.split("::")[0]
        fn = self.config.rootpath / base_fn
        task = self.runtest_tasks_per_file[fn]
        current_item = self.items[nodeid]
        items = self.items_per_file[current_item.path]
        chars = []
        statuses = []
        for item in items:
            status = self.status_per_item[item.nodeid]
            statuses.append(status)
            chars.append(self._get_status_char(status))
        completed_count = [x for x in statuses if x in ("success", "fail")]
        completed = len(completed_count) == len(items)
        percent = len(completed_count) * 100 // len(items)
        description = f"[cyan][{percent:3d}%] [/cyan]{base_fn} " + "".join(chars)
        self.runtest_progress.update(
            task,
            description=description,
            refresh=True,
            completed=completed,
            visible=True,
        )

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        status: Optional[RichTerminalReporter.Status] = None
        if report.when == "setup":
            status = "running"
        elif report.when == "call":
            status = "success" if report.outcome == "passed" else "fail"
        if report.outcome != "passed":
            self.failed_reports[report.nodeid] = report
        if status is not None:
            self.status_per_item[report.nodeid] = status
            self._update_task(report.nodeid)

    def pytest_runtest_logfinish(self) -> None:
        self.total_items_completed += 1
        percent = (self.total_items_completed * 100) // self.total_items_collected
        self.runtest_progress.update(
            self.overall_progress_task,
            description=f"Percent: [green]{percent}%[/green]",
        )

    def pytest_sessionfinish(
        self, session: pytest.Session, exitstatus: Union[int, pytest.ExitCode]
    ):
        if self.runtest_progress is not None:
            self.runtest_progress.stop()
            self.runtest_progress = None
            self.runtest_tasks_per_file.clear()
        for nodeid, report in self.failed_reports.items():
            m = Markdown(f"```python-traceback\n{report.longrepr}\n```")
            self.console.print(Rule(f"[magenta]{nodeid}[/magenta]", style="red"))
            self.console.print(m)

    def pytest_keyboard_interrupt(
        self, excinfo: pytest.ExceptionInfo[BaseException]
    ) -> None:
        ...

    def pytest_unconfigure(self) -> None:
        ...
