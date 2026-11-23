"""
Home page of the Streamlit website for the NFL Big Data Bowl 2027 project.

Run from the repo root:
    streamlit run visualization/app.py
Other pages live in visualization/pages/ and show up in the sidebar automatically.
"""

import streamlit as st

from data import combine_results, list_tables, players, require_db, sidebar_filters

st.set_page_config(page_title="NFL Big Data Bowl 2027", page_icon="🏈", layout="wide")
require_db()
sidebar_filters()

st.title("🏈 NFL Big Data Bowl 2027")
st.markdown(
    "How do NFL Combine drills (40-yard dash, 3-cone, short shuttle) relate to how players move? "
    "Use the pages in the sidebar to explore the data."
)

tables = list_tables()
p = players()
c = combine_results()
row_counts = dict(zip(tables["table"], tables["rows"]))

col1, col2, col3, col4 = st.columns(4)
col1.metric("Players", f"{len(p):,}")
col2.metric("Combine results", f"{len(c):,}")
col3.metric("Tracking frames (combine)", f"{row_counts.get('combine_tracking', 0):,}")
col4.metric("Tables in database", len(tables))

st.subheader("Pages")
st.markdown(
    """
- **Drill Viewer**: a player's path on the field in any combine drill (from Will's EDA), speed and acceleration over time, and a top-speed leaderboard.
- **Combine Results**: 40-yard times, size vs speed, and athleticism scores by position.
- **Combine vs NFL Career**: do players who test well at the combine play more in the NFL? Includes a drill x position heatmap.
- **Route Separation**: do faster, more agile receivers get more open? And does being open lead to more catches?
- **Player Profile**: one player's combine percentiles, career and NFL stats, with an option to compare two players.
- **Data Explorer**: browse any table in the database.

Use the **sidebar filters** (position group, draft year) to narrow every page. They stay set when you switch pages.
"""
)

st.subheader("Tables")
st.dataframe(tables, hide_index=True, width="stretch")
