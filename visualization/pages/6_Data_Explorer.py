"""Browse any table in the database."""

import streamlit as st

from data import list_tables, load_table, require_db, sidebar_filters

st.set_page_config(page_title="Data Explorer", page_icon="🏈", layout="wide")
require_db()
sidebar_filters()
st.title("Data Explorer")
st.caption("Raw tables. The sidebar filters do not apply here.")

tables = list_tables()
c1, c2 = st.columns([3, 1])
table = c1.selectbox("Table", tables["table"])
limit = c2.number_input("Rows to load", min_value=100, max_value=1_000_000, value=10_000, step=1000)

df = load_table(table, limit)
total = int(tables.loc[tables["table"] == table, "rows"].iloc[0])
st.caption(f"Showing {len(df):,} of {total:,} rows, {df.shape[1]} columns")
st.dataframe(df, width="stretch")

st.subheader("Summary statistics")
st.dataframe(df.describe(include="all").T, width="stretch")
