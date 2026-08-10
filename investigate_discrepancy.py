import sqlite3
import pandas as pd

def investigate():
    conn_det = sqlite3.connect('detailed_split.db')
    df_det = pd.read_sql("SELECT [Customer Mobile], [POINT REDUMPTION (DEDUCTION)], [Total Value] FROM Detailed_split_1 UNION ALL SELECT [Customer Mobile], [POINT REDUMPTION (DEDUCTION)], [Total Value] FROM Detailed_split_2", conn_det)
    conn_det.close()

    conn_mon = sqlite3.connect('monthly.db')
    df_mon = pd.read_sql("SELECT [Mobile Number] FROM r_f_monthly", conn_mon)
    conn_mon.close()

    # Pre-clean
    df_det['POINT REDUMPTION (DEDUCTION)'] = pd.to_numeric(df_det['POINT REDUMPTION (DEDUCTION)'], errors='coerce').fillna(0).abs()
    df_det['Total Value'] = pd.to_numeric(df_det['Total Value'], errors='coerce').fillna(0)

    # Let's try to find 11,257
    # My current is 11,273
    
    # Check for non-10 digit numbers
    def check_mob(m):
        m = str(m).strip()
        if m.endswith('.0'): m = m[:-2]
        return m

    df_det['m_str'] = df_det['Customer Mobile'].apply(check_mob)
    df_mon['m_str'] = df_mon['Mobile Number'].apply(check_mob)

    # Filter out common invalid
    invalid_tags = ['0', 'None', 'nan', '', '0000000000', '1234567890']
    
    valid_mobs = set(df_mon['m_str'].unique())
    for tag in invalid_tags:
        valid_mobs.discard(tag)

    df_merged = df_det[df_det['m_str'].isin(valid_mobs)]
    
    # Redeemed customers
    df_red = df_merged[df_merged['POINT REDUMPTION (DEDUCTION)'] > 0]
    red_mobs = df_red['m_str'].unique()
    
    print(f"Redeemed Count (Cleaned): {len(red_mobs)}")
    
    # If it's still not 11,257, let's look at what's extra.
    # User's reported point total: 5,686,539
    # My current point total: 5,715,819 (approx)
    
    p_sum = df_red['POINT REDUMPTION (DEDUCTION)'].sum()
    print(f"Points Sum (All redeemed txns): {p_sum:,.2f}")
    
    # Purchase Value for those 11,257
    all_txns_red = df_merged[df_merged['m_str'].isin(red_mobs)]
    pur_sum = all_txns_red['Total Value'].sum()
    print(f"Purchase Sum (All txns for redeemed): {pur_sum:,.2f}")

    # Check for any specific rows where point is small?
    # Or maybe there are some '0's in the Customer Mobile field that I missed?
    
if __name__ == '__main__':
    investigate()
