"""Shared data loading and sidebar filters for the Streamlit app. Everything is read from data/bdb2027.sqlite."""

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "bdb2027.sqlite"

# Chart colors (validated categorical palette: blue, orange, aqua)
BLUE = "#2a78d6"
ORANGE = "#eb6834"
RED = "#e34948"
GRAY = "#f0efec"

POSITION_GROUPS = ["DB", "DL", "OL", "TE", "WR"]

# Combine measurements: column -> (label, lower_is_better)
DRILLS = {
    "forty": ("40-yard dash (s)", True),
    "ten_yd_split": ("10-yard split (s)", True),
    "three_cone": ("3-cone drill (s)", True),
    "short_shuttle": ("Short shuttle (s)", True),
    "vertical": ("Vertical jump (in)", False),
    "broad_jump": ("Broad jump (in)", False),
    "bench_reps": ("Bench press (reps)", False),
    "ngs_athleticism_score": ("NGS athleticism score", False),
}


def require_db() -> None:
    """Stop the page with a helpful message if the database hasn't been built yet."""
    if not DB_PATH.exists():
        st.error(f"Database not found at `{DB_PATH}`. Run `python src/load_data.py` from the repo root first.")
        st.stop()


def query(sql: str, params: tuple = ()) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as con:
        return pd.read_sql(sql, con, params=params)


# ---------- Sidebar filters shared by every page ----------

def sidebar_filters() -> tuple[list[str], list[int]]:
    """Position group and draft year filters. Their values carry over when you switch pages."""
    years = [2023, 2024, 2025]
    for key, default in [("positions", POSITION_GROUPS), ("years", years)]:
        # Re-assigning keeps the widget value when moving between pages
        st.session_state[key] = st.session_state.get(key, default)

    st.sidebar.header("Filters")
    st.sidebar.multiselect("Position group", POSITION_GROUPS, key="positions")
    st.sidebar.multiselect("Draft year", years, key="years")
    st.sidebar.caption("DB = defensive backs, DL = defensive line, OL = offensive line, TE = tight ends, WR = wide receivers")
    return st.session_state.positions, st.session_state.years


def apply_filters(df: pd.DataFrame, positions: list[str], years: list[int]) -> pd.DataFrame:
    return df[df["position_group"].isin(positions) & df["draft_year"].isin(years)]


# ---------- Cached queries ----------

@st.cache_data
def list_tables() -> pd.DataFrame:
    names = query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")["name"]
    rows = [query(f'SELECT COUNT(*) AS n FROM "{t}"')["n"][0] for t in names]
    return pd.DataFrame({"table": names, "rows": rows})


@st.cache_data
def load_table(name: str, limit: int | None = None) -> pd.DataFrame:
    sql = f'SELECT * FROM "{name}"' + (f" LIMIT {int(limit)}" if limit else "")
    return query(sql)


@st.cache_data
def players() -> pd.DataFrame:
    return query("SELECT * FROM players")


@st.cache_data
def combine_results() -> pd.DataFrame:
    """One row per player: combine results, player info and career outcomes."""
    df = query(
        """
        SELECT c.*, c.combine_position AS position_group,
               p.display_name, p.nfl_position, p.college_name, p.draft_round, p.draft_overall_pick,
               s.career_games_active, s.career_games_started,
               s.career_offensive_snaps + s.career_defensive_snaps AS career_snaps,
               s.pro_bowl_original_ballot, s.ap_all_pro_1st_team, s.ap_all_pro_2nd_team
        FROM combine_results c
        LEFT JOIN players p ON p.nfl_id = c.nfl_id
        LEFT JOIN player_career_successes s ON s.nfl_id = c.nfl_id
        """
    )
    df["honors"] = (df[["pro_bowl_original_ballot", "ap_all_pro_1st_team", "ap_all_pro_2nd_team"]].fillna(0).sum(axis=1) > 0)
    df["honors"] = df["honors"].map({True: "Pro Bowl / All-Pro", False: "Other players"})
    df["drafted"] = df["draft_round"].notna()
    return df


def rank_corr(a: pd.Series, b: pd.Series) -> float:
    """Spearman rank correlation (Pearson correlation of the ranks), without needing scipy."""
    return a.rank().corr(b.rank())


def with_percentiles(df: pd.DataFrame) -> pd.DataFrame:
    """Add <drill>_pct columns: 0-100 percentile within the player's position group, 100 = best."""
    df = df.copy()
    for col, (_, lower_better) in DRILLS.items():
        pct = df.groupby("position_group")[col].rank(pct=True, ascending=not lower_better)
        df[f"{col}_pct"] = (pct * 100).round(0)
    return df


@st.cache_data
def drill_attempts() -> pd.DataFrame:
    """One row per (drill, player, attempt) in the combine tracking data, with top speed."""
    return query(
        """
        SELECT t.drill_name, t.nfl_id, t.event_id, t.attempt, COUNT(*) AS frames, MAX(t.s) AS top_speed,
               p.display_name, p.nfl_position, c.combine_position AS position_group, c.draft_year
        FROM combine_tracking t
        LEFT JOIN players p ON p.nfl_id = t.nfl_id
        LEFT JOIN combine_results c ON c.nfl_id = t.nfl_id
        WHERE t.entity_type = 'PLAYER'
        GROUP BY t.drill_name, t.nfl_id, t.event_id, t.attempt
        """
    )


@st.cache_data
def drill_frames(event_id: str, nfl_id: int, attempt: int) -> pd.DataFrame:
    """All 10 Hz tracking frames for one drill attempt."""
    df = query(
        """
        SELECT time, x, y, s, a, dis, dir FROM combine_tracking
        WHERE event_id = ? AND nfl_id = ? AND attempt = ? AND entity_type = 'PLAYER'
        """,
        (event_id, int(nfl_id), int(attempt)),
    )
    df["time"] = pd.to_datetime(df["time"], format="mixed")
    return df.sort_values("time").reset_index(drop=True)


@st.cache_data
def targets() -> pd.DataFrame:
    """Every play where a receiver was targeted, with how open they were when the ball was thrown."""
    return query(
        """
        SELECT nfl_id, route_ran, separation_at_pass_forward AS separation, pass_result,
               COALESCE(rec_yards, 0) AS rec_yards
        FROM player_play
        WHERE target = 1 AND separation_at_pass_forward IS NOT NULL
        """
    )


@st.cache_data
def nfl_production() -> pd.DataFrame:
    """Per-player totals from the NFL play-by-play data."""
    return query(
        """
        SELECT nfl_id,
               COUNT(*) AS plays,
               SUM(target) AS targets,
               SUM(CASE WHEN target = 1 AND pass_result = 'C' THEN 1 ELSE 0 END) AS receptions,
               SUM(COALESCE(rec_yards, 0)) AS receiving_yards,
               ROUND(AVG(CASE WHEN target = 1 THEN separation_at_pass_forward END), 2) AS avg_separation_yd,
               SUM(COALESCE(sack, 0)) AS sacks,
               SUM(COALESCE(tackle, 0)) AS tackles,
               SUM(COALESCE(pressure_allowed, 0)) AS pressures_allowed,
               SUM(COALESCE(sack_allowed, 0)) AS sacks_allowed
        FROM player_play
        GROUP BY nfl_id
        """
    )
