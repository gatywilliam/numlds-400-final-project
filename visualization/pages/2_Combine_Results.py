"""Simple charts of the official combine results."""

import altair as alt
import pandas as pd
import streamlit as st

from data import BLUE, DRILLS, apply_filters, combine_results, require_db, sidebar_filters

st.set_page_config(page_title="Combine Results", page_icon="🏈", layout="wide")
require_db()
positions, years = sidebar_filters()
st.title("Combine Results")

df = apply_filters(combine_results(), positions, years)
pos_col = "position_group"

if df.empty:
    st.info("No players match the sidebar filters.")
    st.stop()

tooltip = ["display_name", "nfl_position", "college_name", "forty", "combine_weight", "draft_round"]

# 1. Players per position
st.subheader("Players per NFL position")
counts = df["nfl_position"].value_counts().rename_axis("nfl_position").reset_index(name="players")
st.altair_chart(
    alt.Chart(counts).mark_bar(color=BLUE, cornerRadiusEnd=4).encode(
        x=alt.X("players:Q", title="Players"),
        y=alt.Y("nfl_position:N", sort="-x", title=None),
        tooltip=["nfl_position", "players"],
    ),
    width="stretch",
)

# 2. 40-yard dash by position
st.subheader("40-yard dash time by position")
st.caption("Each dot is one player. Lower is faster. Hover a dot for details.")
forty = df.dropna(subset=["forty"])
order = forty.groupby(pos_col)["forty"].median().sort_values().index.tolist()
st.altair_chart(
    alt.Chart(forty).mark_circle(size=60, color=BLUE, opacity=0.6, stroke="white", strokeWidth=1).encode(
        x=alt.X("forty:Q", title="40-yard dash (s)", scale=alt.Scale(zero=False)),
        y=alt.Y(f"{pos_col}:N", sort=order, title=None),
        yOffset="jitter:Q",
        tooltip=tooltip,
    ).transform_calculate(jitter="random()").properties(height=40 * len(order)),
    width="stretch",
)

# 3. Weight vs 40 time
left, right = st.columns(2)
with left:
    st.subheader("Weight vs 40-yard dash")
    st.caption("Heavier players are usually slower.")
    st.altair_chart(
        alt.Chart(forty.dropna(subset=["combine_weight"])).mark_circle(
            size=60, color=BLUE, opacity=0.6, stroke="white", strokeWidth=1
        ).encode(
            x=alt.X("combine_weight:Q", title="Weight (lb)", scale=alt.Scale(zero=False)),
            y=alt.Y("forty:Q", title="40-yard dash (s)", scale=alt.Scale(zero=False)),
            tooltip=tooltip,
        ),
        width="stretch",
    )

# 4. Athleticism score by draft round
with right:
    st.subheader("Athleticism score by draft round")
    st.caption("Average NGS athleticism score of players drafted in each round.")
    scored = df.dropna(subset=["ngs_athleticism_score", "draft_round"]).copy()
    if scored.empty:
        st.info("No athleticism scores for these filters.")
    else:
        scored["draft_round"] = scored["draft_round"].astype(int)
        by_round = scored.groupby("draft_round", as_index=False).agg(
            avg_score=("ngs_athleticism_score", "mean"), players=("nfl_id", "count")
        )
        st.altair_chart(
            alt.Chart(by_round).mark_bar(color=BLUE, cornerRadiusEnd=4).encode(
                x=alt.X("draft_round:O", title="Draft round", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("avg_score:Q", title="Avg athleticism score"),
                tooltip=["draft_round", alt.Tooltip("avg_score:Q", format=".1f"), "players"],
            ),
            width="stretch",
        )

# 5. Distribution of any drill
st.subheader("Drill distribution")
metric = st.selectbox("Drill", list(DRILLS), format_func=lambda c: DRILLS[c][0])
vals = df.dropna(subset=[metric])
st.altair_chart(
    alt.Chart(vals).mark_bar(color=BLUE, cornerRadiusEnd=4).encode(
        x=alt.X(f"{metric}:Q", bin=alt.Bin(maxbins=30), title=DRILLS[metric][0]),
        y=alt.Y("count():Q", title="Players"),
        tooltip=[alt.Tooltip("count():Q", title="Players")],
    ),
    width="stretch",
)

with st.expander("Table"):
    st.dataframe(df, width="stretch", hide_index=True)
