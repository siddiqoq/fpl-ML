# Fantasy Premier League Machine Learning Pipeline

## Overview

This project implements an end-to-end machine learning pipeline to predict Fantasy Premier League (FPL) player points using data scraped from the official FPL API. 

The pipeline covers:
- Season-aware data ingestion: past seasons from vaastav/Fantasy-Premier-League, the live season from the FPL API
- Feature engineering with time-series constraints
- Model training and evaluation
- Next gameweek point prediction

Tech Stack:
- Python 3
- PostgreSQL (local)
- pandas, NumPy
- scikit-learn
- psycopg2
- joblib
- dotenv

## Data Source

The official FPL API only serves per-gameweek stats for the current season, so past seasons (2016/17 onwards) are loaded from the open [vaastav/Fantasy-Premier-League](https://github.com/vaastav/Fantasy-Premier-League) dataset, and the live season from the FPL API. Both are stored in the same local PostgreSQL schema, keyed by season, with one row per player per fixture (`backend/src/db/schema.sql`).

## Model
- RandomForestRegressor
- Trained using historical gameweek data
- Time-based train/test split
- Training data consists of all completed gameweeks prior to the most recent ones, while the test set is dynamically determined based on the latest available gameweek in the current season.
- Evaluation metric: Mean Absolute Error (MAE)


## Future features
- Add relevant features to current model (fixture difficulty, player form, team form, team playstyle)
- Predict team win/loss probability
- Improved performance (lower runtime)
- Web-based dashboard
- Comparison between model predictions and actual outcome for past weeks

## How to Run
### 1. Prerequisites
- Python 3.10+
- PostgreSQL database
- pip or poetry

### 2. Clone Repo
```
git clone https://github.com/siddiqoq/fpl-ML.git
cd fpl-ML
```

### 3. Create and activate Virtual Environment
```
python -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows

```

### 4. Install dependencies
```
pip install -r backend/requirements.txt
```

### 5. Set up a local PostgreSQL database
```
brew install postgresql@18
brew services start postgresql@18
createdb fpl
```

Then copy `backend/.env.example` to `backend/.env` and fill in your user (usually your macOS username).

### 6. Load the data (from `backend/`)

```
cd backend
python src/db/init_db.py         # create the tables (add --reset to drop and recreate them)
python src/db/load_history.py    # one-off: past seasons 2016/17-2025/26 from vaastav (~1 min)
python run_pipeline.py           # live season, ep_next snapshot, features, model, predictions
```

`run_pipeline.py` only fetches gameweeks FPL has marked finished and data-checked, so re-run it after each gameweek. Run `python src/db/snapshot_ep.py` before every deadline to record FPL's own expected points (they can't be recovered afterwards).
