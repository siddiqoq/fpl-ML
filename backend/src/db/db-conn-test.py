from conn import DBNAME, HOST, PORT, USER, get_conn

# Quick check that backend/.env points at a reachable Postgres
try:
    connection = get_conn()
    cursor = connection.cursor()
    cursor.execute("SELECT NOW();")
    print(f"Connected to {HOST}:{PORT}/{DBNAME} as {USER}. Server time:", cursor.fetchone()[0])
    cursor.close()
    connection.close()
except Exception as e:
    print(f"Failed to connect: {e}")
