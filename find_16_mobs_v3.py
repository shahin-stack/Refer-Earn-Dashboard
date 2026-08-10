import sqlite3
import pandas as pd

def find_16():
    conn_det = sqlite3.connect('detailed_split.db')
    df_det = pd.read_sql("SELECT [Customer Mobile], [POINT REDUMPTION (DEDUCTION)], [Total Value] FROM Detailed_split_1 UNION ALL SELECT [Customer Mobile], [POINT REDUMPTION (DEDUCTION)], [Total Value] FROM Detailed_split_2", conn_det)
    conn_det.close()

    conn_mon = sqlite3.connect('monthly.db')
    df_mon = pd.read_sql("SELECT [Mobile Number] FROM r_f_monthly", conn_mon)
    conn_mon.close()

    df_det['p'] = pd.to_numeric(df_det['POINT REDUMPTION (DEDUCTION)'], errors='coerce').fillna(0).abs()
    df_det['v'] = pd.to_numeric(df_det['Total Value'], errors='coerce').fillna(0)

    def clean(m):
        m = str(m).strip()
        if m.endswith('.0'): m = m[:-2]
        return m

    df_det['m'] = df_det['Customer Mobile'].apply(clean)
    df_mon['m'] = df_mon['Mobile Number'].apply(clean)

    valid_mobs = set(df_mon['m'].unique())
    # User said "don't include 0". 
    # Let's try matching if there are 16 customers where the mobile number string is literally '0'.
    
    # Actually, my previous code discarded '0'. 
    # Let's see if 11,273 unique customers contains any that are "0" strings like "000".
    
    all_invalid = ['0', 'None', 'nan', '', '0.0', '0000000000']
    for i in all_invalid:
        valid_mobs.discard(i)

    df_merged = df_det[df_det['m'].isin(valid_mobs)]
    
    # Redemption customers
    df_red_txns = df_merged[df_merged['p'] > 0]
    red_customers_info = df_red_txns.groupby('m').agg({'p':'sum', 'v':'sum'})
    
    # We have 11,273. Target 11,257. (Diff 16)
    # Check for customers with very low point totals?
    p_low = red_customers_info.nsmallest(16, 'p')
    print("Lowest 16 by point sum:")
    print(p_low)
    
    # Check their total sum
    print(f"Total points of those 16: {p_low['p'].sum()}")
    # If this matches 29,280, we found it.

if __name__ == '__main__':
    find_16()
