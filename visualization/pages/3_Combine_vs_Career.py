"""Do better combine results go with longer / more successful NFL careers?"""

import altair as alt
import pandas as pd
import streamlit as st

from data import BLUE, DRILLS, rank_corr, GRAY, ORANGE, RED, apply_filters, combine_results, require_db, sidebar_filters, with_percentiles

st.set_page_config(page_title="Combine vs NFL Career", page_icon="🏈", layout="wide")
require_db()
positions, years = sidebar_filters()

st.title("Combine vs NFL Career")
st.caption(
    "Do players who test well at the combine go on to play more in the NFL? "
    "These players were drafted in 2023-2025, so careers are short and older draft classes have had more time to play."
)

OUTCOMES = {
    "career_games_started": "Career games started",
    "career_games_active": "Career games played",
    "career_snaps": "Career snaps (offense + defense)",
}

df = with_percentiles(apply_filters(combine_results(), positions, years))
if df.empty:
    st.info("No players match the sidebar filters.")
    st.stop()

c1, c2 = st.columns(2)
drill = c1.selectbox("Combine drill", list(DRILLS), format_func=lambda c: DRILLS[c][0])
outcome = c2.selectbox("NFL outcome", list(OUTCOMES), format_func=OUTCOMES.get)
drill_label, lower_better = DRILLS[drill]
outcome_label = OUTCOMES[outcome]
pct_col = f"{drill}_pct"

d = df.dropna(subset=[drill, outcome]).copy()
if len(d) < 8:
    st.info("Not enough players with this drill for the current filters.")
    st.stop()

# ---- 1. Quartile bars ----
st.subheader(f"{outcome_label} by {drill_label.split(' (')[0]} result")
st.caption("Players are split into four equal groups by how they scored compared with others at their position.")
labels = ["Bottom 25%", "25-50%", "50-75%", "Top 25%"]
d["tier"] = pd.cut(d[pct_col], bins=[0, 25, 50, 75, 100], labels=labels, include_lowest=True)
tiers = d.groupby("tier", observed=False).agg(avg=(outcome, "mean"), players=("nfl_id", "count")).reset_index()

st.altair_chart(
    alt.Chart(tiers).mark_bar(color=BLUE, cornerRadiusEnd=4).encode(
        x=alt.X("tier:N", sort=labels, title=f"{drill_label.split(' (')[0]} result within position", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("avg:Q", title=f"Average {outcome_label.lower()}"),
        tooltip=[alt.Tooltip("tier:N", title="Group"), alt.Tooltip("avg:Q", title="Average", format=".1f"),
                 alt.Tooltip("players:Q", title="Players")],
    ).properties(height=320),
    width="stretch",
)

# ---- 2. Scatter with Pro Bowl / All-Pro players highlighted ----
st.subheader("Every player")
st.caption(
    f"{'Lower' if lower_better else 'Higher'} {drill_label.split(' (')[0].lower()} is better. "
    "Orange dots are Pro Bowl or All-Pro players. Hover a dot for details."
)
st.altair_chart(
    alt.Chart(d).mark_circle(size=70, stroke="white", strokeWidth=1).encode(
        x=alt.X(f"{drill}:Q", title=drill_label, scale=alt.Scale(zero=False, reverse=lower_better)),
        y=alt.Y(f"{outcome}:Q", title=outcome_label),
        color=alt.Color("honors:N", title=None, scale=alt.Scale(domain=["Other players", "Pro Bowl / All-Pro"], range=[BLUE, ORANGE]),
                        legend=alt.Legend(orient="top")),
        opacity=alt.condition(alt.datum.honors == "Pro Bowl / All-Pro", alt.value(1), alt.value(0.55)),
        order=alt.Order("honors:N"),
        tooltip=["display_name", "position_group", "college_name", "draft_round", drill, outcome, "honors"],
    ).properties(height=420),
    width="stretch",
)
if lower_better:
    st.caption("The x-axis is flipped so that better results are always on the right.")

# ---- 3. Heatmap: which drills matter for which positions ----
st.subheader("Which drills matter for which positions?")
st.caption(
    f"Rank correlation between each drill and {outcome_label.lower()}, within each position group. "
    "Blue = players who did better on the drill played more. Red = the opposite. "
    "Values near 0 mean no relationship. Cells with fewer than 15 players are left blank."
)
rows = []
for group, g in df.groupby("position_group"):
    for col, (label, lb) in DRILLS.items():
        sub = g.dropna(subset=[col, outcome])
        if len(sub) >= 15:
            r = rank_corr(sub[col], sub[outcome])
            rows.append({"position_group": group, "drill": label, "corr": -r if lb else r, "players": len(sub)})
heat = pd.DataFrame(rows)
if heat.empty:
    st.info("Not enough players per position for the current filters.")
else:
    base = alt.Chart(heat).encode(
        x=alt.X("position_group:N", title=None, axis=alt.Axis(labelAngle=0, orient="top")),
        y=alt.Y("drill:N", title=None, sort=[v[0] for v in DRILLS.values()]),
    )
    cells = base.mark_rect(stroke="white", strokeWidth=2, cornerRadius=4).encode(
        color=alt.Color("corr:Q", title="Correlation", scale=alt.Scale(domain=[-0.5, 0, 0.5], range=[RED, GRAY, BLUE], clamp=True)),
        tooltip=[alt.Tooltip("position_group:N", title="Position"), alt.Tooltip("drill:N", title="Drill"),
                 alt.Tooltip("corr:Q", title="Correlation", format="+.2f"), alt.Tooltip("players:Q", title="Players")],
    )
    text = base.mark_text(fontSize=12).encode(
        text=alt.Text("corr:Q", format="+.2f"),
        color=alt.condition("abs(datum.corr) > 0.3", alt.value("white"), alt.value("#0b0b0b")),
    )
    st.altair_chart((cells + text).properties(height=360), width="stretch")
