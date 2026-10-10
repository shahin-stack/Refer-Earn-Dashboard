"""
Ingest 'Bonus Customer Report_export_1791258173645.xlsx' into ClickHouse refer_point_data table.
- Appends to existing data (does NOT truncate)
- Start Date is DD-MM-YYYY -> normalized to YYYY-MM-DD
- Skips rows already present (same mobile + campaign + bonus_points + start_date)
"""
import pandas as pd
import clickhouse_connect

EXCEL_FILE = r'C:\Users\SHAHIN\Desktop\Refer & Earn Dashboard\Bonus Customer Report_export_1791258173645.xlsx'

df = pd.read_excel(EXCEL_FILE, dtype=str)
print(f'Loaded {len(df):,} rows; columns: {list(df.columns)}')

df['start_date'] = pd.to_datetime(df['Start Date'].str.strip(), format='%d-%m-%Y').dt.strftime('%Y-%m-%d')
df['customer_name'] = df['Customer Name'].fillna('').astype(str).str.strip()
df['customer_mobile_number'] = df['Customer Mobile'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
df['campaign_name'] = df['Campaign Name'].fillna('').astype(str).str.strip()
df['bonus_points'] = pd.to_numeric(df['Bonus Point'], errors='coerce').fillna(0).astype(float)

insert_df = df[['customer_name', 'customer_mobile_number', 'campaign_name', 'bonus_points', 'start_date']].copy()
print(f"Date range in file: {insert_df['start_date'].min()} -> {insert_df['start_date'].max()}")

client = clickhouse_connect.get_client(
    host='pdhsuv47ec.ap-south-1.aws.clickhouse.cloud',
    port=8443, username='default', password='ZFlujj9SA_Iei', secure=True
)

before = client.query('SELECT count() FROM refer_point_data').result_rows[0][0]
before_max = client.query('SELECT MAX(start_date) FROM refer_point_data').result_rows[0][0]
print(f'Rows BEFORE: {before:,}; max date: {before_max}')

# Duplicate guard: drop rows already in the table for the file's date range
lo, hi = insert_df['start_date'].min(), insert_df['start_date'].max()
existing = client.query(
    "SELECT customer_mobile_number, campaign_name, bonus_points, start_date "
    f"FROM refer_point_data WHERE start_date >= '{lo}' AND start_date <= '{hi}'"
).result_rows
existing_keys = {(str(m), c, float(b), str(d)) for m, c, b, d in existing}
print(f'Existing rows in date range: {len(existing_keys):,}')

mask = insert_df.apply(
    lambda r: (r['customer_mobile_number'], r['campaign_name'], r['bonus_points'], r['start_date']) in existing_keys,
    axis=1)
print(f'Already present (skipped): {int(mask.sum())}')
insert_df = insert_df[~mask]

if len(insert_df):
    client.insert_df('refer_point_data', insert_df)
    print(f'Inserted {len(insert_df):,} rows')
else:
    print('Nothing new to insert')

after = client.query('SELECT count() FROM refer_point_data').result_rows[0][0]
after_max = client.query('SELECT MAX(start_date) FROM refer_point_data').result_rows[0][0]
print(f'Rows AFTER: {after:,} (+{after - before:,}); max date: {after_max}')
