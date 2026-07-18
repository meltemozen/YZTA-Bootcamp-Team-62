"""Build the generic hourly consumption-shape artifact from advanced ML models.

This script trains a CatBoostRegressor on our calibrated dataset, generates
synthetic predictions for a full year, and distills the model's learned 
behavior (24-hour shape, weekend multiplier) into a lightweight JSON format 
expected by the backend.

    python data/scripts/train_consumption_model.py
"""

import os
import json
import pandas as pd
import numpy as np
from catboost import CatBoostRegressor
from datetime import datetime

DATA_PATH = "data/tuketim_verisi.csv"
OUT_PATH = "backend/app/models/consumption_v1.json"

DEFAULT_BUSINESS = [
    0.010, 0.009, 0.009, 0.009, 0.010, 0.012,
    0.023, 0.046, 0.078, 0.088, 0.090, 0.089,
    0.086, 0.085, 0.087, 0.086, 0.079, 0.065,
    0.046, 0.032, 0.021, 0.014, 0.013, 0.012,
]

def prepare_features(df):
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['hour'] = df['datetime'].dt.hour
    df['day_of_week'] = df['datetime'].dt.dayofweek
    df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)
    df['month'] = df['datetime'].dt.month
    return df

def train_and_extract_shape():
    print("Veri yükleniyor...")
    df = pd.read_csv(DATA_PATH)
    df = prepare_features(df)
    
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

    # Model Eğitimi (CatBoost)
    print("CatBoost Modeli Eğitiliyor...")
    features = ['hour', 'day_of_week', 'is_weekend', 'month']
    X = df[features]
    y = df['consumption']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = CatBoostRegressor(
        iterations=500,
        learning_rate=0.05,
        depth=6,
        verbose=False,
        allow_writing_files=False
    )
    
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    mse = mean_squared_error(y_test, preds)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_test, preds)
    r2 = r2_score(y_test, preds)
    
    print("\n--- CatBoost Model Başarısı ---")
    print(f"MSE  (Ortalama Kare Hata)      : {mse:.4f}")
    print(f"RMSE (Kök Ortalama Kare Hata)  : {rmse:.4f}")
    print(f"MAE  (Ortalama Mutlak Hata)    : {mae:.4f}")
    print(f"R2   (Açıklanabilirlik Skoru)  : {r2:.4f}\n")
    
    model.fit(X, y)
    
    print("Modelden Türkiye tüketim karakteristiği çekiliyor (Distillation)...")
    date_rng = pd.date_range(start='2024-01-01', end='2024-12-31 23:00:00', freq='1h')
    df_synthetic = pd.DataFrame({'datetime': date_rng})
    df_synthetic = prepare_features(df_synthetic)
    
    df_synthetic['predicted_consumption'] = model.predict(df_synthetic[features])
    
    weekdays = df_synthetic[df_synthetic['is_weekend'] == 0]
    hourly_avg = weekdays.groupby('hour')['predicted_consumption'].mean()
    home_shape = (hourly_avg / hourly_avg.sum()).tolist()
    home_shape = [round(x, 5) for x in home_shape]
    
    avg_weekday_consumption = weekdays['predicted_consumption'].mean()
    weekends = df_synthetic[df_synthetic['is_weekend'] == 1]
    avg_weekend_consumption = weekends['predicted_consumption'].mean()
    weekend_multiplier = round(avg_weekend_consumption / avg_weekday_consumption, 3)
    
    model_data = {
        "model_version": "v2-catboost-calibrated",
        "home_shape": home_shape,
        "business_shape": DEFAULT_BUSINESS,
        "seasonality": {
            "home_amplitude": 0.10,
            "business_amplitude": 0.15
        },
        "weekend": {
            "home_multiplier": weekend_multiplier,
            "business_multiplier": 1.0
        }
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(model_data, f, indent=4)
        
    print(f"Başarılı! Yeni CatBoost AI profili '{OUT_PATH}' dosyasına yazıldı.")
    print(f"- Hafta sonu çarpanı: {weekend_multiplier}")

if __name__ == "__main__":
    train_and_extract_shape()
