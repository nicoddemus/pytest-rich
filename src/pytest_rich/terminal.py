import warnings
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Literal
from typing import Optional
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
from typing_extensions import assert_never

from pytest_rich.capture import save_terminal_output
from pytest_rich.header import generate_header_panel
from pytest_rich.traceback import RichExceptionChainRepr

HORIZONTAL_PAD = (0, 1, 0, 1)


@attr.s(auto_attribs=True, hash=True)
class RichTerminalReporter:
    config: pytest.Config
    console: Console = attr.Factory(Console)

    Status = Literal[
        "collected",
        "running",
        "success",
        "fail",
        "error",
        "skipped",
        "xfailed",
        "xpassed",
    ]

    def __attrs_post_init__(self) -> None:
        self.collect_progress: Optional[Progress] = None
        self.runtest_progress: Optional[Progress] = None
        self.total_items_collected = 0
        self.total_items_completed = 0
        self.items_per_file: dict[Path, list[pytest.Item]] = {}
        self.status_per_item: dict[str, RichTerminalReporter.Status] = {}
        self.items: dict[str, pytest.Item] = {}
        self.nodeid_per_location: dict[tuple[str, Optional[int], str], str] = {}
        self.runtest_tasks_per_file: dict[Path, TaskID] = {}
        self.categorized_reports: dict[str, list[pytest.TestReport]] = defaultdict(list)
        self.summary: Optional[Live] = None
        self.collection_errors: list[pytest.CollectReport] = []
        self.total_duration: float = 0
        self.console.record = self.config.getoption("rich_capture") is not None

    def _preserve_report(self, report, category: str) -> None:
        self.categorized_reports[category].append(report)
        self.total_duration += report.duration

    def pytest_collection(self) -> None:
        self.collect_progress = Progress(
            "[progress.description]{task.description}",
            console=self.console,
        )
        self.collect_task = self.collect_progress.add_task("[cyan][bold]Collecting")
        self.collect_progress.start()

    def pytest_collectreport(self, report: pytest.CollectReport) -> None:
        if report.failed:
            self.collection_errors.append(report)
        items = [x for x in report.result if isinstance(x, pytest.Item)]
        if items:
            for item in items:
                self.items_per_file.setdefault(item.path, []).append(item)
                self.status_per_item[item.nodeid] = "collected"
                self.items[item.nodeid] = item
                self.nodeid_per_location[item.location] = item.nodeid
            self.total_items_collected += len(items)
            if self.collect_progress is not None:
                self.collect_progress.update(
                    self.collect_task,
                    description=f"[cyan][bold]Collecting[/cyan] [magenta]{report.nodeid}[/magenta] ([green]{self.total_items_collected}[/green] total items)",
                    refresh=True,
                )

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        if self.collect_progress is not None:
            error_suffix = ""
            if self.collection_errors:
                n = len(self.collection_errors)
                error_suffix = f" [red]/ {n} errors" if n > 1 else " [red]/ 1 error"
            self.collect_progress.update(
                self.collect_task,
                description=f"[cyan][bold]Collected [green]{self.total_items_collected} [cyan]items{error_suffix}",
                completed=True,
            )
            self.collect_progress.stop()
            self.collect_progress = None

    def pytest_sessionstart(self, session: pytest.Session) -> None:
        self.console.print(Rule("pytest session starts", style="default"))

        if self.no_header is False:
            header = generate_header_panel(session)

            self.console.print(header)

    def pytest_internalerror(self, excrepr: ExceptionRepr) -> None: ...

    def pytest_warning_recorded(
        self,
        warning_message: warnings.WarningMessage,
        nodeid: str,
    ) -> None: ...

    def pytest_deselected(self, items: Sequence[pytest.Item]) -> None:
        # Deselected items never run, so drop them from the bookkeeping or the
        # per-file progress would never reach 100%.
        for item in items:
            if self.items.pop(item.nodeid, None) is None:
                continue
            self.status_per_item.pop(item.nodeid, None)
            self.nodeid_per_location.pop(item.location, None)
            per_file = self.items_per_file[item.path]
            per_file.remove(item)
            if not per_file:
                del self.items_per_file[item.path]

    def pytest_plugin_registered(self, plugin) -> None: ...

    def pytest_runtest_logstart(
        self, nodeid: str, location: tuple[str, Optional[int], str]
    ) -> None:
        if self.runtest_progress is None:
            self.runtest_progress = Progress(
                SpinnerColumn(), "{task.description}", console=self.console
            )
            self.runtest_progress.start()

            for fn in self.items_per_file:
                total_items = self.items_per_file[fn]
                task = self.runtest_progress.add_task(
                    self._file_label(fn),
                    total=len(total_items),
                    visible=False,
                )
                self.runtest_tasks_per_file[fn] = task
            self.overall_progress_task = self.runtest_progress.add_task(
                "Progress", total=len(self.items)
            )

        self._update_task(nodeid)

    def _get_status_char(self, status: Status) -> str:
        match status:
            case "collected" | "running":
                return ""
            case "success":
                return "[green]✔[/green]"
            case "fail":
                return "[red]❌[/red]"
            case "error":
                return "[red]E[/red]"
            case "skipped":
                return "[yellow]s[/yellow]"
            case "xfailed":
                return "[yellow]x[/yellow]"
            case "xpassed":
                return "[yellow]X[/yellow]"
            case unreachable:
                assert_never(unreachable)

    def _file_label(self, fn: Path) -> str:
        # ``relative_to`` raises ValueError for tests collected from outside
        # the rootdir (e.g. ``pytest ../sibling/tests``).
        try:
            return str(fn.relative_to(self.config.rootpath))
        except ValueError:
            return str(fn)

    def _update_task(self, nodeid: str):
        current_item = self.items.get(nodeid)
        if current_item is None:
            # A plugin's report hook rewrote ``nodeid`` into something we never
            # collected (e.g. a display-only string). Nothing to update.
            return
        fn = current_item.path
        task = self.runtest_tasks_per_file[fn]
        base_fn = self._file_label(fn)
        items = self.items_per_file[fn]
        chars = []
        statuses = []
        for item in items:
            status = self.status_per_item[item.nodeid]
            statuses.append(status)
            chars.append(self._get_status_char(status))
        completed_count = [x for x in statuses if x not in ("collected", "running")]
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
            if report.skipped:
                if hasattr(report, "wasxfail"):
                    status = "xfailed"
                    category = "xfailed"
                else:
                    status = "skipped"
                    category = "skipped"
                self._preserve_report(report, category)
            else:
                status = "running"
        elif report.when == "call":
            if hasattr(report, "wasxfail"):
                if report.skipped:
                    status = "xfailed"
                    category = "xfailed"
                elif report.passed:
                    status = "xpassed"
                    category = "xpassed"
                else:
                    status = "fail"
                    category = "failed"
            elif report.passed:
                status = "success"
                category = "passed"
            elif report.skipped:
                status = "skipped"
                category = "skipped"
            else:
                status = "fail"
                category = "failed"
            self._preserve_report(report, category)
        if status is not None:
            # A plugin's makereport hook may have rewritten ``report.nodeid``
            # into a display-only string (#74); recover the collected nodeid
            # through ``report.location``, which plugins don't mutate.
            nodeid = report.nodeid
            if nodeid not in self.items:
                nodeid = self.nodeid_per_location.get(report.location, nodeid)
            self.status_per_item[nodeid] = status
            self._update_task(nodeid)

    def pytest_runtest_logfinish(self) -> None:
        self.total_items_completed += 1
        percent = (self.total_items_completed * 100) // len(self.items)
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

        if self.collection_errors:
            self.console.print(Rule("ERRORS", style="bold red"))
            for report in self.collection_errors:
                self.console.print(
                    Text(f"ERROR collecting {report.nodeid}", style="bold red")
                )
                if hasattr(report.longrepr, "longrepr"):
                    self.console.print(Text(report.longrepr.longrepr, style="red"))
                elif report.longrepr is not None:
                    self.console.print(Text(str(report.longrepr), style="red"))

        if self.no_summary is False:
            error_messages = {}
            for index, report in enumerate(self.categorized_reports["failed"]):
                if index == 0:
                    self.console.print(Rule("FAILURES\n", style="bold red"))
                nodeid = report.nodeid
                if isinstance(report.longrepr, ExceptionChainRepr):
                    tb = RichExceptionChainRepr(nodeid, report.longrepr)
                    error_messages[nodeid] = tb.error_messages
                    self.console.print(tb)
                else:
                    if isinstance(report.longrepr, tuple):
                        _, _, msg = report.longrepr
                    else:
                        msg = str(report.longrepr)
                    error_messages[nodeid] = [msg]
                    self.console.print(
                        Text.assemble(
                            ("FAILED ", "bold red"),
                            (nodeid, "magenta"),
                            ": ",
                            msg,
                        )
                    )
                self._print_captured_sections(report)

            if self.verbosity_level >= 0 and self.total_items_completed > 0:
                self.print_summary(error_messages)

        status = "SUCCEEDED" if exitstatus == 0 else "FAILED"

        self.console.print(
            Rule(
                title=f"{status} in {self.total_duration:.2f} seconds",
                style="green" if status == "SUCCEEDED" else "red",
            )
        )

        if self.console.record is True:
            save_terminal_output(self.console, self.config.getoption("rich_capture"))

    def _print_captured_sections(self, report: pytest.TestReport) -> None:
        # Same filtering as pytest's built-in reporter for --show-capture.
        show_capture = self.config.option.showcapture
        if show_capture == "no":
            return
        for section_name, content in report.sections:
            if show_capture != "all" and show_capture not in section_name:
                continue
            self.console.print(Rule(section_name, style="yellow"))
            self.console.print(Text(content))

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
            "xfailed": "bold yellow",
            "xpassed": "bold yellow",
        }
        for state, reports in self.categorized_reports.items():
            no_of_items = len(reports)
            if no_of_items > 0:
                summary_table.add_row(
                    Padding(str(no_of_items), pad=HORIZONTAL_PAD),
                    Padding(state.title(), pad=HORIZONTAL_PAD),
                    Padding(
                        f"({100 * no_of_items / self.total_items_completed:.1f}%)",
                        pad=HORIZONTAL_PAD,
                    ),
                    style=style_dict[state],
                )

        if self.collection_errors:
            summary_table.add_row(
                Padding(
                    str(len(self.collection_errors)),
                    pad=HORIZONTAL_PAD,
                ),
                Padding("Collection Errors", pad=HORIZONTAL_PAD),
                Padding("", pad=HORIZONTAL_PAD),
                style="bold red",
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
    ) -> None: ...

    def pytest_unconfigure(self) -> None: ...

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
