"""One player's combine results compared with their position group, plus their NFL career so far."""

import altair as alt
import pandas as pd
import streamlit as st

from data import BLUE, DRILLS, ORANGE, apply_filters, combine_results, nfl_production, require_db, sidebar_filters, with_percentiles

st.set_page_config(page_title="Player Profile", page_icon="🏈", layout="wide")
require_db()
positions, years = sidebar_filters()

st.title("Player Profile")

# Percentiles are computed against everyone in the position group, not just the filtered players
everyone = with_percentiles(combine_results())
listed = apply_filters(everyone, positions, years).sort_values("display_name")
if listed.empty:
    st.info("No players match the sidebar filters.")
    st.stop()

label = lambda r: f"{r.display_name} ({r.position_group}, {r.college_name}, {r.draft_year})"
options = {label(r): r.nfl_id for r in listed.itertuples()}

c1, c2 = st.columns(2)
p1 = c1.selectbox("Player", list(options))
p2 = c2.selectbox("Compare with (optional)", ["None"] + [o for o in options if o != p1])

chosen = [options[p1]] + ([options[p2]] if p2 != "None" else [])
sel = everyone[everyone["nfl_id"].isin(chosen)].set_index("nfl_id").loc[chosen].reset_index()
sel["player"] = sel["display_name"]
colors = [BLUE, ORANGE][: len(sel)]

# ---- Header cards ----
cols = st.columns(len(sel))
for col, r in zip(cols, sel.itertuples()):
    with col:
        st.subheader(r.display_name)
        drafted = f"Round {int(r.draft_round)}, pick {int(r.draft_overall_pick)} overall" if pd.notna(r.draft_round) else "Undrafted"
        st.markdown(f"**{r.nfl_position}** · {r.college_name} · {r.draft_year} draft · {drafted}")
        if r.honors == "Pro Bowl / All-Pro":
            st.markdown("⭐ Pro Bowl / All-Pro")
        m1, m2, m3 = st.columns(3)
        m1.metric("Games played", f"{r.career_games_active:.0f}" if pd.notna(r.career_games_active) else "-")
        m2.metric("Games started", f"{r.career_games_started:.0f}" if pd.notna(r.career_games_started) else "-")
        m3.metric("Snaps", f"{r.career_snaps:,.0f}" if pd.notna(r.career_snaps) else "-")

# ---- Combine percentiles ----
st.subheader("Combine results vs their position group")
st.caption("Percentile within the position group: 100 = best in the group, 50 = average. Hover a bar to see the actual result.")
long = pd.DataFrame(
    [{"player": row["player"], "drill": label_, "percentile": row[f"{c}_pct"], "result": row[c]}
     for _, row in sel.iterrows() for c, (label_, _) in DRILLS.items()]
).dropna(subset=["percentile"])

if long.empty:
    st.info("No combine measurements recorded for this player.")
else:
    order = [v[0] for v in DRILLS.values() if v[0] in set(long["drill"])]
    bars = alt.Chart(long).mark_bar(cornerRadiusEnd=4).encode(
        x=alt.X("percentile:Q", title="Percentile within position group", scale=alt.Scale(domain=[0, 100])),
        y=alt.Y("drill:N", sort=order, title=None),
        yOffset=alt.YOffset("player:N", sort=list(sel["player"])),
        color=alt.Color("player:N", sort=list(sel["player"]), scale=alt.Scale(range=colors), title=None,
                        legend=alt.Legend(orient="top") if len(sel) > 1 else None),
        tooltip=["player", "drill", alt.Tooltip("result:Q", title="Result"), alt.Tooltip("percentile:Q", title="Percentile")],
    )
    middle = alt.Chart(pd.DataFrame({"x": [50]})).mark_rule(color="#52514e", strokeDash=[4, 4]).encode(x="x:Q")
    st.altair_chart((bars + middle).properties(height=36 * len(order) * len(sel) + 40), width="stretch")

# ---- NFL production ----
st.subheader("NFL production (2023-2025 play-by-play)")
prod = nfl_production().set_index("nfl_id")
stats = {
    "plays": "Plays",
    "targets": "Targets",
    "receptions": "Receptions",
    "receiving_yards": "Receiving yards",
    "avg_separation_yd": "Avg separation when targeted (yd)",
    "tackles": "Tackles",
    "sacks": "Sacks",
    "pressures_allowed": "Pressures allowed",
    "sacks_allowed": "Sacks allowed",
}
table = pd.DataFrame({r.display_name: prod.reindex([r.nfl_id])[list(stats)].iloc[0] for r in sel.itertuples()})
table.index = [stats[i] for i in table.index]
table = table[(table.fillna(0) != 0).any(axis=1)]  # hide stats that don't apply to these players
if table.empty:
    st.info("No NFL plays recorded for this player in the data.")
else:
    st.dataframe(table, width="stretch")
