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
    # User says "don't include 0". Let's assume they mean many variants of 0.
    invalid = ['0', 'None', 'nan', '', '0.0', '0000000000']
    for i in invalid:
        valid_mobs.discard(i)

    df_merged = df_det[df_det['m'].isin(valid_mobs)]
    
    # Target: 11,257. (My current 11,273 - 11,257 = 16).
    # Removing 16.
    
    df_red = df_merged[df_merged['p'] > 0]
    u_red = df_red['m'].unique()
    print(f"Current unique redeemed in both: {len(u_red)}")
    
    # Are there 16 customers who have points > 0 but purchase value <= 0?
    df_customer_sums = df_merged[df_merged['m'].isin(u_red)].groupby('m').agg({'p': 'sum', 'v': 'sum'})
    
    # Maybe filtering out those who have 0 total value?
    zero_val = df_customer_sums[df_customer_sums['v'] <= 0]
    print(f"Customers with 0 or less total value: {len(zero_val)}")
    
    # Target 16? If this is 16, we found it!
    # Let's check it.
    
if __name__ == '__main__':
    find_16()
