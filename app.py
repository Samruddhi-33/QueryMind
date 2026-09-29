"""QueryMind - Streamlit UI.  Run: streamlit run app.py"""
import streamlit as st

from querymind import config
from querymind.charts import auto_chart
from querymind.database import create_sample_db, csvs_to_sqlite, get_schema, run_query
from querymind.engine import QueryMind
from querymind.llm import LLMClient
from querymind.sql_guard import UnsafeSQLError, validate_sql

st.set_page_config(page_title="QueryMind", page_icon="🧠", layout="wide")
EXAMPLES = [
    "Top 5 products by total revenue",
    "Monthly revenue trend for completed orders",
    "Which region has the most customers?",
    "Return rate (returned orders / all orders) by product category",
]

with st.sidebar:
    st.title("🧠 QueryMind")
    key = st.text_input("Anthropic API key", type="password", value=config.ANTHROPIC_API_KEY)
    llm = LLMClient(api_key=key)
    st.caption("🟢 LLM ready" if llm.available else "🟠 No API key - use the SQL editor tab")
    source = st.radio("Data source", ["Sample sales database", "Upload CSV files", "Upload SQLite file"])

db_path = config.SAMPLE_DB
if source == "Sample sales database":
    if not db_path.exists():
        create_sample_db(db_path)
elif source == "Upload CSV files":
    files = st.sidebar.file_uploader("CSV files (one table each)", type="csv", accept_multiple_files=True)
    if not files:
        st.info("Upload one or more CSV files in the sidebar.")
        st.stop()
    db_path = csvs_to_sqlite(config.UPLOAD_DB, {f.name: f.getvalue() for f in files})
else:
    up = st.sidebar.file_uploader("SQLite file", type=["db", "sqlite", "sqlite3"])
    if not up:
        st.info("Upload a SQLite database in the sidebar.")
        st.stop()
    config.UPLOAD_DB.parent.mkdir(exist_ok=True)
    config.UPLOAD_DB.write_bytes(up.getvalue())
    db_path = config.UPLOAD_DB

st.header("Ask your database in plain English")
with st.expander("Database schema"):
    st.code(get_schema(db_path), language="sql")

tab_ask, tab_sql = st.tabs(["💬 Ask", "🛠 SQL editor"])


def show(df, sql):
    st.code(sql, language="sql")
    st.dataframe(df, width="stretch")
    fig = auto_chart(df)
    if fig is not None:
        st.plotly_chart(fig, width="stretch")
    st.download_button("Download CSV", df.to_csv(index=False), "result.csv", "text/csv")


with tab_ask:
    cols = st.columns(len(EXAMPLES))
    for c, ex in zip(cols, EXAMPLES):
        if c.button(ex, width="stretch"):
            st.session_state["q"] = ex
    question = st.text_input("Your question", key="q", placeholder="e.g. Who are our top 10 customers by spend?")
    if st.button("Run", type="primary") and question:
        if not llm.available:
            st.warning("Add an Anthropic API key in the sidebar (or use the SQL editor tab).")
        else:
            with st.spinner("Writing and running SQL..."):
                engine = QueryMind(db_path, llm)
                res = engine.ask(question)
            if res.error or res.df is None:
                st.error(f"Could not answer: {res.error}")
                st.code(res.sql, language="sql")
            else:
                if res.attempts > 1:
                    st.caption("Auto-corrected after a first failed attempt.")
                try:
                    st.success(engine.explain(res))
                except Exception:  # noqa: BLE001
                    pass
                show(res.df, res.sql)

with tab_sql:
    sql = st.text_area("SELECT query", "SELECT category, ROUND(AVG(price),2) AS avg_price FROM products GROUP BY category", height=120)
    if st.button("Execute"):
        try:
            show(run_query(db_path, validate_sql(sql), config.MAX_ROWS, config.QUERY_TIMEOUT_SEC), sql)
        except (UnsafeSQLError, Exception) as exc:  # noqa: BLE001
            st.error(exc)
