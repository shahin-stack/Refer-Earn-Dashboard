import sqlite3
import pandas as pd

def check_zeros():
    conn_mon = sqlite3.connect('monthly.db')
    df_mon = pd.read_sql("SELECT [Point Given] FROM r_f_monthly", conn_mon)
    conn_mon.close()

    p = pd.to_numeric(df_mon['Point Given'], errors='coerce').fillna(0)
    zero_points = p[p == 0]
    print(f"Total Rows in Monthly DB: {len(df_mon)}")
    print(f"Rows where Point Given is 0: {len(zero_points)}")
    
    # Target gap is 16. If this is 16, we found it!
    # Let's hope.

if __name__ == '__main__':
    check_zeros()
