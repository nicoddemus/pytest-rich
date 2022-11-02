import sys
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Union

import attr
import pytest
from _pytest._code.code import ExceptionChainRepr
from _pytest._code.code import ExceptionRepr
from rich.console import Console
from rich.live import Live
from rich.padding import Padding
from rich.panel import Panel
from rich.progress import Progress
from rich.progress import SpinnerColumn
from rich.progress import TaskID
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from pytest_rich.header import generate_header_panel
from pytest_rich.traceback import RichExceptionChainRepr

if sys.version_info < (3, 8):
    from typing_extensions import Literal
else:
    from typing import Literal

HORIZONTAL_PAD = (0, 1, 0, 1)


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
        self.categorized_reports: Dict[str, List[pytest.TestReport]] = defaultdict(list)
        self.summary: Optional[Live] = None
        self.total_duration: float = 0

    def _preserve_report(self, report) -> None:
        self.categorized_reports[report.outcome].append(report)
        self.total_duration += report.duration

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
            if self.collect_progress is not None:
                self.collect_progress.update(
                    self.collect_task,
                    description=f"[cyan][bold]Collecting[/cyan] [magenta]{report.nodeid}[/magenta] ([green]{self.total_items_collected}[/green] total items)",
                    refresh=True,
                )

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        if self.collect_progress is not None:
            self.collect_progress.update(
                self.collect_task,
                description=f"[cyan][bold]Collected [green]{self.total_items_collected} [cyan]items",
                completed=True,
            )
            self.collect_progress.stop()
            self.collect_progress = None

    def pytest_sessionstart(self, session: pytest.Session) -> None:
        self.console.print(Rule("pytest session starts", style="default"))

        if self.no_header is False:
            header = generate_header_panel(session)

            self.console.print(header)

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
        if self.runtest_progress is not None:
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
            self._preserve_report(report)
        if status is not None:
            self.status_per_item[report.nodeid] = status
            self._update_task(report.nodeid)

    def pytest_runtest_logfinish(self) -> None:
        self.total_items_completed += 1
        percent = (self.total_items_completed * 100) // self.total_items_collected
        if self.runtest_progress is not None:
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

        if self.no_summary is False:
            error_messages = {}
            for index, report in enumerate(self.categorized_reports["failed"]):
                if index == 0:
                    self.console.print(Rule("FAILURES\n", style="bold red"))
                nodeid = report.nodeid
                assert isinstance(report.longrepr, ExceptionChainRepr)
                tb = RichExceptionChainRepr(nodeid, report.longrepr)
                error_messages[nodeid] = tb.error_messages
                self.console.print(tb)

            if self.verbosity_level >= 0:
                self.print_summary(error_messages)

        status = "SUCCEEDED" if exitstatus == 0 else "FAILED"

        self.console.print(
            Rule(
                title=f"{status} in {self.total_duration:.2f} seconds",
                style="green" if status == "SUCCEEDED" else "red",
            )
        )

    def print_summary(self, error_messages):
        summary_table = Table.grid()
        summary_table.add_column(justify="right")
        summary_table.add_column()
        summary_table.add_column()

        summary_table.add_row(
            Padding(
                str(self.total_items_completed),
                pad=HORIZONTAL_PAD,
                style="bold cyan",
            ),
            Padding(
                "Total Tests",
                pad=HORIZONTAL_PAD,
            ),
            style="default",
        )

        style_dict = {
            "passed": "bold green",
            "failed": "bold red",
            "skipped": "bold yellow",
        }
        for state, reports in self.categorized_reports.items():
            no_of_items = len(reports)
            if no_of_items > 0:
                summary_table.add_row(
                    Padding(
                        str(no_of_items),
                        pad=HORIZONTAL_PAD,
                    ),
                    Padding(
                        state.title(),
                        pad=HORIZONTAL_PAD,
                    ),
                    Padding(
                        f"({100 * no_of_items / self.total_items_completed:.1f}%)",
                        pad=HORIZONTAL_PAD,
                    ),
                    #
                    style=style_dict[state],
                )

        if self.verbose is True:
            for nodeid, status in self.status_per_item.items():
                if status == "success":
                    self.console.print(
                        Text("SUCCESS ", style="green"), Text(f"{nodeid}")
                    )

        for nodeid, errors in error_messages.items():
            self.console.print(
                Text("FAILED ", style="red"),
                Text(f"{nodeid} {''.join(errors)}"),
            )

        result_summary_panel = Panel(
            summary_table,
            title="Summary",
            style="bold blue",
            expand=False,
            border_style="bold blue",
        )
        self.console.print("\n")
        self.console.print(result_summary_panel)

    def pytest_keyboard_interrupt(
        self, excinfo: pytest.ExceptionInfo[BaseException]
    ) -> None:
        ...

    def pytest_unconfigure(self) -> None:
        ...

    @property
    def verbose(self) -> bool:
        return self.config.getoption("verbose") > 0

    @property
    def verbosity_level(self) -> int:
        return self.config.getoption("verbose")

    @property
    def no_header(self) -> bool:
        return self.config.getoption("no_header")

    @property
    def no_summary(self) -> bool:
        return self.config.getoption("no_summary")
