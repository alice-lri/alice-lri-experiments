import sqlite3
from typing import TypeVar

T = TypeVar("T", bound="OrmEntity")

class SQLExpr:
    def __init__(self, expr: str):
        self.expr = expr

    def __repr__(self):
        return f"SQLExpr({self.expr!r})"


class Database:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def execute(self, query: str, params: tuple = ()):
        cur = self.conn.cursor()
        cur.execute(query, params)
        self.conn.commit()
        return cur

    def executemany(self, query: str, seq_of_params: list[tuple]):
        cur = self.conn.cursor()
        cur.executemany(query, seq_of_params)
        self.conn.commit()
        return cur

    def close(self):
        self.conn.close()


class OrmEntity:
    __table__: str
    id: int

    def __init_subclass__(cls, table_name: str, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.__table__ = table_name
        cls.__fields__ = [
            field for field in cls.__annotations__.keys() if field != "id"
        ]

    def __init__(self, **kwargs):
        for field in self.__annotations__.keys():
            setattr(self, field, kwargs.get(field))

    @classmethod
    def _map_python_type_to_sql(cls, py_type: type) -> str:
        mapping = {
            int: "INTEGER",
            str: "TEXT",
            float: "REAL",
            bool: "INTEGER",
        }
        return mapping.get(py_type, "TEXT")

    @classmethod
    def create_table(cls, db: Database):
        fields_sql = []
        for field, field_type in cls.__annotations__.items():
            if field == "id":
                fields_sql.append("id INTEGER PRIMARY KEY")
            else:
                sql_type = cls._map_python_type_to_sql(field_type)
                fields_sql.append(f"{field} {sql_type}")
        db.execute(f"CREATE TABLE IF NOT EXISTS {cls.__table__} ({', '.join(fields_sql)})")

    def save(self, db: Database):
        if getattr(self, "id", None) is None:
            field_names, placeholders, params = [], [], []

            for f in self.__fields__:
                val = getattr(self, f)
                field_names.append(f)
                if isinstance(val, SQLExpr):
                    placeholders.append(val.expr)
                else:
                    placeholders.append("?")
                    params.append(val)

            sql = f"INSERT INTO {self.__table__} ({', '.join(field_names)}) VALUES ({', '.join(placeholders)})"
            db.execute(sql, tuple(params))

            self.id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        else:
            set_clause_parts, params = [], []

            for f in self.__fields__:
                val = getattr(self, f)
                if isinstance(val, SQLExpr):
                    set_clause_parts.append(f"{f}={val.expr}")
                else:
                    set_clause_parts.append(f"{f}=?")
                    params.append(val)

            sql = f"UPDATE {self.__table__} SET {', '.join(set_clause_parts)} WHERE id=?"
            params.append(self.id)
            db.execute(sql, tuple(params))

    def save_or_ignore(self, db: Database):
        try:
            self.save(db)
        except sqlite3.IntegrityError:
            pass

    def delete(self, db: Database):
        if getattr(self, "id", None) is not None:
            db.execute(f"DELETE FROM {self.__table__} WHERE id=?", (self.id,))
            self.id = None

    @classmethod
    def get(cls: type[T], db: Database, id_: int) -> T | None:
        row = db.execute(f"SELECT * FROM {cls.__table__} WHERE id=?", (id_,)).fetchone()
        return cls(**row) if row else None

    @classmethod
    def all(cls: type[T], db: Database) -> list[T]:
        rows = db.execute(f"SELECT * FROM {cls.__table__}").fetchall()
        return [cls(**row) for row in rows]

    @classmethod
    def where(cls: type[T], db: Database, condition: str, params: tuple = ()) -> list[T]:
        query = f"SELECT * FROM {cls.__table__} WHERE {condition}"
        rows = db.execute(query, params).fetchall()
        return [cls(**row) for row in rows]

    @classmethod
    def save_all(cls: type[T], db: Database, objects: list[T]):
        if not objects:
            return

        if any(getattr(obj, "id", None) is not None for obj in objects):
            raise ValueError("save_all only supports inserting new objects (id must be None).")

        field_names = cls.__fields__

        first_obj = objects[0]
        placeholders = []
        expr_mode = []

        for f in field_names:
            val = getattr(first_obj, f)
            if isinstance(val, SQLExpr):
                placeholders.append(val.expr)
                expr_mode.append("expr")
            else:
                placeholders.append("?")
                expr_mode.append("param")

        sql = f"INSERT INTO {cls.__table__} ({', '.join(field_names)}) VALUES ({', '.join(placeholders)})"

        values = []
        for obj in objects:
            row_params = []
            for f, mode in zip(field_names, expr_mode):
                val = getattr(obj, f)
                if mode == "param":
                    row_params.append(val)
                elif mode == "expr":
                    if not isinstance(val, SQLExpr):
                        raise ValueError(f"Field {f} must be SQLExpr in all rows when using save_all.")

            values.append(tuple(row_params))

        db.executemany(sql, values)

        last_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        start_id = last_id - len(objects) + 1
        for i, obj in enumerate(objects):
            obj.id = start_id + i
