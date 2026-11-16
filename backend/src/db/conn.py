import os
from pathlib import Path
from urllib.parse import quote_plus

import psycopg2
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Single place for DB settings, read from backend/.env (see .env.example)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

USER = os.getenv("user")
PASSWORD = os.getenv("password") or ""
HOST = os.getenv("host", "localhost")
PORT = os.getenv("port", "5432")
DBNAME = os.getenv("name", "fpl")
SSLMODE = os.getenv("DB_SSLMODE", "disable")


def get_conn():
    # psycopg2 connection, used by the loaders for bulk upserts
    return psycopg2.connect(user=USER, password=PASSWORD, host=HOST, port=PORT,
                            dbname=DBNAME, sslmode=SSLMODE)


def get_engine():
    # SQLAlchemy engine, used with pandas.read_sql
    return create_engine(f"postgresql://{USER}:{quote_plus(PASSWORD)}@{HOST}:{PORT}/{DBNAME}",
                         connect_args={"sslmode": SSLMODE})
