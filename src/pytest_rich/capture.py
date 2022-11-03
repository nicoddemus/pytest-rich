import re
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Tuple

from rich.console import Console


def save_terminal_output(console: Console, arg: str) -> None:
    """
    Save terminal output to file.

    Args:
        console (Console): Rich console.
        arg (str): Argument to parse.
    """
    try:
        filename, filetype = _get_filename_from_arg(arg)
    except ValueError as e:
        console.print(f"[red]Error saving terminal output: {e}[/red]")
        return

    func_name = "text" if filetype == "txt" else filetype

    save_func = getattr(console, f"save_{func_name}")

    save_func(f"{filename}.{filetype}")


def _get_filename_from_arg(arg: str) -> Tuple[str, str]:
    """
    Get filename from command line argument.

    Args:
        arg (str): Argument to parse.

    Returns:
        tuple: Filename and file type.
    """

    ACCEPTED_FILE_TYPES = ["svg", "html", "txt"]

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    if not arg:
        # if no argument is supplied, use the module name and a timestamp
        # with the default svg file type
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

    return filename, filetype
