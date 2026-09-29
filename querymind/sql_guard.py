"""Reject anything that is not a single read-only SELECT statement."""
import re

FORBIDDEN = {
    "insert", "update", "delete", "drop", "alter", "create", "replace", "truncate",
    "attach", "detach", "pragma", "vacuum", "reindex", "grant", "revoke",
}


class UnsafeSQLError(ValueError):
    pass


def validate_sql(sql: str) -> str:
    if not sql or not sql.strip():
        raise UnsafeSQLError("Empty SQL.")
    cleaned = sql.strip().rstrip(";").strip()
    masked = re.sub(r"'(?:[^']|'')*'", "''", cleaned)          # hide string literals
    masked = re.sub(r'"(?:[^"]|"")*"', '""', masked)            # hide quoted identifiers
    masked = re.sub(r"/\*.*?\*/", " ", masked, flags=re.S)      # block comments
    masked = re.sub(r"--[^\n]*", " ", masked)                   # line comments
    if ";" in masked:
        raise UnsafeSQLError("Only a single statement is allowed.")
    words = re.findall(r"[a-z_]+", masked.lower())
    if not words or words[0] not in ("select", "with"):
        raise UnsafeSQLError("Only SELECT queries are allowed.")
    bad = FORBIDDEN.intersection(words)
    if bad:
        raise UnsafeSQLError(f"Forbidden keyword(s): {', '.join(sorted(bad))}")
    return cleaned
