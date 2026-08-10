import sqlite3
import pandas as pd
import json
import numpy as np

def generate_daily_stats():
    # 1. Monthly DB stats (Overall static figures)
    conn_mon = sqlite3.connect('monthly.db')
    df_mon = pd.read_sql("SELECT [Mobile Number], [Point Given] FROM r_f_monthly", conn_mon)
    conn_mon.close()
    
    total_cust_master = int(df_mon['Mobile Number'].nunique())
    total_points_master = float(pd.to_numeric(df_mon['Point Given'], errors='coerce').fillna(0).sum())
    
    # 2. Detailed Split stats
    conn_det = sqlite3.connect('detailed_split.db')
    df_det = pd.read_sql("SELECT [Date], [Customer Mobile], [Total Value], [POINT REDUMPTION (DEDUCTION)] FROM Detailed_split_1 UNION ALL SELECT [Date], [Customer Mobile], [Total Value], [POINT REDUMPTION (DEDUCTION)] FROM Detailed_split_2", conn_det)
    conn_det.close()
    
    df_det['POINT REDUMPTION (DEDUCTION)'] = pd.to_numeric(df_det['POINT REDUMPTION (DEDUCTION)'], errors='coerce').fillna(0).abs()
    df_det['Total Value'] = pd.to_numeric(df_det['Total Value'], errors='coerce').fillna(0)
    
    def clean_m(s):
        s = str(s).strip()
        if s.endswith('.0'): s = s[:-2]
        return s
    
    df_det['m'] = df_det['Customer Mobile'].apply(clean_m)
    df_det['Date'] = pd.to_datetime(df_det['Date'], format='%d-%m-%Y', errors='coerce').dt.strftime('%Y-%m-%d')
    df_det = df_det.dropna(subset=['Date'])
    
    daily_stats = {}
    unique_dates = sorted(df_det['Date'].unique())
    
    for date in unique_dates:
        df_day = df_det[df_det['Date'] == date]
        redeemed_mobs = df_day[df_day['POINT REDUMPTION (DEDUCTION)'] > 0]['m'].unique()
        
        daily_stats[date] = {
            "purchase_count": int(df_day['m'].nunique()),
            "redeemed_count": int(len(redeemed_mobs)),
            "point_redeemed_value": float(df_day['POINT REDUMPTION (DEDUCTION)'].sum()),
            "redeemed_purchase_value": float(df_day[df_day['m'].isin(redeemed_mobs)]['Total Value'].sum())
        }
    
    final_output = {
        "master_stats": {
            "total_customer_count": total_cust_master,
            "total_bonus_point_given": total_points_master
        },
        "daily_data": daily_stats
    }
    
    def default_serialize(obj):
        if isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

    with open('dashboard_daily_stats.json', 'w') as f:
        json.dump(final_output, f, indent=2, default=default_serialize)
    
    print("Dashboard daily stats (Static Master List Version) reverted successfully.")

if __name__ == '__main__':
    generate_daily_stats()
