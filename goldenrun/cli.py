# PYTHON_ARGCOMPLETE_OK
import argparse
import os
import os.path
import runpy
import sys
from typing import IO, TYPE_CHECKING, List, Optional, Tuple
from goldenrun.exceptions import GoldenRunError


from goldenrun import trace
from goldenrun.config import Config
from goldenrun.util import get_name_in_module

if TYPE_CHECKING:
    # This is not present in Python 3.6.1, so not safe for runtime import
    from typing import NoReturn  # noqa


def module_path(path: str) -> Tuple[str, Optional[str]]:
    """Parse <module>[:<qualname>] into its constituent parts."""
    parts = path.split(":", 1)
    module = parts.pop(0)
    qualname = parts[0] if parts else None
    if os.sep in module:  # Smells like a path
        raise argparse.ArgumentTypeError(
            f"{module} does not look like a valid Python import path"
        )

    return module, qualname


def module_path_with_qualname(path: str) -> Tuple[str, str]:
    """Require that path be of the form <module>:<qualname>."""
    module, qualname = module_path(path)
    if qualname is None:
        raise argparse.ArgumentTypeError("must be of the form <module>:<qualname>")
    return module, qualname


def get_goldenrun_config(path: str) -> Config:
    """Imports the config instance specified by path.

    Path should be in the form module:qualname. Optionally, path may end with (),
    in which case we will call/instantiate the given class/function.
    """
    should_call = False
    if path.endswith("()"):
        should_call = True
        path = path[:-2]
    module, qualname = module_path_with_qualname(path)
    try:
        config = get_name_in_module(module, qualname)
    except GoldenRunError as mte:
        raise argparse.ArgumentTypeError(f"cannot import {path}: {mte}")
    if should_call:
        config = config()
    return config  # type: ignore[no-any-return]


def record_handler(args: argparse.Namespace, stdout: IO[str], stderr: IO[str]) -> None:
    # remove initial `goldenrun record`
    old_argv = sys.argv.copy()
    try:
        with trace(args.config):
            sys.argv = [args.script_path] + args.script_args
            if args.m:
                runpy.run_module(args.script_path, run_name="__main__", alter_sys=True)
            else:
                runpy.run_path(args.script_path, run_name="__main__")
    finally:
        sys.argv = old_argv


def update_args_from_config(args: argparse.Namespace) -> None:
    """Pull values from config for unspecified arguments."""
    return
    if args.limit is None:
        args.limit = args.config.query_limit()


def main(argv: List[str], stdout: IO[str], stderr: IO[str]) -> int:
    parser = argparse.ArgumentParser(description="Generate and run golden image tests.")
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default="goldenrun.config:get_default_config()",
        help=(
            "The <module>:<qualname> of the config to use"
            " (default: goldenrun_config:CONFIG if it exists, "
            "else goldenrun.config:DefaultConfig())"
        ),
    )

    subparsers = parser.add_subparsers(title="commands", dest="command")

    record_parser = subparsers.add_parser(
        "record",
        help="Run a Python script under GoldenRun tracing",
        description="Run a Python script under GoldenRun tracing",
    )
    record_parser.add_argument(
        "script_path",
        type=str,
        help="""Filesystem path to a Python script file to run under tracing""",
    )
    record_parser.add_argument(
        "-m", action="store_true", help="Run a library module as a script"
    )
    record_parser.add_argument(
        "script_args",
        nargs=argparse.REMAINDER,
    )
    record_parser.set_defaults(handler=record_handler)

    args = parser.parse_args(argv)
    args.config = get_goldenrun_config(args.config)
    update_args_from_config(args)

    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help(file=stderr)
        return 1

    with args.config.cli_context(args.command):
        handler(args, stdout, stderr)

    return 0


def entry_point_main() -> "NoReturn":
    # Since goldenrun needs to import the user's code (and possibly config
    # code), the user's code must be on the Python path. But when running the
    # CLI script, it won't be. So we add the current working directory to the
    # Python path ourselves.
    sys.path.insert(0, os.getcwd())
    sys.exit(main(sys.argv[1:], sys.stdout, sys.stderr))


entry_point_main()  # REMOVE LATER
