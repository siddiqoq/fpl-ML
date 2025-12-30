# Fantasy Premier League Machine Learning Pipeline

## Overview

This project implements an end-to-end machine learning pipeline to predict Fantasy Premier League (FPL) player points using data scraped from the official FPL API. 

The pipeline covers:
- Automated data ingestion (static + dynamic match data)
- Feature engineering with time-series constraints
- Model training and evaluation
- Next gameweek point prediction

Tech Stack:
- Python 3
- PostgreSQL (Supabase)
- pandas, NumPy
- scikit-learn
- psycopg2
- joblib
- dotenv

## Data Source

All data is sourced directly from the official FPL API. Important to note that the official FPL API only gives matchday specific stats for the current running season. For previous seasons (up to 2016/17) only season totals are provided. As a result some features are dependant on whether the season has started or not (points last gameweeks).

The project uses PostgreSQL for data storage. Supabase is recommended but any PostgreSQL-compatible database can be used.


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

### 4. Install dependancies
```
pip install -r requirements.txt
```

### 5. Create .env file in project root

```
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=fpl
DB_SSLMODE=disable #enable if using Supabase
```

### 6. Run run_pipeline.py

```
python run_pieline.py
```
