import re
from datetime import datetime
from pathlib import Path

from rich.console import Console


def save_terminal_output(console: Console, arg: str) -> None:
    """
    Save terminal output to file.

    Args:
        console (Console): Rich console.
        arg (str): Argument to parse.
    """
    try:
        filename = _get_filename_from_arg(arg)
    except ValueError as e:
        console.print(f"[red]Error saving terminal output: {e}[/red]")
        return

    func_name = "text" if filename.endswith(".txt") else filename.split(".")[-1]

    save_func = getattr(console, f"save_{func_name}")

    save_func(filename)


def _get_filename_from_arg(arg: str) -> str:
    """
    Get filename from command line argument.

    Args:
        arg (str): Argument to parse.

    Returns:
        str: Filename.
    """

    ACCEPTED_FILE_TYPES = ["svg", "html", "txt"]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if not arg:
        # if no argument is supplied, use the module name and a timestamp
        filename = f"pytest_rich-{timestamp}"
        filetype = "svg"
    elif re.match(r"^\.\w+$", arg) or arg in ACCEPTED_FILE_TYPES:
        # if the argument is a file type, use the module name and a timestamp
        filename = f"pytest_rich-{timestamp}"
        filetype = arg[1:] if arg.startswith(".") else arg
    elif "." not in arg:
        # if no file type is supplied, use svg
        filename = arg
        filetype = "svg"
    else:
        path = Path(arg)
        filename = path.stem
        filetype = path.suffix[1:]

    if filetype not in ACCEPTED_FILE_TYPES:
        raise ValueError(f"File type {filetype} is not supported.")

    return f"{filename}.{filetype}"
