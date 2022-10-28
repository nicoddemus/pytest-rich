import ast
import sys
from typing import Dict
from typing import Optional
from typing import Sequence

import attr
from _pytest._code.code import ExceptionChainRepr
from _pytest._code.code import ReprEntry
from _pytest._code.code import ReprFileLocation
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
from rich.console import Console
from rich.console import ConsoleOptions
from rich.console import ConsoleRenderable
from rich.console import group
from rich.console import RenderResult
from rich.highlighter import ReprHighlighter
from rich.panel import Panel
from rich.rule import Rule
from rich.style import Style
from rich.syntax import Syntax
from rich.syntax import SyntaxTheme
from rich.text import Text
from rich.theme import Theme
from rich.traceback import PathHighlighter


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
    error_messages: list = []

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        theme = self.get_theme()
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
            assert isinstance(entry, ReprEntry)
            assert isinstance(entry.reprfileloc, ReprFileLocation)
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
        theme = self.get_theme()
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
                        if node.end_lineno is not None:
                            if node.lineno <= lineno <= node.end_lineno:
                                return node.name
            return "???"

        def get_args(reprfuncargs: ReprFuncArgs) -> Text:
            args = Text("")
            for arg in reprfuncargs.args:
                assert isinstance(arg[1], str)
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

        def get_error_source(lines: Sequence[str]) -> str:
            for line in lines:
                if line.startswith(">"):
                    return line.split(">")[1].strip()
            return ""

        def get_err_msgs(lines: Sequence[str]) -> list[str]:
            err_lines = []
            for line in lines:
                if line.startswith("E"):
                    err_lines.append(line[1:].strip())
            return err_lines

        for last, entry in loop_last(chain.reprtraceback.reprentries):
            assert isinstance(entry, ReprEntry)
            assert entry.reprfileloc is not None
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

            assert entry.reprfuncargs is not None
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
                    self.error_messages.append(err_msg)
                    yield Text.assemble(
                        ("E ", Style(color="red")),
                        repr_highlighter(err_msg),
                    )

            if not last:
                yield ""
                yield Rule(style=Style(color="red", dim=True))

    def get_theme(self) -> SyntaxTheme:
        """
        Get SyntaxTheme from `theme` class attribute.

        Theme is set via a string attribute option. We need to pass the
        string through Rich's Syntax class to get the actual SyntaxTheme
        object.
        """
        return Syntax.get_theme(self.theme)
