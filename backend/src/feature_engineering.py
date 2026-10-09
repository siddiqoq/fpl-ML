import os.path
from path import PROCESSED_DATA_DIR
from features import add_training_features
import pandas as pd

DATASET_PATH = os.path.join(PROCESSED_DATA_DIR, "ml_dataset.csv")
df = pd.read_csv(DATASET_PATH)

# points_last_gw: player's points in the previous GW
# points_last_3_gws: mean of the player's previous 3 GWs
# both are grouped by season + player so values never bleed between players or seasons
df = add_training_features(df)

OUTPUT_PATH = os.path.join(PROCESSED_DATA_DIR, "ml_features_dataset.csv")
df.to_csv(OUTPUT_PATH, index =False)
print(df.shape)
