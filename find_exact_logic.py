import sqlite3
import pandas as pd

def find_exact_logic():
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
    
    # Try different filter combinations to hit 11,257
    print("--- BRUTE FORCE FILTER FINDER ---\n")
    
    # Baseline: exclude common junk
    junk = ['0', 'None', 'nan', '', '0.0']
    
    for exclude_set in [junk, junk + ['0000000000']]:
        v_mobs = set(valid_mobs)
        for j in exclude_set: v_mobs.discard(j)
        
        df_m = df_det[df_det['m'].isin(v_mobs)]
        df_red = df_m[df_m['POINT REDUMPTION (DEDUCTION)'] > 0]
        redeemed_customers = df_red['m'].unique()
        
        count = len(redeemed_customers)
        points = df_red['POINT REDUMPTION (DEDUCTION)'].sum()
        
        # logic: total redeemed customer total purchase value
        purchase_val = df_m[df_m['m'].isin(redeemed_customers)]['Total Value'].sum()
        
        print(f"Filter {exclude_set}:")
        print(f"  Count: {count:,}")
        print(f"  Points: {points:,.2f}")
        print(f"  Purchase Val: {purchase_val:,.2f}\n")
        
    # If not matching, let's look at the top 20 customers by Point sum that might be "0" variants
    # Target gap: 16 customers, 29,280 points.
    
if __name__ == '__main__':
    find_exact_logic()
