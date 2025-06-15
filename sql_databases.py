# (c) Andrew Chen (https://github.com/achen1296)

import csv
import json
import os
import re
import sqlite3
from datetime import datetime
from functools import cache
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

sqlite3.enable_callback_tracebacks(True)


def adapt_json_serializable(d: dict | list):
    return json.dumps(d)


sqlite3.register_adapter(dict, adapt_json_serializable)
sqlite3.register_adapter(list, adapt_json_serializable)


def convert_json(b: bytes):
    return json.loads(b)


sqlite3.register_converter("json", convert_json)
sqlite3.register_converter("dict", convert_json)
sqlite3.register_converter("object", convert_json)
sqlite3.register_converter("obj", convert_json)
sqlite3.register_converter("list", convert_json)
sqlite3.register_converter("array", convert_json)


def adapt_datetime(d: datetime):
    return d.isoformat()


sqlite3.register_adapter(datetime, adapt_datetime)


def convert_datetime(b: bytes):
    return datetime.fromisoformat(b.decode())


sqlite3.register_converter("date", convert_datetime)
sqlite3.register_converter("time", convert_datetime)
sqlite3.register_converter("datetime", convert_datetime)


def adapt_bool(b: bool):
    return int(b)


sqlite3.register_adapter(bool, adapt_bool)


def convert_bool(b: bytes):
    """ Numbers: 0 is false and anything else is true.
    Text: keywords "true" or "false", case-insensitive with surrounding whitespace stripped, anything else results in `ValueError`. """
    try:
        return float(b) != 0.
    except ValueError:
        pass
    b = b.lower().strip()
    if b == b"true":
        return True
    if b == b"false":
        return False
    raise ValueError(b)


sqlite3.register_converter("bool", convert_bool)

sqlite3.register_converter("str", lambda b: b.decode())
sqlite3.register_converter("int", int)
sqlite3.register_converter("integer", int)
sqlite3.register_converter("float", float)
sqlite3.register_converter("real", float)


def convert_lenient_int(b: bytes):
    """ Find first instance of text convertbile to int (decimal only) and use that, discarding the rest. """
    m = re.search(b"(\\+|-)?\\d+", b)
    if not m:
        raise ValueError(b)
    return int(m.group(0))


# https://docs.python.org/3/library/functions.html#float
LENIENT_FLOAT_RE = re.compile(
    b"""(\\+|-)? # sign
        ( # value
            inf(inity)?|nan| # special value keywords
            (
                ( \\d*\\.\\d+ | \\d+\\.? ) # digits
                ( e # optional exponent
                    (\\+|-)? # exponent sign
                    \\d+ # exponent digits
                )?
            )
        )
    """,
    re.VERBOSE | re.I
)


def convert_lenient_float(b: bytes):
    """ Find first instance of text convertbile to float and use that, discarding the rest. """
    m = re.search(LENIENT_FLOAT_RE, b)
    if not m:
        raise ValueError(b)
    return float(m.group(0))


sqlite3.register_converter("lenient float", convert_lenient_float)
sqlite3.register_converter("lenient_float", convert_lenient_float)
sqlite3.register_converter("lenient real", convert_lenient_float)
sqlite3.register_converter("lenient_real", convert_lenient_float)
sqlite3.register_converter("lenient integer", convert_lenient_int)
sqlite3.register_converter("lenient_integer", convert_lenient_int)
sqlite3.register_converter("lenient int", convert_lenient_int)
sqlite3.register_converter("lenient_int", convert_lenient_int)


def col_str(column: str | tuple[str, str], table: str | None = None):
    if isinstance(column, str):
        c = f'"{column.lower()}"'
    else:
        c = f'"{column[0].lower()}" "{column[1]}"'
    if table is not None:
        return f'"{table}".{c}'
    else:
        return c


def col_name_type(column: str | tuple[str, str]) -> tuple[str, str]:
    if isinstance(column, str):
        return column.lower(), ""
    else:
        return (column[0].lower(), column[1])


def cols_strs(columns: Mapping[str, str] | Iterable[str | tuple[str, str]], table: str | None = None) -> list:
    """ `columns`: `Iterable` of either just the column name or `tuple` of the column's name and declared type, or `Mapping` of column name and type. """
    if isinstance(columns, Mapping):
        return [col_str((c, columns[c]), table=table) for c in columns]  # type:ignore
    else:
        return [col_str(c, table=table) for c in columns]


