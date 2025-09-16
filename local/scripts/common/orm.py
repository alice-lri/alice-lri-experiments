import sqlite3
from typing import TypeVar

T = TypeVar("T", bound="BaseModel")

class Database:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def execute(self, query: str, params: tuple = ()):
        cur = self.conn.cursor()
        cur.execute(query, params)
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
            bool: "INTEGER",  # SQLite has no native boolean
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
            placeholders = ", ".join("?" for _ in self.__fields__)
            db.execute(
                f"INSERT INTO {self.__table__} ({', '.join(self.__fields__)}) VALUES ({placeholders})",
                tuple(getattr(self, f) for f in self.__fields__)
            )
            self.id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        else:
            set_clause = ", ".join(f"{f}=?" for f in self.__fields__)
            db.execute(
                f"UPDATE {self.__table__} SET {set_clause} WHERE id=?",
                tuple(getattr(self, f) for f in self.__fields__) + (self.id,)
            )

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

"""
class User(OrmEntity, table_name="users"):
    id: int
    name: str
    email: str
    age: int


if __name__ == "__main__":
    db = Database("test.db")

    # Create table automatically
    User.create_table(db)

    # Create a user
    u = User(name="Alice", email="alice@example.com", age=30)
    u.save(db)

    # Retrieve
    user = User.get(db, u.id)
    print(user.id, user.name, user.email, user.age)

    # Update
    user.age = 31
    user.save(db)

    # List all
    for u in User.all(db):
        print(u.id, u.name, u.email, u.age)

    # Delete
    user.delete(db)
    db.close()
"""