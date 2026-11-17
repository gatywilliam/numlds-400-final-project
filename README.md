# numlds-400-final-project

Our project for the [NFL Big Data Bowl 2027](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027).

## Setup

### 1. Clone the repo and create a virtual environment

```bash
git clone <repo-url>
cd numlds-400-final-project
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Activate the venv (`source .venv/bin/activate`) every time you open a new terminal. Run `deactivate` to leave it.

**Notebooks:** open a `.ipynb` file, click **Select Kernel** (top right in VS Code), and choose the `.venv` Python. If the notebook can't import packages, it's on the wrong kernel.

### 2. Get Kaggle access

1. Sign in to Kaggle and **accept the competition rules** on the [rules page](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/rules). The download fails with "403 Forbidden" until you do.
2. Go to [kaggle.com/settings/api](https://www.kaggle.com/settings/api) and click **Generate New Token**.
3. Copy the example env file and paste your token into it:

```bash
cp .env.example .env
```

```
KAGGLE_API_TOKEN=your-token-here
```

`.env` is gitignored. Never commit your token.

### 3. Download the data and build the database

From the repo root:

```bash
python src/load_data.py
```

This downloads the competition files from Kaggle, loads each CSV into its own table in `data/bdb2027.sqlite`, and then deletes the downloaded files, so only the database is kept. Each table is named after its CSV file. The `data/` folder is gitignored.

### Using the data

```python
import sqlite3
import pandas as pd

con = sqlite3.connect("data/bdb2027.sqlite")
print(pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", con))  # list tables
df = pd.read_sql("SELECT * FROM <table_name>", con)
```
