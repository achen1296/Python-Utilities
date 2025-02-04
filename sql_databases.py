import csv
import json
import os
import sqlite3
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
sqlite3.register_converter("list", convert_json)
# all other JSON types (string, number, boolean, and null) are already representable directly in Python, but these are useful to provide for PARSE_COLNAMES conversions
sqlite3.register_converter("str", lambda b: b.decode())
sqlite3.register_converter("int", int)
sqlite3.register_converter("bool", bool)


def _col_str(columns: Iterable[str]):
    return ",".join(f'"{c}"' for c in columns)


class Database:
    def __init__(self, db_file: str | Path):
        self.db_file = Path(db_file)
        self.con = sqlite3.connect(self.db_file, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        self.cur = self.con.cursor()
        self.con.row_factory = sqlite3.Row

    def tables(self) -> list[str]:
        with self.con:
            return [name[0].lower() for name in self.cur.execute(""" select name from sqlite_schema where type = 'table' """).fetchall()]

    def create_table(self, name: str, columns: Iterable[str | tuple[str, str]], primary_keys: Iterable[str]):
        """ `columns`: `Iterable` of either just the column name or `tuple` of the column's name and declared type. """

        col_str = ",".join(f'"{c}"' if isinstance(c, str) else f'"{c[0]}" "{c[1]}"' for c in columns)
        primary_keys_str = _col_str(primary_keys)
        with self.con:
            self.cur.execute(f""" create table \"{name}\" ( {col_str}, primary key ({primary_keys_str}) ) """)
        return self.table(name)

    @cache
    def table(self, name: str):
        return Table(self, name)


class TableNotFound(Exception):
    pass


class ExtraData(Exception):
    pass


class Table:
    # not worrying about SQL injection here

    def __init__(self, db: Database, name: str):
        self.db = db
        self.con = db.con
        self.cur = db.con.cursor()
        self.name = name

        self.altered_table = True
        self.columns  # evaluate for existence check

    @property
    def columns(self) -> tuple[str]:
        if self.altered_table:
            with self.con:
                cols = tuple(name[0].lower() for name in self.cur.execute(""" select name from pragma_table_info(?) """, (self.name, )).fetchall())
            if not cols:
                raise TableNotFound(self.name)
            self._columns = cols
        return self._columns

    @property
    @cache  # primary keys cannot be changed except by recreating the table
    def primary_keys(self) -> tuple[str]:
        with self.con:
            cols = tuple(name[0].lower() for name in self.cur.execute(""" select name from pragma_table_info(?) where pk > 0 """, (self.name, )).fetchall())
        if not cols:
            raise TableNotFound(self.name)
        return cols

    def _parse_row(self, row: Mapping[str, Any] | Sequence, *, add_missing_columns: bool, add_column_types: bool, ignore_extra_data: bool):
        if isinstance(row, Mapping):
            if add_missing_columns:
                with self.con:
                    for c in row.keys():
                        if c.lower() not in self.columns:
                            col_definition = f'"{c.lower()}"'
                            if add_column_types:
                                col_definition += f' "{type(row[c]).__name__}"'
                            self.cur.execute(f""" alter table {self.name} add column {col_definition} """)
                self.altered_table = True
            elif not ignore_extra_data:
                extra_keys = [c for c in row.keys() if c.lower() not in self.columns]
                if extra_keys:
                    raise ExtraData(extra_keys)
            operation_cols = [c for c in self.columns if c in row]
            params = [row[c] for c in operation_cols]
        else:
            lr = len(row)
            lc = len(self.columns)
            if not ignore_extra_data and lr > lc:
                raise ExtraData(row[lc:])
            operation_cols = self.columns[:lr]
            params = list(row[:lc])
        return operation_cols, params

    def insert(self, row: Mapping[str, Any] | Sequence, *, add_missing_columns: bool = False, add_column_types=True, ignore_extra_data=False, upsert=False):
        """ If `add_missing_columns`, will add keys of a `row` that is a `Mapping` as new columns if one with the same name doesn't exist (SQLite columns are case-insensitive), and if `add_column_types`, will add declared column types using `type(v).__name__`. Else, if `ignore_extra_data`, ignores the additional keys, otherwise raise an exception.

        If `row` is a `Sequence` with length at most the number of columns, always succeeds. Otherwise, either ignores or raises an exception based on `ignore_extra_data`. Cannot add new columns this way because a name is not provided. """

        operation_cols, params = self._parse_row(row, add_missing_columns=add_missing_columns, add_column_types=add_column_types, ignore_extra_data=ignore_extra_data)
        sql = f""" insert into {self.name} ({_col_str(operation_cols)}) values({",".join("?"*len(params))}) """
        if upsert:
            sql += f""" on conflict do update set ({_col_str(operation_cols)}) = ({",".join("?"*len(params))}) """
            params = params + params

        with self.con:
            self.cur.execute(sql, params)

    def import_csv(self, csv_file: Path | str, *, add_missing_columns: bool = False, ignore_extra_data=False, upsert=False):
        """ Cannot add types to columns this way, as CSV reader would of course always produce string values. """
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
            self.cur.execute(""" drop table if exists temp_table """)

        os.system(f""" sqlite3 "{self.db.db_file}" ".import '{csv_file}' temp_table --csv" """)

        sql = f""" insert into \"{self.name}\" ({_col_str(operation_cols)})
        select {_col_str(operation_cols)} from temp_table where true """  # where true needed for upsert clause https://sqlite.org/lang_upsert.html 2.2
        if upsert:
            sql += f""" on conflict do update set ({_col_str(operation_cols)}) = ({",".join(f"excluded.\"{c}\"" for c in operation_cols)}) """
        else:
            sql += "on conflict do nothing"

        with self.con:
            self.cur.execute(sql)
            self.cur.execute("drop table if exists temp_table")

    def upsert(self, row: Mapping[str, Any] | Sequence, *, upsert=True, **kwargs,):
        """ See `insert`. """
        return self.insert(row, upsert=True, **kwargs)

    def update(self, row: Mapping[str, Any] | Sequence, where: str, *, add_missing_columns: bool = False, add_column_types=True, ignore_extra_data=False):
        """ See `insert`. """
        operation_cols, params = self._parse_row(row, add_missing_columns=add_missing_columns, add_column_types=add_column_types, ignore_extra_data=ignore_extra_data)
        sql = f""" update {self.name} set ({_col_str(operation_cols)}) = ({",".join("?"*len(params))}) where {where} """
        with self.con:
            self.cur.execute(sql, params)

    def select(self, columns: Iterable[str] | None = None, where: str = "true", *, as_types: Mapping[str, str] = {}) -> list[sqlite3.Row]:
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
            return self.cur.execute(sql).fetchall()

    def delete(self, where: str = "true"):
        with self.con:
            sql = f""" delete from {self.name} where {where} """
            self.cur.execute(sql)

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
