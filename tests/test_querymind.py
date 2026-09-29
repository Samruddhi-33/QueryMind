import pytest

from querymind.charts import auto_chart
from querymind.database import create_sample_db, get_schema, run_query
from querymind.engine import QueryMind
from querymind.llm import extract_sql
from querymind.sql_guard import UnsafeSQLError, validate_sql


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    return create_sample_db(tmp_path_factory.mktemp("d") / "t.db", n_orders=200)


class FakeLLM:
    def __init__(self, replies):
        self.replies = list(replies)

    def generate(self, prompt, system="", max_tokens=0):
        return self.replies.pop(0)


@pytest.mark.parametrize("sql", [
    "DROP TABLE customers", "DELETE FROM orders", "SELECT 1; DROP TABLE orders",
    "UPDATE products SET price=0", "PRAGMA table_info(orders)", "",
])
def test_guard_blocks_unsafe(sql):
    with pytest.raises(UnsafeSQLError):
        validate_sql(sql)


def test_guard_allows_select_and_literals():
    assert validate_sql("SELECT * FROM orders WHERE status = 'delete';") == "SELECT * FROM orders WHERE status = 'delete'"
    assert validate_sql("WITH a AS (SELECT 1 x) SELECT * FROM a")


def test_extract_sql():
    assert extract_sql("here:\n```sql\nSELECT 1\n```") == "SELECT 1"


def test_schema_and_query(db):
    assert "CREATE TABLE orders" in get_schema(db)
    df = run_query(db, "SELECT region, COUNT(*) n FROM customers GROUP BY region")
    assert df["n"].sum() == 200


def test_readonly_connection_blocks_writes(db):
    with pytest.raises(Exception):
        run_query(db, "SELECT 1", max_rows=1)
        from querymind.database import connect_readonly
        connect_readonly(db).execute("DELETE FROM orders")


def test_engine_self_corrects(db):
    llm = FakeLLM(["```sql\nSELECT nonexistent FROM orders\n```",
                   "```sql\nSELECT status, COUNT(*) AS n FROM orders GROUP BY status\n```"])
    res = QueryMind(db, llm).ask("orders by status")
    assert res.error is None and res.attempts == 2 and len(res.df) >= 2


def test_engine_rejects_destructive(db):
    llm = FakeLLM(["DELETE FROM orders", "DROP TABLE orders"])
    res = QueryMind(db, llm).ask("wipe everything")
    assert res.error and res.df is None


def test_auto_chart(db):
    df = run_query(db, "SELECT category, AVG(price) p FROM products GROUP BY category")
    assert auto_chart(df) is not None
