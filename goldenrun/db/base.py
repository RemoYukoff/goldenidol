from abc import ABCMeta, abstractmethod
from typing import Iterable, List

from goldenrun.tracing import FuncRecord, FuncRecordLogger


class FuncRecordThunk(metaclass=ABCMeta):
    """A deferred computation that produces a FuncRecord or raises an error."""

    @abstractmethod
    def to_trace(self) -> FuncRecord:
        """Produces the FuncRecord."""


class FuncRecordStore(metaclass=ABCMeta):
    """An interface that all concrete FuncRecord storage backends must implement."""

    @abstractmethod
    def add(self, traces: Iterable[FuncRecord]) -> None:
        """Store the supplied call traces in the backing store"""

    @abstractmethod
    def get_records(
        self, func_qualname: str, limit: int = 2000
    ) -> List[FuncRecordThunk]:
        """Query the backing store for any traces that match the supplied query.

        By returning a list of thunks we let the caller get a partial result in the
        event that decoding one or more call traces fails.
        """

    @classmethod
    def make_store(cls, connection_string: str) -> "FuncRecordStore":
        """Create a new store instance.

        This is a factory function that is intended to be used by the CLI.
        """
        raise NotImplementedError(
            f"Your FuncRecordStore ({cls.__module__}.{cls.__name__}) "
            f"does not implement make_store()"
        )

    def list_modules(self) -> List[str]:
        """List of traced modules from the backing store"""
        raise NotImplementedError(
            f"Your FuncRecordStore ({self.__class__.__module__}.{self.__class__.__name__}) "
            f"does not implement list_modules()"
        )


class FuncRecordStoreLogger(FuncRecordLogger):
    """A FuncRecordLogger that stores logged traces in a FuncRecordStore."""

    def __init__(self, store: FuncRecordStore) -> None:
        self.store = store
        self.traces: List[FuncRecord] = []

    def log(self, trace: FuncRecord) -> None:
        self.traces.append(trace)

    def flush(self) -> None:
        self.store.add(self.traces)
        self.traces = []
