import sqlite3
import pandas as pd

def get_monthly_stats():
    conn = sqlite3.connect('monthly.db')
    df = pd.read_sql("SELECT [Mobile Number], [Point Given] FROM r_f_monthly", conn)
    conn.close()
    
    total_customers = df['Mobile Number'].nunique()
    total_points = pd.to_numeric(df['Point Given'], errors='coerce').fillna(0).sum()
    
    print(f"Total Customer Count: {total_customers:,}")
    print(f"Total Bonus Point Given: {total_points:,.2f}")

if __name__ == '__main__':
    get_monthly_stats()
