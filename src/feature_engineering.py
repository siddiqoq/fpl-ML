import pandas as pd
from fontTools.subset import subset

df = pd.read_csv("data/processed/ml_dataset.csv")


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
df.to_csv("data/processed/ml_features_dataset.csv", index =False)
print(df.shape)