def cols_names_types(columns: Mapping[str, str] | Iterable[str | tuple[str, str]]) -> Mapping[str, str]:
    if isinstance(columns, Mapping):
        return columns  # type:ignore
    else:
        return {
            c: t
            for c, t in (col_name_type(col) for col in columns)
        }


def cols_joined_str(columns: Mapping[str, str] | Iterable[str | tuple[str, str]], table: str | None = None) -> str:
    return ",".join(cols_strs(columns, table=table))


class Row(sqlite3.Row):
    def __repr__(self):
        return repr(dict(**self))

    def __str__(self):
        return str(dict(**self))


def _add_connection_features(con: sqlite3.Connection):
    con.row_factory = Row
    con.create_function("regexp", 2, lambda p, s: bool(re.search(p, s, re.I)), deterministic=True)


class Database:
    def __init__(self, db_file: str | Path, timeout=60.):
        self.db_file = Path(db_file)
        self.con = sqlite3.connect(self.db_file, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES, timeout=timeout)
        self.cur = self.con.cursor()
        _add_connection_features(self.con)

    @property
    def tables(self) -> list[str]:
        with self.con:
            return [name[0].lower() for name in self.cur.execute(""" select name from sqlite_schema where type = 'table' """).fetchall()]

    def create_table(self, name: str, columns: Mapping[str, str] | Iterable[str | tuple[str, str]], primary_keys: Iterable[str]):
        cs = cols_joined_str(columns)
        primary_keys_str = cols_joined_str(primary_keys)
        with self.con:
            self.cur.execute(f""" create table \"{name}\" ( {cs}, primary key ({primary_keys_str}) ) """)
        return self.table(name)

    @cache
    def table(self, name: str):
        return Table(self, name)

    def create_sql(self) -> list[str]:
        return [r[0] for r in self.cur.execute(f""" select sql from sqlite_schema where sql is not null """).fetchall()]

    def synchronize_definition_file(self, db_definition_file: Path | str):
        # the database file is not expected to be reconstructed often if at all, this code is mostly to document the intent of matching the saved table definitions in git
        db_definition_file = Path(db_definition_file)
        tables = self.tables
        if db_definition_file.exists():
            with open(db_definition_file) as f:
                for line in f:
                    m = re.match("create table \"?(.*?)\"? ?\\(", line, re.I)
                    assert m
                    t = m.group(1)
                    if t not in tables:
                        self.cur.execute(line)
        with open(db_definition_file, "w") as f:
            for sql in self.create_sql():
                print(sql, file=f)


class TableNotFound(Exception):
    pass


class ExtraData(Exception):
    pass


RowType = Mapping[str, Any] | Sequence | sqlite3.Row


