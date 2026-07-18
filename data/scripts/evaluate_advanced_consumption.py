"""
Advanced Consumption Models Comparison Script
This script compares CatBoost, LightGBM, and Prophet models for energy consumption forecasting.

Usage:
    python data/scripts/evaluate_advanced_consumption.py --csv path_to_your_data.csv --target your_target_column
"""

import argparse
import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error

import lightgbm as lgb
from catboost import CatBoostRegressor
from prophet import Prophet

def prepare_features(df):
    """
    Creates basic time series features from a datetime column.
    Modify this function based on the extra data you have (e.g. holidays, temperature)
    """
    # Ensure datetime format
    df['datetime'] = pd.to_datetime(df['datetime'])
    
    # Extract time-based features
    df['hour'] = df['datetime'].dt.hour
    df['day_of_week'] = df['datetime'].dt.dayofweek
    df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)
    df['month'] = df['datetime'].dt.month
    
    return df

def train_lightgbm(X_train, y_train, X_test, y_test):
    print("Training LightGBM...")
    model = lgb.LGBMRegressor(
        n_estimators=100, 
        learning_rate=0.1, 
        random_state=42, 
        verbose=-1
    )
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    return model, preds

def train_catboost(X_train, y_train, X_test, y_test, cat_features):
    print("Training CatBoost...")
    model = CatBoostRegressor(
        iterations=200, 
        learning_rate=0.1, 
        depth=6, 
        random_state=42, 
        verbose=0
    )
    # CatBoost natively handles categorical variables without One-Hot Encoding
    model.fit(X_train, y_train, cat_features=cat_features)
    preds = model.predict(X_test)
    return model, preds

def train_prophet(df_train, df_test):
    print("Training Prophet...")
    # Prophet strictly requires columns to be named 'ds' (datestamp) and 'y' (target)
    prophet_train = df_train[['datetime', 'consumption']].rename(columns={'datetime': 'ds', 'consumption': 'y'})
    
    model = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=True)
    model.fit(prophet_train)
    
    prophet_test = df_test[['datetime']].rename(columns={'datetime': 'ds'})
    forecast = model.predict(prophet_test)
    preds = forecast['yhat'].values
    return model, preds

def evaluate_metrics(y_true, y_pred, model_name):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    
    print(f"--- {model_name} ---")
    print(f"MAE:  {mae:.4f} ")
    print(f"RMSE: {rmse:.4f} \n")
    return mae, rmse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Path to the consumption data CSV")
    parser.add_argument("--target", default="consumption", help="Name of the target column (e.g., consumption, kwh, energy_kwh)")
    parser.add_argument("--datetime-col", default="datetime", help="Name of the datetime column in your CSV")
    args = parser.parse_args()

    # 1. Load Data
    print(f"Loading data from {args.csv}...")
    try:
        df = pd.read_csv(args.csv)
    except FileNotFoundError:
        print(f"Error: Could not find file {args.csv}")
        return

    # Standardize datetime and target column names for the script
    if args.datetime_col != "datetime":
        if args.datetime_col in df.columns:
            df = df.rename(columns={args.datetime_col: "datetime"})
        else:
            print(f"Error: Column {args.datetime_col} not found in CSV. Available columns: {df.columns.tolist()}")
            return
            
    if args.target != "consumption":
        if args.target in df.columns:
            df = df.rename(columns={args.target: "consumption"})
        else:
            print(f"Error: Target column {args.target} not found in CSV. Available columns: {df.columns.tolist()}")
            return
    
    # Drop NaNs in target
    df = df.dropna(subset=['consumption'])
    
    # 2. Feature Engineering
    print("Preparing time-based features...")
    df = prepare_features(df)
    
    # Sort by time to ensure time-series integrity before splitting
    df = df.sort_values("datetime")
    
    # 3. Train / Test Split (Time Series Split - No shuffling)
    # We use the first 80% of time for training, and the last 20% for testing
    train_size = int(len(df) * 0.8)
    df_train = df.iloc[:train_size].copy()
    df_test = df.iloc[train_size:].copy()
    
    # Define features to be used by tree-based models
    features = ['hour', 'day_of_week', 'is_weekend', 'month']
    
    # CatBoost specific: define which features are categorical
    cat_features = ['hour', 'day_of_week', 'is_weekend', 'month']
    
    X_train = df_train[features]
    y_train = df_train['consumption']
    X_test = df_test[features]
    y_test = df_test['consumption']
    
    print(f"Training on {len(df_train)} rows, Testing on {len(df_test)} rows.\n")
    
    # 4. Model Training & Evaluation
    
    # A) LightGBM
    lgb_model, lgb_preds = train_lightgbm(X_train, y_train, X_test, y_test)
    evaluate_metrics(y_test, lgb_preds, "LightGBM")
    
    # B) CatBoost
    cat_model, cat_preds = train_catboost(X_train, y_train, X_test, y_test, cat_features=cat_features)
    evaluate_metrics(y_test, cat_preds, "CatBoost")
    
    # C) Prophet
    prophet_model, prophet_preds = train_prophet(df_train, df_test)
    evaluate_metrics(y_test, prophet_preds, "Prophet")
    
    print("Comparison complete!")

if __name__ == "__main__":
    main()
