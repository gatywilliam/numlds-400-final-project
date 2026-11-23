"""Plot one combine drill attempt on the field (adapted from Will's notebook), plus a top-speed leaderboard."""

import altair as alt
import matplotlib.pyplot as plt
import streamlit as st

from data import BLUE, ORANGE, apply_filters, drill_attempts, drill_frames, require_db, sidebar_filters
from field import path_length, plot_drill_path

st.set_page_config(page_title="Drill Viewer", page_icon="🏈", layout="wide")
require_db()
positions, years = sidebar_filters()

st.title("Drill Viewer")
st.caption("Pick a drill and a player to see their path on the field and how their speed and acceleration change.")

attempts = apply_filters(drill_attempts(), positions, years)
if attempts.empty:
    st.info("No players match the sidebar filters.")
    st.stop()

drills = sorted(attempts["drill_name"].unique())
default = drills.index("THREE_CONE_DRILL") if "THREE_CONE_DRILL" in drills else 0
pretty = lambda d: d.replace("_", " ").title()

c1, c2, c3 = st.columns([2, 3, 1])
drill = c1.selectbox("Drill", drills, index=default, format_func=pretty)
in_drill = attempts[attempts["drill_name"] == drill].copy()
in_drill["label"] = (in_drill["display_name"].fillna("nfl_id " + in_drill["nfl_id"].astype(str))
                     + " (" + in_drill["nfl_position"].fillna("?") + ")")
player = c2.selectbox("Player", sorted(in_drill["label"].unique()))
player_attempts = in_drill[in_drill["label"] == player].sort_values("attempt")
attempt = c3.selectbox("Attempt", player_attempts["attempt"].tolist())

row = player_attempts[player_attempts["attempt"] == attempt].iloc[0]
frames = drill_frames(row["event_id"], row["nfl_id"], row["attempt"])

if len(frames) < 2:
    st.warning("Not enough tracking frames for this attempt.")
    st.stop()

elapsed = (frames["time"].iloc[-1] - frames["time"].iloc[0]).total_seconds()
m1, m2, m3, m4 = st.columns(4)
m1.metric("Duration", f"{elapsed:.1f} s")
m2.metric("Top speed", f"{frames['s'].max():.2f} yd/s", f"{frames['s'].max() * 2.04545:.1f} mph", delta_color="off")
m3.metric("Peak acceleration", f"{frames['a'].max():.2f} yd/s²")
m4.metric("Distance", f"{path_length(frames):.1f} yd")

zoom = st.toggle("Zoom to the drill area", value=True)
fig = plot_drill_path(frames, title=f"{player}: {pretty(drill)}", zoom=zoom)
st.pyplot(fig)
plt.close(fig)

# Speed and acceleration over time: two separate charts that share the time axis
frames["elapsed_s"] = (frames["time"] - frames["time"].iloc[0]).dt.total_seconds()
hover = alt.selection_point(fields=["elapsed_s"], nearest=True, on="pointerover", empty=False)


def line_chart(col: str, title: str, color: str) -> alt.LayerChart:
    base = alt.Chart(frames).encode(x=alt.X("elapsed_s:Q", title="Seconds since drill start"))
    line = base.mark_line(color=color, strokeWidth=2).encode(y=alt.Y(f"{col}:Q", title=title))
    points = base.mark_circle(size=60, color=color).encode(
        y=f"{col}:Q",
        opacity=alt.condition(hover, alt.value(1), alt.value(0)),
        tooltip=[alt.Tooltip("elapsed_s:Q", title="Seconds", format=".1f"),
                 alt.Tooltip(f"{col}:Q", title=title, format=".2f")],
    ).add_params(hover)
    rule = base.mark_rule(color="gray").encode(opacity=alt.condition(hover, alt.value(0.5), alt.value(0)))
    return (line + points + rule).properties(height=220)


left, right = st.columns(2)
with left:
    st.subheader("Speed")
    st.altair_chart(line_chart("s", "Speed (yd/s)", BLUE), width="stretch")
with right:
    st.subheader("Acceleration")
    st.altair_chart(line_chart("a", "Acceleration (yd/s²)", ORANGE), width="stretch")

# ---- Leaderboard ----
st.subheader(f"Top speed leaderboard: {pretty(drill)}")
st.caption("Each player's fastest moment in this drill (best attempt), for the players in the sidebar filters. The selected player is orange.")
board = (in_drill.groupby(["nfl_id", "label", "position_group"], as_index=False)["top_speed"].max()
         .sort_values("top_speed", ascending=False).reset_index(drop=True))
board["rank"] = board.index + 1
board["mph"] = board["top_speed"] * 2.04545
board["who"] = (board["label"] == player).map({True: "Selected player", False: "Others"})
show = board.head(15)
if player not in set(show["label"]):
    show = board[(board.index < 14) | (board["label"] == player)]  # keep the selected player visible

st.altair_chart(
    alt.Chart(show).mark_bar(cornerRadiusEnd=4).encode(
        x=alt.X("top_speed:Q", title="Top speed (yd/s)"),
        y=alt.Y("label:N", sort=alt.EncodingSortField("rank"), title=None),
        color=alt.Color("who:N", scale=alt.Scale(domain=["Others", "Selected player"], range=[BLUE, ORANGE]), legend=None),
        tooltip=[alt.Tooltip("rank:Q", title="Rank"), alt.Tooltip("label:N", title="Player"),
                 alt.Tooltip("top_speed:Q", format=".2f", title="yd/s"), alt.Tooltip("mph:Q", format=".1f", title="mph")],
    ).properties(height=28 * len(show)),
    width="stretch",
)
sel_rank = int(board.loc[board["label"] == player, "rank"].iloc[0])
st.caption(f"{player} ranks #{sel_rank} of {len(board)} in this drill.")

with st.expander("Raw frames"):
    st.dataframe(frames, width="stretch")