class Table:
    # not worrying about SQL injection here
    def __init__(self, db: Database, name: str):
        self.db = db
        self.con = db.con
        self.cur = db.con.cursor()
        self.name = name

        self.altered_table = True
        self.columns  # evaluate for existence check

        # _add_connection_features(self.con) # already done by db __init__

    def _cache_columns_and_types(self):
        if self.altered_table:
            with self.con:
                cols_and_types = self.cur.execute(""" select name, type from pragma_table_info(?) """, (self.name, )).fetchall()
            if not cols_and_types:
                raise TableNotFound(self.name)
            self._columns: tuple[str, ...] = tuple(c[0] for c in cols_and_types)
            self._column_types: tuple[str, ...] = tuple(c[1] for c in cols_and_types)

            self.altered_table = False

    @property
    def columns(self) -> tuple[str, ...]:
        self._cache_columns_and_types()
        return self._columns

    @property
    def column_types(self) -> tuple[str, ...]:
        self._cache_columns_and_types()
        return self._column_types

    @property
    def columns_and_types(self) -> tuple[tuple[str, str], ...]:
        return tuple(zip(self._columns, self._column_types))

    def add_columns(self, columns: Mapping[str, str] | Iterable[str | tuple[str, str]]):
        """ Adds columns, unless they are already in the table. Returns `True` if any new columns were added, `False` otherwise. """
        with self.con:
            added_any = False
            existing_cols = [c.lower() for c in self.columns]
            for c, t in cols_names_types(columns).items():
                if c.lower() not in existing_cols:
                    added_any = True
                    if t:
                        self.cur.execute(f""" alter table "{self.name}" add column {col_str((c, t))} """)
                    else:
                        self.cur.execute(f""" alter table "{self.name}" add column {col_str(c)} """)
            return added_any

    @property
    @cache  # primary keys cannot be changed except by recreating the table
    def primary_keys(self) -> tuple[str]:
        with self.con:
            cols = tuple(name[0].lower() for name in self.cur.execute(""" select name from pragma_table_info(?) where pk > 0 """, (self.name, )).fetchall())
        if not cols:
            raise TableNotFound(self.name)
        return cols

    def _parse_row(self, row: RowType, *, add_missing_columns: bool, add_column_types: bool, ignore_extra_data: bool):
        if isinstance(row, Mapping) or isinstance(row, sqlite3.Row):
            keys = row.keys()
            lower_columns = [c.lower() for c in self.columns]
            if add_missing_columns:
                if add_column_types:
                    cols = {
                        c: type(row[c]).__name__
                        for c in row.keys()
                    }
                else:
                    cols = [c for c in keys]
                self.altered_table = self.add_columns(cols)
            elif not ignore_extra_data:
                extra_keys = [c for c in keys if c.lower() not in lower_columns]
                if extra_keys:
                    raise ExtraData(extra_keys)

            # `in row` is keys for `Mapping` but values for `sqlite3.Row`
            # need to use the case of the keys as they are in `row` for retrieving them below
            operation_cols = [c for c in keys if c.lower() in lower_columns]
            params = [row[c] for c in operation_cols]
        else:
            lr = len(row)
            lc = len(self.columns)
            if not ignore_extra_data and lr > lc:
                raise ExtraData(row[lc:])
            operation_cols = self.columns[:lr]
            params = list(row[:lc])
        return operation_cols, params

    def insert(self, row: RowType, *, add_missing_columns: bool = False, add_column_types=True, ignore_extra_data=False, upsert=False):
        """ If `add_missing_columns`, will add keys of a `row` that is a `Mapping` as new columns if one with the same name doesn't exist (SQLite columns are case-insensitive), and if `add_column_types`, will add declared column types using `type(v).__name__`. Else, if `ignore_extra_data`, ignores the additional keys, otherwise raise an exception.

        If `row` is a `Sequence` with length at most the number of columns, always succeeds. Otherwise, either ignores or raises an exception based on `ignore_extra_data`. Cannot add new columns this way because a name is not provided.

        Note: `sqlite3.Row` is treated as a `Mapping`, not a `Sequence`. It is designed such that it could be treated as either in many ways. """

        operation_cols, params = self._parse_row(row, add_missing_columns=add_missing_columns, add_column_types=add_column_types, ignore_extra_data=ignore_extra_data)
        sql = f""" insert into {self.name} ({cols_joined_str(operation_cols)}) values({",".join("?"*len(params))}) """
        if upsert:
            sql += f""" on conflict do update set ({cols_joined_str(operation_cols)}) = ({",".join("?"*len(params))}) """
            params = params + params

        with self.con:
            self.cur.execute(sql, params)

    def upsert(self, row: RowType, *, upsert=True, **kwargs,):
        """ See `insert`. `upsert` argument is just to absorb accidentally including this argument, always passed as `True` to `insert`. """
        return self.insert(row, upsert=True, **kwargs)

    def import_csv(self, csv_file: Path | str, *, add_missing_columns: bool = False, ignore_extra_data=False, upsert=False):
        """ Cannot add types to columns this way, as CSV reader would of course always produce string values. Returns count of entries added. """
        with open(csv_file, encoding="utf-8-sig") as f:  # encoding handles byte order mark
            reader = csv.reader(f)
            try:
                csv_cols = next(reader)
            except StopIteration:
                # empty file
                return
            try:
                first_row = next(reader)
            except StopIteration:
                return  # CSV has header only, no data
            operation_cols, _ = self._parse_row({c: v for c, v in zip(csv_cols, first_row)}, add_missing_columns=add_missing_columns, add_column_types=False, ignore_extra_data=ignore_extra_data)  # update columns and get columns to operate on

        with self.con:
            self.cur.execute(""" drop table if exists csv_temp_table """)

        os.system(f""" sqlite3 "{self.db.db_file}" ".import '{csv_file}' csv_temp_table --csv" """)

        sql = f""" insert into \"{self.name}\" ({cols_joined_str(operation_cols)})
        select {cols_joined_str(operation_cols)} from csv_temp_table where true """  # where true needed for upsert clause https://sqlite.org/lang_upsert.html 2.2
        if upsert:
            sql += f""" on conflict do update set ({cols_joined_str(operation_cols)}) = ({",".join(f"excluded.\"{c}\"" for c in operation_cols)}) """
        else:
            sql += "on conflict do nothing"

        count = 0
        with self.con:
            try:
                self.cur.execute(sql)
                count = self.cur.execute("select count(*) from csv_temp_table").fetchone()[0]
            finally:
                self.cur.execute("drop table if exists csv_temp_table")

        return count

    def update(self, row: RowType, where: str, where_params=[], *, add_missing_columns: bool = False, add_column_types=True, ignore_extra_data=False):
        """ See `insert`. """
        operation_cols, params = self._parse_row(row, add_missing_columns=add_missing_columns, add_column_types=add_column_types, ignore_extra_data=ignore_extra_data)
        sql = f""" update {self.name} set ({cols_joined_str(operation_cols)}) = ({",".join("?"*len(params))}) where {where} """
        params += where_params
        with self.con:
            self.cur.execute(sql, params)

    def select(self, columns: Iterable[str] | None = None, where: str = "true", where_params=[], *, as_types: Mapping[str, str] = {}) -> list[sqlite3.Row]:
        """ Don't forget to `sqlite3.register_converter` if you use `as_types`! Some converters have already been registered for common Python built-in types. """
        if columns is None:
            columns = self.columns
        else:
            columns = [c.lower() for c in columns]
        as_types = {
            k.lower(): v
            for k, v in as_types.items()
        }
        col_str = ",".join(f"\"{c}\" as '{c} [{as_types[c]}]'" if c in as_types else f'"{c}"' for c in columns)

        with self.con:
            sql = f""" select {col_str} from {self.name} where {where} """
            return self.cur.execute(sql, where_params).fetchall()

    def delete(self, where: str = "true", where_params=[], ):
        with self.con:
            sql = f""" delete from "{self.name}" where {where} """
            self.cur.execute(sql, where_params)

    def __iter__(self):
        return iter(self.select())


