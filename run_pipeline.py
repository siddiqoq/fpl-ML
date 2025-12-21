import subprocess
import sys

scripts = [
    "src/db/load_static.py",
    "src/db/load_dynamic.py",
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