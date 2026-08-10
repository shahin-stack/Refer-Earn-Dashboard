import sqlite3
import pandas as pd

start_date = '2026-03-01'
end_date = '2026-03-01'

dr = pd.date_range(start=start_date, end=end_date)
date_list = [d.strftime('%d-%m-%Y') for d in dr]
print("Date list:", date_list)

conn_det = sqlite3.connect('detailed_split.db')
tables_res = conn_det.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
tables = [r[0] for r in tables_res if r[0] != 'sqlite_sequence']

queries = []
params = []
for t in tables:
    placeholders = ','.join(['?'] * len(date_list))
    q = f'SELECT [Date], [Customer Mobile], [Total Value], [POINT REDUMPTION (DEDUCTION)] FROM "{t}" WHERE [Date] IN ({placeholders})'
    params.extend(date_list)
    queries.append(q)

query = " UNION ALL ".join(queries)
df = pd.read_sql(query, conn_det, params=params)
print("Detailed DF shape:", df.shape)
if not df.empty:
    df['mob'] = df['Customer Mobile'].astype(str).str.strip().str.replace('.0', '', regex=False)
conn_det.close()

conn_mon = sqlite3.connect('monthly.db')
master_df = pd.read_sql(
    "SELECT [MOBILE_NUMBER] as Mobile, [BONUS_POINTS] as [Sum of Point] FROM r_f_monthly_OG WHERE SUBSTR(START_DATE, 1, 10) >= ? AND SUBSTR(START_DATE, 1, 10) <= ?",
    conn_mon, params=(start_date, end_date)
)
print("Master DF shape:", master_df.shape)
master_df['mob'] = master_df['Mobile'].astype(str).str.strip().str.replace('.0', '', regex=False)
conn_mon.close()

valid_member_mobs = set(master_df['mob'].tolist())
print("Valid member mobs count:", len(valid_member_mobs))

if not df.empty:
    df = df[df['mob'].isin(valid_member_mobs)]

print("Filtered Detailed DF shape:", df.shape)

