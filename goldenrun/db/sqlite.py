import logging
import pickle
import sqlite3
from datetime import datetime
from typing import Iterable, List, Tuple, Union

from goldenrun.db.base import FuncRecordStore, FuncRecordThunk
from goldenrun.tracing import FuncRecord

logger = logging.getLogger(__name__)


def create_func_table(conn: sqlite3.Connection) -> None:
    query = """
        CREATE TABLE IF NOT EXISTS goldenrun_func (
          id          INTEGER PRIMARY KEY AUTOINCREMENT,
          module      TEXT,
          qualname    TEXT,
          record      BOOL);
        """

    with conn:
        conn.execute(query)


def create_record_table(conn: sqlite3.Connection) -> None:
    query = """
        CREATE TABLE IF NOT EXISTS goldenrun_record (
          func_id           INTEGER,
          created_at        TEXT,
          serialized_args   BLOB,
          serialized_return BLOB,
          FOREIGN KEY (func_id) REFERENCES goldenrun_func(id));
        """

    with conn:
        conn.execute(query)


QueryValue = Union[str, int]
ParameterizedQuery = Tuple[str, List[QueryValue]]


class SQLiteStore(FuncRecordStore):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    @classmethod
    def make_store(cls, connection_string: str) -> "FuncRecordStore":
        conn = sqlite3.connect(connection_string)
        create_func_table(conn)
        create_record_table(conn)
        return cls(conn)

    def _get_or_insert_func(self, module: str, qualname: str):
        get_func_query = "SELECT id FROM goldenrun_func WHERE module=? AND qualname=?"
        result = self.conn.execute(get_func_query, (module, qualname)).fetchone()

        if result:
            return result[0]
        else:
            insert_func_query = (
                "INSERT INTO goldenrun_func (module, qualname) VALUES (?, ?)"
            )
            self.conn.execute(insert_func_query, (module, qualname))
            return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def add(self, traces: Iterable[FuncRecord]) -> None:
        with self.conn as conn:
            for trace in traces:
                func_id = self._get_or_insert_func(trace.module, trace.qualname)
                insert_record_query = """
                        INSERT INTO goldenrun_record (func_id, created_at, serialized_args, serialized_return)
                        VALUES (?, ?, ?, ?)
                    """
                conn.execute(
                    insert_record_query,
                    (
                        func_id,
                        datetime.now(),
                        pickle.dumps(trace.args),
                        pickle.dumps(trace.return_value),
                    ),
                )

    def get_records(
        self, func_qualname: str, limit: int = 2000
    ) -> List[FuncRecordThunk]:
        get_func_query = """
            SELECT id
            FROM goldenrun_func
            WHERE qualname = ?
        """
        get_records_query = """
            SELECT created_at, serialized_args, serialized_return
            FROM goldenrun_record
            WHERE func_id = ?
        """
        with self.conn as conn:
            _id = conn.execute(get_func_query, (func_qualname,)).fetchone()[0]
            return conn.execute(get_records_query, (_id,)).fetchall()

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
