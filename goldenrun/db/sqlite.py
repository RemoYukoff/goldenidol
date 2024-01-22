import datetime
import logging
import pickle
import sqlite3
from typing import Iterable, List, Optional, Tuple, Union

from goldenrun.db.base import FuncRecordStore, FuncRecordThunk
from goldenrun.encoding import FuncRecordRow

# from goldenrun.encoding import FuncRecordRow, serialize_traces
from goldenrun.tracing import FuncRecord

logger = logging.getLogger(__name__)


DEFAULT_TABLE = "goldenrun_func_record"


def create_call_trace_table(
    conn: sqlite3.Connection, table: str = DEFAULT_TABLE
) -> None:
    queries = [
        """
        CREATE TABLE IF NOT EXISTS {table} (
          created_at  TEXT,
          module      TEXT,
          qualname    TEXT,
          serialized_args BLOB,
          serialized_return BLOB,
          record BOOL);
        """,
    ]

    with conn:
        for query in queries:
            conn.execute(query.format(table=table))


QueryValue = Union[str, int]
ParameterizedQuery = Tuple[str, List[QueryValue]]


def make_query(
    table: str, module: str, qualname: Optional[str], limit: int
) -> ParameterizedQuery:
    raw_query = """
    SELECT
        module, qualname, serialized_args, serialized_return
    FROM {table}
    WHERE
        module == ?
    """.format(
        table=table
    )
    values: List[QueryValue] = [module]
    if qualname is not None:
        raw_query += " AND qualname LIKE ? || '%'"
        values.append(qualname)
    raw_query += """
    GROUP BY
        module, qualname, arg_types, return_type, yield_type
    ORDER BY date(created_at) DESC
    LIMIT ?
    """
    values.append(limit)
    return raw_query, values


class SQLiteStore(FuncRecordStore):
    def __init__(self, conn: sqlite3.Connection, table: str = DEFAULT_TABLE) -> None:
        self.conn = conn
        self.table = table

    @classmethod
    def make_store(cls, connection_string: str) -> "FuncRecordStore":
        conn = sqlite3.connect(connection_string)
        create_call_trace_table(conn)
        return cls(conn)

    def add(self, traces: Iterable[FuncRecord]) -> None:
        values = []
        for trace in traces:
            values.append(
                (
                    datetime.datetime.now(),
                    trace.module,
                    trace.qualname,
                    pickle.dumps(trace.args),
                    pickle.dumps(trace.return_value),
                )
            )
        with self.conn:
            self.conn.executemany(
                "INSERT INTO {table} VALUES (?, ?, ?, ?, ?, ?)".format(
                    table=self.table
                ),
                values,
            )

    def filter(
        self, module: str, qualname_prefix: Optional[str] = None, limit: int = 2000
    ) -> List[FuncRecordThunk]:
        ...
        # sql_query, values = make_query(self.table, module, qualname_prefix, limit)
        # with self.conn:
        #     cur = self.conn.cursor()
        #     cur.execute(sql_query, values)
        #     return [FuncRecordRow(*row) for row in cur.fetchall()]

    def list_modules(self) -> List[str]:
        ...
        # with self.conn:
        #     cur = self.conn.cursor()
        #     cur.execute(
        #         """
        #                 SELECT module FROM {table}
        #                 GROUP BY module
        #                 ORDER BY date(created_at) DESC
        #                 """.format(
        #             table=self.table
        #         )
        #     )
        #     return [row[0] for row in cur.fetchall() if row[0]]
