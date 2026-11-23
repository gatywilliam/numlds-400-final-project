# Visualization website

A Streamlit website for exploring the Big Data Bowl data. Streamlit turns Python scripts into
web pages, so it runs in the browser like a normal site.

## Run

From the repo root, with the venv active and the database built (`python src/load_data.py`):

```bash
pip install -r requirements.txt
streamlit run visualization/app.py
```

It opens at http://localhost:8501.

## Pages

| File | Page |
|---|---|
| `app.py` | Home: project summary, headline numbers, list of tables |
| `pages/1_Drill_Viewer.py` | A player's path in any combine drill (Will's field plot), speed and acceleration over time, top-speed leaderboard |
| `pages/2_Combine_Results.py` | Players per position, 40-yard dash by position, weight vs 40 time, athleticism by draft round, drill distributions |
| `pages/3_Combine_vs_Career.py` | Do good combine results go with more NFL games/snaps? Quartile bars, scatter with Pro Bowlers, drill x position heatmap |
| `pages/4_Route_Separation.py` | WR/TE: separation by route, catch rate by separation, combine drill vs separation |
| `pages/5_Player_Profile.py` | One player's combine percentiles vs their position group, career and NFL stats, compare two players |
| `pages/6_Data_Explorer.py` | Browse any table and its summary stats |

The sidebar filters (position group, draft year) apply to every page and stay set when you switch pages.

Shared code:

- `data.py`: all database queries (cached so pages load fast), the sidebar filters, chart colors, and the list of combine drills.
- `field.py`: NFL field drawing and drill path plot, adapted from `src/local_eda_wgaty.ipynb`.

## Adding a page

Create `pages/4_My_Page.py`. It shows up in the sidebar automatically. Start it with:

```python
import streamlit as st
from data import query, require_db, sidebar_filters

st.set_page_config(page_title="My Page", layout="wide")
require_db()
positions, years = sidebar_filters()  # call this on every page so the filters carry over
st.title("My Page")
df = query("SELECT * FROM players")
```
