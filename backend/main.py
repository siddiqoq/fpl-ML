import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os.path
import joblib
import pandas as pd
from src.path import MODELS_DIR, PROCESSED_DATA_DIR


app = FastAPI()

origins = ["http://localhost:5173",
           "localhost:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

memory_db = {}

MODEL_PATH = os.path.join(MODELS_DIR, 'rf_model.pkl')
FEATURE_DS = os.path.join(PROCESSED_DATA_DIR, "ml_features_dataset.csv")

model = joblib.load(MODEL_PATH)
df = pd.read_csv(FEATURE_DS)

@app.get("/")
def top_10(position:str = "ALL"):
    positionDictionary = {
        'GK': 1,
        'DEF' : 2,
        'MID' : 3,
        'ATT' : 4
    }
    lastGW = df["gameweek"].max()
    predictedGW = lastGW + 1

    latest_player_gw = df.groupby("player_id").tail(1).reset_index(drop=True)
    X_next = latest_player_gw[["points_last_gw","points_last_3_gws"]]

    if position != "ALL": # filter by position before running model
        latest_player_gw = latest_player_gw[latest_player_gw["element_type"] == positionDictionary[position]]
    latest_player_gw[f"predicted_points_gw{predictedGW}"] = model.predict(X_next)





    predicted_values = (latest_player_gw[["player_id","web_name","short_name","now_cost",f"predicted_points_gw{predictedGW}"]]
                        .sort_values(f"predicted_points_gw{predictedGW}",ascending=False)).reset_index(drop=True)

    return predicted_values.head(10).to_dict(orient='index')

if __name__ == "__main__":
    uvicorn.run("app.api:app", host="0.0.0.0", port=8000, reload=True)