import sqlite3
import pandas as pd

def find_16():
    conn_det = sqlite3.connect('detailed_split.db')
    df_det = pd.read_sql("SELECT [Customer Mobile], [POINT REDUMPTION (DEDUCTION)], [Total Value] FROM Detailed_split_1 UNION ALL SELECT [Customer Mobile], [POINT REDUMPTION (DEDUCTION)], [Total Value] FROM Detailed_split_2", conn_det)
    conn_det.close()

    df_det['p'] = pd.to_numeric(df_det['POINT REDUMPTION (DEDUCTION)'], errors='coerce').fillna(0).abs()
    df_red = df_det[df_det['p'] > 0]
    
    unique_mobs = df_red['Customer Mobile'].unique()
    print(f"Unique Customer Mobiles in Redemptions (Raw): {len(unique_mobs)}")
    
    # 1. How many are '0'?
    # 2. How many are '0.0'?
    # 3. How many are blank?
    
    zero_variants = ['0', 0, 0.0, '0.0', ' 0 ', 'None', 'nan', '']
    z_count = 0
    for v in zero_variants:
        match = [m for m in unique_mobs if m == v]
        if match:
            print(f"Found match for {v}: {len(match)}")
            z_count += len(match)
            
    # Try cleaning and seeing what remains
    def clean(m):
        return str(m).strip().split('.')[0]
    
    cleaned = set([clean(m) for m in unique_mobs])
    print(f"Cleaned unique count: {len(cleaned)}")
    
    # Target: 11,257. (My current cleaned 11,273 - target 11,257 = 16).
    # Removing 16.
    
    # Let's count how many start with 0
    starts_0 = [x for x in cleaned if x.startswith('0')]
    print(f"Starts with 0: {len(starts_0)}")

if __name__ == '__main__':
    find_16()
