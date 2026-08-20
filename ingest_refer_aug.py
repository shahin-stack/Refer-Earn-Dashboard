"""
Ingest 'refer point data august 1-9 2026.xlsx' into ClickHouse refer_point_data table.
- Appends to existing data (does NOT truncate)
- Normalizes Start Date from DD-MM-YYYY to YYYY-MM-DD to match existing format
- Maps column names to match table schema
"""

import pandas as pd
import clickhouse_connect
from datetime import datetime

# ── Config ─────────────────────────────────────────────────────────────────────
EXCEL_FILE = 'refer point data august 1-9 2026.xlsx'

CH_HOST     = 'pdhsuv47ec.ap-south-1.aws.clickhouse.cloud'
CH_PORT     = 8443
CH_USER     = 'default'
CH_PASSWORD = 'ZFlujj9SA_Iei'

# ── Read Excel ─────────────────────────────────────────────────────────────────
print(f'Reading {EXCEL_FILE}...')
df = pd.read_excel(EXCEL_FILE, dtype=str)
print(f'  Raw rows: {len(df)}')
print(f'  Columns : {list(df.columns)}')

# ── Normalize date: DD-MM-YYYY -> YYYY-MM-DD ───────────────────────────────────
def normalize_date(val):
    val = str(val).strip()
    for fmt in ('%d-%m-%Y', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(val[:len(fmt)], fmt).strftime('%Y-%m-%d')
        except:
            pass
    try:
        return pd.to_datetime(val, dayfirst=True).strftime('%Y-%m-%d')
    except:
        return val

df['start_date'] = df['Start Date'].apply(normalize_date)
print(f'  Sample dates after normalization: {df["start_date"].head(5).tolist()}')

# ── Map and clean columns to match refer_point_data schema ────────────────────
# Table schema: customer_name, customer_mobile_number, campaign_name, bonus_points, start_date
df['customer_name']          = df['Customer Name'].fillna('').astype(str).str.strip()
df['customer_mobile_number'] = df['Customer Mobile'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
df['campaign_name']          = df['Campaign Name'].fillna('').astype(str).str.strip()
df['bonus_points']           = pd.to_numeric(df['Bonus Point'], errors='coerce').fillna(0).astype(float)

# Keep only the 5 table columns in correct order
insert_df = df[['customer_name', 'customer_mobile_number', 'campaign_name', 'bonus_points', 'start_date']]

print(f'\n  Sample after mapping:')
print(insert_df.head(5).to_string())
print(f'\n  Date range: {insert_df["start_date"].min()} to {insert_df["start_date"].max()}')

# ── Connect to ClickHouse ──────────────────────────────────────────────────────
print('\nConnecting to ClickHouse...')
client = clickhouse_connect.get_client(
    host=CH_HOST, port=CH_PORT,
    username=CH_USER, password=CH_PASSWORD,
    secure=True
)

# ── Check existing row count ───────────────────────────────────────────────────
existing = client.query('SELECT count() FROM refer_point_data').result_rows[0][0]
print(f'  Existing rows in refer_point_data: {existing:,}')

# ── Insert (APPEND - no truncate) ──────────────────────────────────────────────
print(f'\nInserting {len(insert_df)} rows into refer_point_data...')
client.insert_df('refer_point_data', insert_df)
print(f'[OK] Done! {len(insert_df)} rows inserted.')

# ── Verify ─────────────────────────────────────────────────────────────────────
total = client.query('SELECT count() FROM refer_point_data').result_rows[0][0]
max_date = client.query("SELECT MAX(start_date) FROM refer_point_data").result_rows[0][0]
min_date = client.query("SELECT MIN(start_date) FROM refer_point_data").result_rows[0][0]

print(f'\n[OK] Verification:')
print(f'  Total rows in refer_point_data : {total:,}')
print(f'  Earliest start_date            : {min_date}')
print(f'  Latest start_date              : {max_date}')
