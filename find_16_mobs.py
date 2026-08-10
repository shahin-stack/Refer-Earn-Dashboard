import sqlite3
import pandas as pd

def find_target_customers():
    conn_det = sqlite3.connect('detailed_split.db')
    df_det = pd.read_sql("SELECT [Customer Mobile], [POINT REDUMPTION (DEDUCTION)], [Total Value] FROM Detailed_split_1 UNION ALL SELECT [Customer Mobile], [POINT REDUMPTION (DEDUCTION)], [Total Value] FROM Detailed_split_2", conn_det)
    conn_det.close()

    conn_mon = sqlite3.connect('monthly.db')
    df_mon = pd.read_sql("SELECT [Mobile Number] FROM r_f_monthly", conn_mon)
    conn_mon.close()

    # Pre-clean
    df_det['POINT REDUMPTION (DEDUCTION)'] = pd.to_numeric(df_det['POINT REDUMPTION (DEDUCTION)'], errors='coerce').fillna(0).abs()
    df_det['Total Value'] = pd.to_numeric(df_det['Total Value'], errors='coerce').fillna(0)

    def clean_m(s):
        s = str(s).strip()
        if s.endswith('.0'): s = s[:-2]
        return s

    df_det['m'] = df_det['Customer Mobile'].apply(clean_m)
    df_mon['m'] = df_mon['Mobile Number'].apply(clean_m)

    # All unique in Mon (Join keys)
    valid_mobs = set(df_mon['m'].unique())
    # User said "don't include 0". Let's assume they mean many variants of 0 or invalid.
    invalid = ['0', 'None', 'nan', '', '0000000000', '1234567890']
    for i in invalid:
        valid_mobs.discard(i)

    # Initial merge
    df_merged = df_det[df_det['m'].isin(valid_mobs)]
    
    # Redeemed Customers (p > 0)
    df_red_txns = df_merged[df_merged['POINT REDUMPTION (DEDUCTION)'] > 0]
    red_mobs = set(df_red_txns['m'].unique())
    
    print(f"Current Redeemed Customer Count: {len(red_mobs)}")
    # Current: 11,273. Target: 11,257. (Diff: 16)
    
    # Let's check for "Mobile Number" that are not 10 digits
    abnormal = [m for m in red_mobs if len(m) != 10]
    print(f"Customers with non-10 digit numbers: {len(abnormal)}")
    print(abnormal)
    
    # What if we exclude anything that isn't exactly a 10-digit number?
    cleaned_red_mobs = [m for m in red_mobs if len(m) == 10 and m.isdigit()]
    print(f"Redeemed Count (Strict 10 digits): {len(cleaned_red_mobs)}")

if __name__ == '__main__':
    find_target_customers()
