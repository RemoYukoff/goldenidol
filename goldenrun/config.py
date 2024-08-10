import functools
import os
import pathlib
import sys
import sysconfig
from abc import ABCMeta, abstractmethod
from contextlib import contextmanager
from types import CodeType
from typing import Iterator, Optional

from goldenrun.db.base import FuncRecordStore, FuncRecordStoreLogger
from goldenrun.db.sqlite import SQLiteStore
from goldenrun.tracing import CodeFilter, FuncRecordLogger


class Config(metaclass=ABCMeta):
    """A Config ties together concrete implementations of the different abstractions
    that make up a typical deployment of GoldenRun.
    """

    @abstractmethod
    def trace_store(self) -> FuncRecordStore:
        """Return the FuncRecordStore for storage/retrieval of call traces."""
        pass

    @contextmanager
    def cli_context(self, command: str) -> Iterator[None]:
        """Lifecycle hook that is called once right after the CLI
        starts.

        `command` is the name of the command passed to goldenrun
        ('run', 'apply', etc).
        """
        yield

    def trace_logger(self) -> FuncRecordLogger:
        """Return the FuncRecordLogger for logging call traces.

        By default, returns a FuncRecordStoreLogger that logs to the configured
        trace store.
        """
        return FuncRecordStoreLogger(self.trace_store())

    def code_filter(self) -> Optional[CodeFilter]:
        """Return the (optional) CodeFilter predicate for triaging calls.

        A CodeFilter is a callable that takes a code object and returns a
        boolean determining whether the call should be traced or not. If None is
        returned, all calls will be traced and logged.
        """
        return None


lib_paths = {sysconfig.get_path(n) for n in ["stdlib", "purelib", "platlib"]}
# if in a virtualenv, also exclude the real stdlib location
venv_real_prefix = getattr(sys, "real_prefix", None)
if venv_real_prefix:
    lib_paths.add(
        sysconfig.get_path("stdlib", vars={"installed_base": venv_real_prefix})
    )
LIB_PATHS = tuple(pathlib.Path(p).resolve() for p in lib_paths if p is not None)


def _startswith(a: pathlib.Path, b: pathlib.Path) -> bool:
    try:
        return bool(a.relative_to(b))
    except ValueError:
        return False


@functools.lru_cache(maxsize=8192)
def default_code_filter(code: CodeType) -> bool:
    """A CodeFilter to exclude stdlib and site-packages."""
    # Filter code without a source file
    if not code.co_filename or code.co_filename[0] == "<":
        return False

    filename = pathlib.Path(code.co_filename).resolve()
    # if GOLDENRUN_TRACE_MODULES is defined, trace only specified packages or modules
    trace_modules_str = os.environ.get("GOLDENRUN_TRACE_MODULES")
    if trace_modules_str is not None:
        trace_modules = trace_modules_str.split(",")
        # try to remove lib_path to only check package and module names
        for lib_path in LIB_PATHS:
            try:
                filename = filename.relative_to(lib_path)
                break
            except ValueError:
                pass
        return any(m == filename.stem or m in filename.parts for m in trace_modules)
    else:
        return not any(_startswith(filename, lib_path) for lib_path in LIB_PATHS)


class DefaultConfig(Config):
    DB_PATH_VAR = "GR_DB_PATH"

    # def type_rewriter(self) -> TypeRewriter:
    #     return DEFAULT_REWRITER

    def trace_store(self) -> FuncRecordStore:
        """By default we store traces in a local SQLite database.

        The path to this database file can be customized via the `GR_DB_PATH`
        environment variable.
        """
        db_path = os.environ.get(self.DB_PATH_VAR, "goldenrun.sqlite3")
        return SQLiteStore.make_store(db_path)

    def code_filter(self) -> CodeFilter:
        """Default code filter excludes standard library & site-packages."""
        return default_code_filter


def get_default_config() -> Config:
    """Use goldenrun_config.CONFIG if it exists, otherwise DefaultConfig().

    goldenrun_config is not a module that is part of the goldenrun
    distribution, it must be created by the user.
    """
    try:
        import goldenrun_config  # type: ignore[import-not-found]
    except ImportError:
        return DefaultConfig()
    return goldenrun_config.CONFIG  # type: ignore[no-any-return]
