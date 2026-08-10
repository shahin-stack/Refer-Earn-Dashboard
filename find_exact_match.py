import sqlite3
import pandas as pd

def find_exact():
    conn_det = sqlite3.connect('detailed_split.db')
    df_det = pd.read_sql("SELECT [Customer Mobile], [POINT REDUMPTION (DEDUCTION)], [Total Value] FROM Detailed_split_1 UNION ALL SELECT [Customer Mobile], [POINT REDUMPTION (DEDUCTION)], [Total Value] FROM Detailed_split_2", conn_det)
    conn_det.close()

    conn_mon = sqlite3.connect('monthly.db')
    df_mon = pd.read_sql("SELECT [Mobile Number] FROM r_f_monthly", conn_mon)
    conn_mon.close()

    df_det['POINT REDUMPTION (DEDUCTION)'] = pd.to_numeric(df_det['POINT REDUMPTION (DEDUCTION)'], errors='coerce').fillna(0).abs()
    df_det['Total Value'] = pd.to_numeric(df_det['Total Value'], errors='coerce').fillna(0)

    def clean_m(s):
        s = str(s).strip()
        if s.endswith('.0'): s = s[:-2]
        return s

    df_det['m_str'] = df_det['Customer Mobile'].apply(clean_m)
    df_mon['m_str'] = df_mon['Mobile Number'].apply(clean_m)

    # All unique in Mon
    valid_mobs = set(df_mon['m_str'].unique())

    # Filter 1: Basic joins
    # Target count: 11,257
    
    # Let's see how many have different lengths
    df_det['len'] = df_det['m_str'].str.len()
    
    # Let's try matching exact user numbers by iterating over filters
    # Filter A: Original logic - discard '0', 'nan', 'None'
    invalid = ['0', 'None', 'nan', '', '0.0']
    
    # Filter B: Length check?
    
    print("--- INVESTIGATION ---\n")
    
    mobs_to_try = set(valid_mobs)
    for i in invalid: mobs_to_try.discard(i)

    # Let's find exactly which 16 customers to remove if possible or which rule applies
    # 11,273 -> 11,257 (remove 16)
    
    df_merged = df_det[df_det['m_str'].isin(mobs_to_try)]
    df_red = df_merged[df_merged['POINT REDUMPTION (DEDUCTION)'] > 0]
    
    unique_red = df_red['m_str'].unique()
    print(f"Redeemed Unique Mobs: {len(unique_red)}")
    
    # Try filtering by length == 10
    unique_red_10 = [x for x in unique_red if len(x) == 10]
    print(f"Redeemed (length 10): {len(unique_red_10)}")

    # Try filtering by is_all_numeric
    unique_red_num = [x for x in unique_red if x.isdigit()]
    print(f"Redeemed (all numeric): {len(unique_red_num)}")
    
    # Try filtering where length >= 10 and all numeric
    unique_red_strict = [x for x in unique_red if x.isdigit() and len(x) >= 10]
    print(f"Redeemed (numeric and len>=10): {len(unique_red_strict)}")

    # Try filtering out specific patterns
    # e.g. '1234567890', '9999999999', etc.
    patterns_to_exclude = ['1234567890', '9999999999', '1111111111', '8888888888']
    unique_red_final = [x for x in unique_red if x not in patterns_to_exclude and x.isdigit() and len(x) >= 10]
    print(f"Redeemed (no dummy patterns): {len(unique_red_final)}")

    # Let's check sums for the 10-digit numeric ones
    final_mobs = set(unique_red_num) # let's start with all numeric
    # Maybe removing anything not exactly 10 digits?
    # Target: 11,257
    
    # Check lens distribution of unique_red_num
    from collections import Counter
    lens = Counter([len(x) for x in unique_red_num])
    print(f"Lens count: {lens}")

if __name__ == '__main__':
    find_exact()
