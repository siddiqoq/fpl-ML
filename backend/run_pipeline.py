import subprocess
import sys

scripts = [
    "src/db/init_db.py",       # creates tables if missing (load_history.py is a separate one-off)
    "src/db/load_current.py",
    "src/db/snapshot_ep.py",
    "src/fetch_data.py",
    "src/feature_engineering.py",
    "src/model.py",
    "src/predict_next_gw.py"]
for script in scripts:
    print(f"Running {script}")
    result = subprocess.run([sys.executable,script])

    if result.returncode != 0:
        print(f"Failed to run {script}")
        sys.exit(1)

print("All scripts ran successfully")