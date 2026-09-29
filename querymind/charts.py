import pandas as pd
import plotly.express as px


def auto_chart(df: pd.DataFrame):
    """Pick a sensible chart for a small 2+ column result, else None."""
    if df is None or df.shape[1] < 2 or not 2 <= len(df) <= 60:
        return None
    x, y = df.columns[0], df.columns[1]
    if not pd.api.types.is_numeric_dtype(df[y]):
        return None
    looks_temporal = df[x].astype(str).str.match(r"^\d{4}(-\d{2})?(-\d{2})?$").all()
    if looks_temporal:
        return px.line(df, x=x, y=y, markers=True)
    if pd.api.types.is_numeric_dtype(df[x]):
        return None
    return px.bar(df, x=x, y=y)
