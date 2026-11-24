import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# scripts in src/ import each other by module name (from features import ...)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


@pytest.fixture
def raw():
    # small gameweek-level dataset in the shape fetch_data.py writes: 2 seasons x 8 GWs x 6 players
    rng = np.random.default_rng(0)
    rows = []
    for season in ["2021/22", "2022/23"]:
        for player_id in range(1, 7):
            for gw in range(1, 9):
                rows.append({"season": season, "player_id": player_id, "code": 100 + player_id,
                             "gameweek": gw, "element_type": player_id % 4 + 1,
                             "minutes": int(rng.choice([0, 90])), "total_points": int(rng.integers(0, 12)),
                             "xp": float(rng.uniform(0, 6))})
    # shuffled, so nothing relies on the input already being in order
    return pd.DataFrame(rows).sample(frac=1, random_state=0).reset_index(drop=True)
