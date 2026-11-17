"""
Download the NFL Big Data Bowl 2027 data from Kaggle and load it into SQLite.
"""

import sqlite3
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv()  # must run before importing kaggle, which authenticates on import
from kaggle.api.kaggle_api_extended import KaggleApi  # noqa: E402

COMPETITION = "nfl-big-data-bowl-2027"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "bdb2027.sqlite"

# Download, unzip, and load into a temporary folder that is deleted afterward,
# so only the SQLite database is left in data/
DATA_DIR.mkdir(exist_ok=True)
api = KaggleApi()
api.authenticate()

with tempfile.TemporaryDirectory() as tmp:
    api.competition_download_files(COMPETITION, path=tmp, quiet=False)
    for zip_path in Path(tmp).glob("*.zip"):
        zipfile.ZipFile(zip_path).extractall(tmp)

    # Load each CSV into its own table, named after the file
    con = sqlite3.connect(DB_PATH)
    for csv in Path(tmp).rglob("*.csv"):
        print(f"Loading {csv.name}...")
        pd.read_csv(csv).to_sql(csv.stem, con, if_exists="replace", index=False)
    con.close()

print(f"Done. Database saved to {DB_PATH}")
