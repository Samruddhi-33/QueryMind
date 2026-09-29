"""SQLite helpers: sample data, schema introspection, safe read-only execution."""
import io
import random
import re
import sqlite3
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

SCHEMA = """
CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT, region TEXT, signup_date TEXT);
CREATE TABLE products (product_id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT, price REAL);
CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER REFERENCES customers(customer_id), order_date TEXT, status TEXT);
CREATE TABLE order_items (item_id INTEGER PRIMARY KEY, order_id INTEGER REFERENCES orders(order_id), product_id INTEGER REFERENCES products(product_id), quantity INTEGER, unit_price REAL);
"""

FIRST = ["Aarav", "Priya", "Rohan", "Sneha", "Vikram", "Ananya", "Karan", "Meera", "Arjun", "Isha", "Rahul", "Neha"]
LAST = ["Sharma", "Patel", "Singh", "Iyer", "Gupta", "Reddy", "Nair", "Joshi", "Mehta", "Kulkarni"]
REGIONS = ["North", "South", "East", "West"]
CATEGORIES = {
    "Electronics": ["Headphones", "Smartwatch", "Power Bank", "Speaker", "Webcam", "Keyboard"],
    "Home": ["Desk Lamp", "Air Fryer", "Cookware Set", "Vacuum Cleaner", "Bedsheet Set"],
    "Fitness": ["Yoga Mat", "Dumbbells", "Resistance Bands", "Skipping Rope", "Water Bottle"],
    "Books": ["Data Science Handbook", "Python Cookbook", "Deep Learning Guide", "SQL in 10 Minutes"],
}


def create_sample_db(path, seed: int = 42, n_orders: int = 1500) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    rng = random.Random(seed)
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)

    start = date(2025, 1, 1)
    customers = []
    for cid in range(1, 201):
        name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        customers.append((cid, name, f"{name.lower().replace(' ', '.')}{cid}@example.com",
                          rng.choice(REGIONS), str(start + timedelta(days=rng.randint(0, 200)))))
    con.executemany("INSERT INTO customers VALUES (?,?,?,?,?)", customers)

    products, pid = [], 1
    for cat, names in CATEGORIES.items():
        for n in names:
            products.append((pid, n, cat, round(rng.uniform(9, 250), 2)))
            pid += 1
    con.executemany("INSERT INTO products VALUES (?,?,?,?)", products)

    item_id = 1
    for oid in range(1, n_orders + 1):
        odate = start + timedelta(days=rng.randint(0, 364))
        status = rng.choices(["completed", "returned", "cancelled"], [0.85, 0.08, 0.07])[0]
        con.execute("INSERT INTO orders VALUES (?,?,?,?)", (oid, rng.randint(1, 200), str(odate), status))
        for _ in range(rng.randint(1, 4)):
            p = rng.choice(products)
            con.execute("INSERT INTO order_items VALUES (?,?,?,?,?)",
                        (item_id, oid, p[0], rng.randint(1, 3), p[3]))
            item_id += 1
    con.commit()
    con.close()
    return path


def csvs_to_sqlite(path, files: dict) -> Path:
    """files: {filename: bytes}. Each CSV becomes a table."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    con = sqlite3.connect(path)
    for fname, data in files.items():
        table = re.sub(r"\W+", "_", Path(fname).stem).strip("_").lower() or "table1"
        pd.read_csv(io.BytesIO(data)).to_sql(table, con, index=False)
    con.close()
    return path


def connect_readonly(path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{Path(path).resolve().as_posix()}?mode=ro", uri=True)


def get_schema(path, sample_rows: int = 2) -> str:
    con = connect_readonly(path)
    try:
        tables = con.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        parts = []
        for name, ddl in tables:
            rows = con.execute(f'SELECT * FROM "{name}" LIMIT {sample_rows}').fetchall()
            parts.append(f"{ddl.strip()}\n-- sample rows: {rows}")
        return "\n\n".join(parts)
    finally:
        con.close()


def run_query(path, sql: str, max_rows: int = 1000, timeout: float = 10) -> pd.DataFrame:
    """Execute a (validated) query on a read-only connection with a time limit."""
    con = connect_readonly(path)
    start = time.time()
    con.set_progress_handler(lambda: 1 if time.time() - start > timeout else 0, 10000)
    try:
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        return pd.DataFrame(cur.fetchmany(max_rows), columns=cols)
    finally:
        con.close()
