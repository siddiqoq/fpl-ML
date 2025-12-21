import os
from urllib.parse import quote_plus

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from sqlalchemy import create_engine
from path import PROCESSED_DATA_DIR

load_dotenv()
USER = os.getenv("user")
PASSWORD = quote_plus(os.getenv("password"))
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")
engine = create_engine(f'postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}')

players = pd.read_sql("SELECT * FROM players ", engine)
teams = pd.read_sql("SELECT * FROM teams ", engine)
gameweeks = pd.read_sql("SELECT * FROM player_gameweek_stats",engine)




df = gameweeks.merge(players, on="player_id", how="left")
df = df.merge(teams, left_on="team_id", right_on="team_id", how="left")
DATASET_PATH = os.path.join(PROCESSED_DATA_DIR, "ml_dataset.csv")

df.to_csv(DATASET_PATH, index=False)
print("ML dataset created:", df.shape)