"""
Proof of concept for pytest + rich integration.
"""
import ast
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
from _pytest._code.code import ExceptionChainRepr
from _pytest._code.code import ExceptionRepr
from _pytest._code.code import ReprFuncArgs
from pygments.token import Comment
from pygments.token import Keyword
from pygments.token import Name
from pygments.token import Number
from pygments.token import Operator
from pygments.token import String
from pygments.token import Text as TextToken
from pygments.token import Token
from rich._loop import loop_last
from rich.columns import Columns
from rich.console import Console
from rich.console import ConsoleOptions
from rich.console import ConsoleRenderable
from rich.console import Group
from rich.console import group
from rich.console import RenderResult
from rich.highlighter import ReprHighlighter
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress
from rich.progress import SpinnerColumn
from rich.progress import TaskID
from rich.rule import Rule
from rich.style import Style
from rich.syntax import Syntax
from rich.text import Text
from rich.theme import Theme
from rich.traceback import PathHighlighter

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
        if getattr(sys, "pypy_version_info", None):
            pypy_verinfo = ".".join(map(str, sys.pypy_version_info[:3]))
            column1.add_renderable(f"pypy [cyan]{pypy_verinfo}")
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
        if self.failed_reports:
            self.console.print(Rule("FAILURES", style="red"))
            for nodeid, report in self.failed_reports.items():
                tb = RichExceptionChainRepr(nodeid, report.longrepr)
                self.console.print(tb)

    def pytest_keyboard_interrupt(
        self, excinfo: pytest.ExceptionInfo[BaseException]
    ) -> None:
        ...

    def pytest_unconfigure(self) -> None:
        ...


@attr.s(auto_attribs=True)
class RichExceptionChainRepr:
    """
    A rich representation of an ExceptionChainRepr produced by pytest.

    This is needed because pytest does not provide the actual traceback
    object, which Rich's `Traceback` class requires.
    """

    nodeid: str
    chain: ExceptionChainRepr
    extra_lines: int = 3
    theme: Optional[str] = "ansi_dark"
    word_wrap: bool = True
    indent_guides: bool = True

    def __attrs_post_init__(self):
        self.theme = Syntax.get_theme(self.theme)

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        theme = self.theme
        background_style = theme.get_background_style()
        token_style = theme.get_style_for_token

        traceback_theme = Theme(
            {
                "pretty": token_style(TextToken),
                "pygments.text": token_style(Token),
                "pygments.string": token_style(String),
                "pygments.function": token_style(Name.Function),
                "pygments.number": token_style(Number),
                "repr.indent": token_style(Comment) + Style(dim=True),
                "repr.str": token_style(String),
                "repr.brace": token_style(TextToken) + Style(bold=True),
                "repr.number": token_style(Number),
                "repr.bool_true": token_style(Keyword.Constant),
                "repr.bool_false": token_style(Keyword.Constant),
                "repr.none": token_style(Keyword.Constant),
                "scope.border": token_style(String.Delimiter),
                "scope.equals": token_style(Operator),
                "scope.key": token_style(Name),
                "scope.key.special": token_style(Name.Constant) + Style(dim=True),
            },
            inherit=False,
        )

        stack_renderable: ConsoleRenderable = Panel(
            self._render_chain(self.chain, options),
            title=f"[magenta]{self.nodeid}[/magenta]",
            style=background_style,
            border_style="traceback.border",
            expand=True,
            padding=(0, 1),
        )
        with console.use_theme(traceback_theme):
            yield stack_renderable

        path_highlighter = PathHighlighter()
        for entry in self.chain.reprtraceback.reprentries:
            if entry.reprfileloc.message:
                yield Text.assemble(
                    path_highlighter(
                        Text(entry.reprfileloc.path, style="pygments.string")
                    ),
                    (":", "pygments.text"),
                    (str(entry.reprfileloc.lineno), "pygments.number"),
                    (": ", "pygments.text"),
                    Text(entry.reprfileloc.message, style="pygments.string"),
                    style="pygments.text",
                )
                yield ""

    @group()
    def _render_chain(
        self, chain: ExceptionChainRepr, options: ConsoleOptions
    ) -> RenderResult:
        path_highlighter = PathHighlighter()
        repr_highlighter = ReprHighlighter()
        theme = self.theme
        code_cache: Dict[str, str] = {}

        def read_code(filename: str) -> str:
            """
            Read files and cache results on filename.

            Args:
                filename (str): Filename to read

            Returns:
                str: Contents of file
            """
            code = code_cache.get(filename)
            if not code:
                with open(
                    filename, "rt", encoding="utf-8", errors="replace"
                ) as code_file:
                    code = code_file.read()
                code_cache[filename] = code
            return code

        def get_funcname(lineno: int, filename: str) -> str:
            """
            Given a line number in a file, using `ast.parse` walk backwards
            until we find the function name.

            Args:
                lineno (int): Line number to start searching from
                filename (str): Filename to read

            Returns:
                str: Function name
            """
            code = read_code(filename)
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # TODO: Remove this if statement once 3.7 support is dropped
                    if sys.version_info < (3, 8):
                        if node.lineno <= lineno < node.lineno + node.body[0].lineno:
                            return node.name
                    else:
                        if node.lineno <= lineno <= node.end_lineno:
                            return node.name
            return "???"

        def get_args(reprfuncargs: ReprFuncArgs) -> str:
            args = Text("")
            for arg in reprfuncargs.args:
                args.append(
                    Text.assemble(
                        (arg[0], "name.variable"),
                        (" = ", "repr.equals"),
                        (arg[1], "token"),
                    )
                )
                if reprfuncargs.args[-1] != arg:
                    args.append(Text(", "))
            return args

        def get_error_source(lines: List[str]) -> str:
            for line in lines:
                if line.startswith(">"):
                    return line.split(">")[1].strip()

        def get_err_msgs(lines: List[str]) -> str:
            err_lines = []
            for line in lines:
                if line.startswith("E"):
                    err_lines.append(line[1:].strip())
            return err_lines

        for last, entry in loop_last(chain.reprtraceback.reprentries):
            filename = entry.reprfileloc.path
            lineno = entry.reprfileloc.lineno
            funcname = get_funcname(lineno, filename)
            message = entry.reprfileloc.message

            text = Text.assemble(
                path_highlighter(Text(filename, style="pygments.string")),
                (":", "pygments.text"),
                (str(lineno), "pygments.number"),
                " in ",
                (funcname, "pygments.function"),
                style="pygments.text",
            )
            yield text

            args = get_args(entry.reprfuncargs)
            if args:
                yield args

            code = read_code(filename)
            syntax = Syntax(
                code,
                "python",
                theme=theme,
                line_numbers=True,
                line_range=(
                    lineno - self.extra_lines,
                    lineno + self.extra_lines,
                ),
                highlight_lines={lineno},
                word_wrap=self.word_wrap,
                code_width=88,
                indent_guides=self.indent_guides,
                dedent=False,
            )
            yield ""
            yield syntax

            if message:
                line_pointer = "> " if options.legacy_windows else "❱ "
                yield ""
                yield Text.assemble(
                    (str(lineno), "pygments.number"),
                    ": ",
                    (message, "traceback.exc_type"),
                )
                yield Text.assemble(
                    (line_pointer, Style(color="red")),
                    repr_highlighter(get_error_source(entry.lines)),
                )
                for err_msg in get_err_msgs(entry.lines):
                    yield Text.assemble(
                        ("E ", Style(color="red")),
                        repr_highlighter(err_msg),
                    )

            if not last:
                yield ""
                yield Rule(style=Style(color="red", dim=True))
