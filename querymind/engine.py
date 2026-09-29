"""Question -> SQL -> validated execution, with one self-correction retry."""
import sqlite3
from dataclasses import dataclass

import pandas as pd

from . import config
from .database import get_schema, run_query
from .llm import extract_sql
from .sql_guard import UnsafeSQLError, validate_sql

SYSTEM = (
    "You are an expert SQLite analyst. Convert the user's question into ONE read-only "
    "SQLite SELECT query. Use only tables/columns present in the schema. Prefer explicit "
    "JOINs, meaningful column aliases and ORDER BY for rankings. If the question cannot be "
    "answered from the schema, return: SELECT 'Cannot answer from this database' AS message. "
    "Return only the SQL inside a ```sql block."
)


@dataclass
class QueryResult:
    question: str
    sql: str = ""
    df: pd.DataFrame | None = None
    error: str | None = None
    attempts: int = 0


def build_prompt(schema: str, question: str, prev_sql: str | None = None, error: str | None = None) -> str:
    prompt = f"Database schema (SQLite):\n{schema}\n\nQuestion: {question}\n"
    if prev_sql and error:
        prompt += (f"\nYour previous query failed.\nQuery: {prev_sql}\nError: {error}\n"
                   "Fix it and return the corrected SQL.\n")
    return prompt


class QueryMind:
    def __init__(self, db_path, llm, max_rows: int = config.MAX_ROWS):
        self.db_path, self.llm, self.max_rows = db_path, llm, max_rows

    def ask(self, question: str) -> QueryResult:
        schema = get_schema(self.db_path)
        result, prev_sql, error = QueryResult(question), None, None
        for attempt in (1, 2):
            raw = self.llm.generate(build_prompt(schema, question, prev_sql, error), SYSTEM, 800)
            sql = extract_sql(raw)
            result.attempts, result.sql = attempt, sql
            try:
                result.df = run_query(self.db_path, validate_sql(sql), self.max_rows, config.QUERY_TIMEOUT_SEC)
                result.error = None
                return result
            except (UnsafeSQLError, sqlite3.Error) as exc:
                error, prev_sql, result.error = str(exc), sql, str(exc)
        return result

    def explain(self, result: QueryResult) -> str:
        if result.df is None or result.df.empty:
            return "The query returned no rows."
        prompt = (f"Question: {result.question}\nSQL: {result.sql}\n"
                  f"Result (first rows):\n{result.df.head(15).to_string(index=False)}\n\n"
                  "Answer the question in 1-3 plain-English sentences using only these results.")
        return self.llm.generate(prompt, "You explain query results to business users.", 300)
