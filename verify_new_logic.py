import sqlite3
import pandas as pd

def verify():
    # Date Driver: Detailed DB on March 24th, 2026
    conn_det = sqlite3.connect('detailed_split.db')
    df_det = pd.read_sql("SELECT [Customer Mobile] FROM Detailed_split_1 WHERE Date='24-03-2026' UNION ALL SELECT [Customer Mobile] FROM Detailed_split_2 WHERE Date='24-03-2026'", conn_det)
    active_mobs = set(df_det['Customer Mobile'].astype(str).str.strip().str.replace('.0', '', regex=False))
    conn_det.close()

    # Monthly DB Filtered by active_mobs
    conn_mon = sqlite3.connect('monthly.db')
    df_mon = pd.read_sql("SELECT [Mobile Number], [Point Given] FROM r_f_monthly", conn_mon)
    df_mon['m'] = df_mon['Mobile Number'].astype(str).str.strip().str.replace('.0', '', regex=False)
    filtered_mon = df_mon[df_mon['m'].isin(active_mobs)]
    
    print(f"Active Mobs in Detailed DB (24-03-2026): {len(active_mobs)}")
    print(f"Matched Mobs in Monthly DB: {filtered_mon['m'].nunique()}")
    print(f"Total Bonus Points for these mobs: {filtered_mon['Point Given'].sum()}")
    conn_mon.close()

if __name__ == '__main__':
    verify()
