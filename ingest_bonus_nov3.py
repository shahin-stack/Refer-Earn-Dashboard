"""
Ingest 'Bonus Customer Report_export_1793678334775.xlsx' into ClickHouse refer_point_data table.
- Appends to existing data (does NOT truncate)
- Start Date is DD-MM-YYYY -> normalized to YYYY-MM-DD
- Idempotent duplicate guard using Counter on existing rows in date range
"""
from collections import Counter
import pandas as pd
import clickhouse_connect

EXCEL_FILE = r'C:\Users\SHAHIN\Desktop\Refer & Earn Dashboard\Bonus Customer Report_export_1793678334775.xlsx'

df = pd.read_excel(EXCEL_FILE, dtype=str)
print(f'Loaded {len(df):,} rows; columns: {list(df.columns)}')

parsed_dates = pd.to_datetime(df['Start Date'].str.strip(), format='%d-%m-%Y', errors='raise')
df['start_date'] = parsed_dates.dt.strftime('%Y-%m-%d')
df['customer_name'] = df['Customer Name'].fillna('').astype(str).str.strip()
df['customer_mobile_number'] = df['Customer Mobile'].fillna('').astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
df['campaign_name'] = df['Campaign Name'].fillna('').astype(str).str.strip()
df['bonus_points'] = pd.to_numeric(df['Bonus Point'], errors='raise').astype(float)

insert_df = df[['customer_name', 'customer_mobile_number', 'campaign_name', 'bonus_points', 'start_date']].copy()
print(f"Date range in file: {insert_df['start_date'].min()} -> {insert_df['start_date'].max()}")
print(f"Total bonus points in file: {insert_df['bonus_points'].sum():,.2f}")

client = clickhouse_connect.get_client(
    host='pdhsuv47ec.ap-south-1.aws.clickhouse.cloud',
    port=8443, username='default', password='ZFlujj9SA_Iei', secure=True
)

before = client.query('SELECT count() FROM refer_point_data').result_rows[0][0]
before_max = client.query('SELECT MAX(start_date) FROM refer_point_data').result_rows[0][0]
print(f'Rows BEFORE: {before:,}; max date: {before_max}')

# Duplicate guard: skip rows already present in ClickHouse for the file's date range
lo, hi = insert_df['start_date'].min(), insert_df['start_date'].max()
existing = client.query(
    "SELECT customer_mobile_number, campaign_name, bonus_points, start_date "
    f"FROM refer_point_data WHERE start_date >= '{lo}' AND start_date <= '{hi}'"
).result_rows
existing_counts = Counter((str(m), str(c), float(b), str(d)) for m, c, b, d in existing)
print(f'Existing rows in date range ({lo}..{hi}): {sum(existing_counts.values()):,}')

keep_indices = []
skipped = 0
for idx, r in insert_df.iterrows():
    key = (r['customer_mobile_number'], r['campaign_name'], r['bonus_points'], r['start_date'])
    if existing_counts[key] > 0:
        existing_counts[key] -= 1
        skipped += 1
    else:
        keep_indices.append(idx)

print(f'Already present (skipped): {skipped:,}')
insert_df = insert_df.loc[keep_indices]

if len(insert_df):
    client.insert_df('refer_point_data', insert_df)
    print(f'Inserted {len(insert_df):,} rows (bonus points: {insert_df["bonus_points"].sum():,.2f})')
else:
    print('Nothing new to insert')

after = client.query('SELECT count() FROM refer_point_data').result_rows[0][0]
after_min, after_max = client.query('SELECT MIN(start_date), MAX(start_date) FROM refer_point_data').result_rows[0]
print(f'Rows AFTER: {after:,} (+{after - before:,}); date range: {after_min} -> {after_max}')
print('Latest 7 dates in table:')
for d, c in client.query(
        'SELECT start_date, count() FROM refer_point_data GROUP BY start_date ORDER BY start_date DESC LIMIT 7'
).result_rows:
    print(f'  {d}: {c:,}')