if __name__ == "__main__":
    test_db_path = Path("test.db")
    if test_db_path.exists():
        os.remove(test_db_path)
    db = Database(test_db_path)
    t = db.create_table("t", [("a", "int")], ["a"])
    assert t.columns == ("a",), t.columns
    assert t.primary_keys == ("a",), t.primary_keys

    try:
        t.insert({"a": 1, "b": 2})
    except ExtraData:
        pass
    else:
        assert False
    t.insert({"a": 1, "b": 2}, ignore_extra_data=True)

    try:
        t.insert([3, 4])
    except ExtraData:
        pass
    else:
        assert False
    t.insert([3, 4], ignore_extra_data=True)

    rows = list(dict(**r) for r in t)
    assert rows == [{"a": 1}, {"a": 3}], rows

    t.insert({"a": 5, "b": 6}, add_missing_columns=True, add_column_types=False)

    assert t.columns == ("a", "b"), t.columns

    rows = list(dict(**r) for r in t)
    assert rows == [{"a": 1, "b": None}, {"a": 3, "b": None}, {"a": 5, "b": 6}], rows

    t.upsert({"a": 1, "b": {"hello": "world"}})
    rows = list(dict(**r) for r in t)
    assert rows == [{"a": 1, "b": '{"hello": "world"}'}, {"a": 3, "b": None}, {"a": 5, "b": 6}], rows

    t.update((7, ["asdf"]), "a=1")
    rows = list(dict(**r) for r in t)
    assert rows == [{"a": 7, "b": '["asdf"]'}, {"a": 3, "b": None}, {"a": 5, "b": 6}], rows

    # new column should get list type
    t.insert({"a": 8, "c": []}, add_missing_columns=True)
    selected = [dict(**r) for r in t.select(where="a=8")]
    assert selected == [{"a": 8, "b": None, "c": []}], selected

    selected = [dict(**r) for r in t.select(where="a=8", as_types={"c": "str"})]
    assert selected == [{"a": 8, "b": None, "c": "[]"}], selected

    with open("test.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["a", "c"])
        w.writerow([9, '["hello", "world"]'])
        w.writerow([7, '["bye", "world"]'])
    t.import_csv("test.csv", upsert=True)
    os.remove("test.csv")

    selected = [dict(**r) for r in t.select(where="a=9", as_types={"c": "list"})]
    assert selected == [{"a": 9, "b": None, "c": ["hello", "world"]}], selected
    selected = [dict(**r) for r in t.select(where="a=7", as_types={"c": "list"})]
    assert selected == [{"a": 7, "b": '["asdf"]', "c": ["bye", "world"]}], selected

    db.con.close()
    os.remove(test_db_path)
