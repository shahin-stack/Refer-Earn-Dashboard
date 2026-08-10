import sqlite3
import pandas as pd

def check_mobs():
    conn_det = sqlite3.connect('detailed_split.db')
    df_det = pd.read_sql("SELECT [Customer Mobile], [POINT REDUMPTION (DEDUCTION)] FROM Detailed_split_1 UNION ALL SELECT [Customer Mobile], [POINT REDUMPTION (DEDUCTION)] FROM Detailed_split_2", conn_det)
    conn_det.close()

    df_det['p'] = pd.to_numeric(df_det['POINT REDUMPTION (DEDUCTION)'], errors='coerce').fillna(0).abs()
    df_red = df_det[df_det['p'] > 0]

    def clean_m(s):
        s = str(s).strip()
        if s.endswith('.0'): s = s[:-2]
        return s

    df_red['m'] = df_red['Customer Mobile'].apply(clean_m)
    u = df_red['m'].unique()
    print(f"Total Unique Redeemed Customers: {len(u)}")

    starts_0 = [x for x in u if x.startswith('0')]
    print(f"Count of Redeemed starting with 0: {len(starts_0)}")
    if len(starts_0) > 0:
        print(f"List of those 0-starting mobs: {starts_0}")

    others = [x for x in u if not x.isdigit()]
    print(f"Count of non-digit redeemed mobs: {len(others)}")
    if len(others) > 0:
        print(others)

if __name__ == '__main__':
    check_mobs()
