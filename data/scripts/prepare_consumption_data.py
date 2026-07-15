import os
import pandas as pd
import numpy as np

KAGGLE_PATH = "data/kaggle_london.csv"
EPIAS_PATH = "data/epias-tuketim-01012024-31122024.csv"
OUT_PATH = "data/tuketim_verisi.csv"

def load_kaggle_base_profile():
    print("Kaggle (Londra) verisi okunuyor...")
    df = pd.read_csv(KAGGLE_PATH, usecols=['tstp', 'energy(kWh/hh)'])
    
    df.rename(columns={'tstp': 'datetime', 'energy(kWh/hh)': 'consumption'}, inplace=True)
    
    print("Kaggle verisi temizleniyor...")
    df['consumption'] = pd.to_numeric(df['consumption'], errors='coerce')
    df.dropna(inplace=True)
    
    df['datetime'] = pd.to_datetime(df['datetime'])
    
    print("Ortalama İngiliz ev profili oluşturuluyor...")
    # Aggregate thousands of houses into a single average household profile
    df_avg_house = df.groupby('datetime')['consumption'].mean().reset_index()
    
    # Resample half-hourly data to 1-hour frequency
    df_avg_house.set_index('datetime', inplace=True)
    df_hourly = df_avg_house.resample('1h').sum()
    
    df_hourly['consumption'] = df_hourly['consumption'].ffill()
    
    return df_hourly

def get_epias_calibration_ratios():
    print("EPİAŞ (Türkiye) verisi okunuyor...")
    df_epias = pd.read_csv(EPIAS_PATH, sep=';', parse_dates=False)
    
    # Parse Turkish locale numbers (e.g., '28.929,45' -> 28929.45)
    df_epias['Tüketim Miktarı(MWh)'] = (
        df_epias['Tüketim Miktarı(MWh)']
        .str.replace('.', '', regex=False)  
        .str.replace(',', '.', regex=False) 
    )
    df_epias['consumption'] = pd.to_numeric(df_epias['Tüketim Miktarı(MWh)'], errors='coerce')
    
    df_epias['hour'] = df_epias['Saat'].str.split(':').str[0].astype(int)
    
    # Extract the 24-hour macro consumption shape of Turkey
    epias_hourly_avg = df_epias.groupby('hour')['consumption'].mean()
    epias_shape_normalized = epias_hourly_avg / epias_hourly_avg.mean()
    
    return epias_shape_normalized

def process_and_calibrate():
    df_base = load_kaggle_base_profile()
    
    epias_shape = get_epias_calibration_ratios()
    
    df_base['hour'] = df_base.index.hour
    kaggle_hourly_avg = df_base.groupby('hour')['consumption'].mean()
    kaggle_shape_normalized = kaggle_hourly_avg / kaggle_hourly_avg.mean()
    
    print("Kaggle profili, EPİAŞ profili kullanılarak Türkiye'ye kalibre ediliyor...")
    
    # Calculate the ratio difference between UK and TR energy shapes per hour
    calibration_multipliers = epias_shape / kaggle_shape_normalized
    
    def apply_calibration(row):
        h = int(row['hour'])
        return row['consumption'] * calibration_multipliers.loc[h]
        
    df_base['calibrated_consumption'] = df_base.apply(apply_calibration, axis=1)
    
    df_final = df_base[['calibrated_consumption']].rename(columns={'calibrated_consumption': 'consumption'})
    
    df_final = df_final.dropna()
    
    df_final.to_csv(OUT_PATH)
    print(f"\nİşlem Başarılı! {len(df_final)} saatlik kalibre edilmiş Türkiye-Ev verisi '{OUT_PATH}' olarak oluşturuldu.")

if __name__ == "__main__":
    process_and_calibrate()
