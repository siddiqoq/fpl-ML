import os.path
from path import PROCESSED_DATA_DIR
import pandas as pd
from fontTools.subset import subset

DATASET_PATH = os.path.join(PROCESSED_DATA_DIR, "ml_dataset.csv")
df = pd.read_csv(DATASET_PATH)


df = df.sort_values(["player_id", "gameweek"])

# PREVIOUS GW POINTS
df["points_last_gw"] = df.groupby("player_id")["total_points"].shift(1)
# .groupby seperates each player through player_id
# each player's total points shift by 1 downwards
# points for gw2 -> gw3 row

# PAST 3 GW POINTS
df["points_last_3_gws"] = df.groupby("player_id")['total_points'].rolling(3).mean().shift(1).reset_index(0, drop=True)
#.reset_index(0) drops player_id index so df's original indexes are kept


df = df.dropna(subset=["points_last_gw","points_last_3_gws"])

OUTPUT_PATH = os.path.join(PROCESSED_DATA_DIR, "ml_features_dataset.csv")
df.to_csv(OUTPUT_PATH, index =False)
print(df.shape)