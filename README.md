# 🧠 QueryMind - Natural Language SQL Analytics

Ask questions about your data in plain English. QueryMind turns them into safe,
read-only SQL, runs them, explains the answer and draws a chart.

## Features
- **Text-to-SQL** with an LLM (Claude) that sees your live schema + sample rows
- **Self-correction**: if the SQL fails, the error is fed back for one automatic retry
- **Safety guard**: only single `SELECT`/`WITH` statements; read-only DB connection; query time limit; row cap
- **Bring your data**: sample sales DB, upload CSVs (one table each) or a SQLite file
- **Plain-English explanation**, auto chart (bar/line) and CSV download
- Manual **SQL editor** tab (works without an API key)

## Architecture
```
Question -> prompt(schema + samples) -> LLM -> SQL
        -> sql_guard.validate_sql -> read-only SQLite (timeout, row cap)
        -> (error? retry with error message) -> DataFrame -> explanation + chart
```

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # add ANTHROPIC_API_KEY
streamlit run app.py
pytest                      # run tests
```

## Project structure
```
app.py                 Streamlit UI
querymind/
  database.py          sample DB, schema introspection, safe execution
  sql_guard.py         SQL validation (blocks writes / multi-statements)
  llm.py               Claude wrapper + SQL extraction
  engine.py            text-to-SQL pipeline with retry + explanation
  charts.py            automatic chart selection
tests/                 unit tests (LLM mocked)
```

## Example questions
- Top 5 products by total revenue
- Monthly revenue trend for completed orders
- Return rate by product category

## Ideas to extend
Multi-turn follow-ups, PostgreSQL/MySQL connectors, query history & favourites, schema descriptions for better accuracy.

## License
MIT - see [LICENSE](LICENSE). Replace `<Your Name>` with your name.
