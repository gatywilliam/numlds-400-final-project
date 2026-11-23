"""Do faster / more agile receivers get more open on their routes?"""

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from data import BLUE, DRILLS, rank_corr, apply_filters, combine_results, require_db, sidebar_filters, targets

st.set_page_config(page_title="Route Separation", page_icon="🏈", layout="wide")
require_db()
positions, years = sidebar_filters()

st.title("Route Separation")
st.caption(
    "Separation = how many yards the receiver was from the nearest defender when the ball was thrown. "
    "Only plays where the player was targeted are counted."
)

receiver_groups = [p for p in positions if p in ("WR", "TE")]
if not receiver_groups:
    st.info("This page is about receivers. Add WR or TE to the position filter in the sidebar.")
    st.stop()

players = apply_filters(combine_results(), receiver_groups, years)
t = targets().merge(players[["nfl_id", "display_name", "position_group"]], on="nfl_id")
if t.empty:
    st.info("No targets for the current filters.")
    st.stop()

routes = t["route_ran"].dropna().value_counts().index.tolist()
c1, c2, c3 = st.columns([3, 2, 1])
chosen_routes = c1.multiselect("Routes", routes, default=routes)
drill = c2.selectbox("Combine drill", ["three_cone", "short_shuttle", "forty", "ten_yd_split", "vertical", "broad_jump", "ngs_athleticism_score"],
                     format_func=lambda c: DRILLS[c][0])
min_targets = c3.number_input("Min targets", min_value=1, max_value=100, value=10)
t = t[t["route_ran"].isin(chosen_routes)]

# ---- 1. Separation by route ----
left, right = st.columns(2)
with left:
    st.subheader("Average separation by route")
    by_route = t.groupby("route_ran").agg(separation=("separation", "mean"), targets=("nfl_id", "count")).reset_index()
    st.altair_chart(
        alt.Chart(by_route).mark_bar(color=BLUE, cornerRadiusEnd=4).encode(
            x=alt.X("separation:Q", title="Average separation (yd)"),
            y=alt.Y("route_ran:N", sort="-x", title=None),
            tooltip=[alt.Tooltip("route_ran:N", title="Route"), alt.Tooltip("separation:Q", format=".2f", title="Separation (yd)"),
                     alt.Tooltip("targets:Q", title="Targets")],
        ).properties(height=360),
        width="stretch",
    )

# ---- 2. Does being open lead to catches? ----
with right:
    st.subheader("Catch rate by separation")
    bins = [0, 1, 2, 3, 4, 5, 6, np.inf]
    labels = ["0-1", "1-2", "2-3", "3-4", "4-5", "5-6", "6+"]
    t["sep_bin"] = pd.cut(t["separation"], bins=bins, labels=labels, right=False)
    catch = t.groupby("sep_bin", observed=False).agg(
        catch_rate=("pass_result", lambda s: (s == "C").mean()), targets=("nfl_id", "count")
    ).reset_index()
    st.altair_chart(
        alt.Chart(catch).mark_bar(color=BLUE, cornerRadiusEnd=4).encode(
            x=alt.X("sep_bin:N", sort=labels, title="Separation when ball was thrown (yd)", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("catch_rate:Q", title="Catch rate", axis=alt.Axis(format="%")),
            tooltip=[alt.Tooltip("sep_bin:N", title="Separation (yd)"), alt.Tooltip("catch_rate:Q", format=".0%", title="Catch rate"),
                     alt.Tooltip("targets:Q", title="Targets")],
        ).properties(height=360),
        width="stretch",
    )

# ---- 3. Combine drill vs separation, per player ----
st.subheader(f"{DRILLS[drill][0].split(' (')[0]} vs average separation")
per_player = (
    t.groupby(["nfl_id", "display_name", "position_group"])
    .agg(avg_separation=("separation", "mean"), targets=("separation", "count"))
    .reset_index()
    .merge(players[["nfl_id", drill]], on="nfl_id")
)
per_player = per_player[per_player["targets"] >= min_targets].dropna(subset=[drill])

if len(per_player) < 5:
    st.info("Not enough players with this many targets. Lower the minimum targets or widen the filters.")
else:
    lower_better = DRILLS[drill][1]
    r = rank_corr(per_player[drill], per_player["avg_separation"])
    better = -r if lower_better else r
    st.caption(
        f"Each dot is one player with at least {min_targets} targets ({len(per_player)} players). "
        f"Rank correlation: {better:+.2f} "
        f"({'better drill result goes with more separation' if better > 0 else 'better drill result does not mean more separation'}; "
        "values near 0 mean no clear relationship). "
        + ("The x-axis is flipped so better results are on the right." if lower_better else "")
    )
    base = alt.Chart(per_player).encode(
        x=alt.X(f"{drill}:Q", title=DRILLS[drill][0], scale=alt.Scale(zero=False, reverse=lower_better)),
        y=alt.Y("avg_separation:Q", title="Average separation (yd)", scale=alt.Scale(zero=False)),
    )
    dots = base.mark_circle(size=70, color=BLUE, opacity=0.7, stroke="white", strokeWidth=1).encode(
        tooltip=["display_name", "position_group", alt.Tooltip(f"{drill}:Q", title=DRILLS[drill][0]),
                 alt.Tooltip("avg_separation:Q", format=".2f", title="Avg separation (yd)"), "targets"],
    )
    trend = base.transform_regression(drill, "avg_separation").mark_line(color="#52514e", strokeDash=[4, 4], strokeWidth=2)
    st.altair_chart((dots + trend).properties(height=420), width="stretch")

    st.subheader("Most open receivers")
    top = per_player.sort_values("avg_separation", ascending=False).head(10)
    st.dataframe(
        top[["display_name", "position_group", "targets", "avg_separation", drill]].rename(columns={
            "display_name": "Player", "position_group": "Pos", "targets": "Targets",
            "avg_separation": "Avg separation (yd)", drill: DRILLS[drill][0]}),
        hide_index=True, width="stretch",
    )
