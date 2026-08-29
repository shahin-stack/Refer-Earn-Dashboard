"""
Ingest 'refer point latest.xlsx' into ClickHouse refer_point_data table.
- Appends to existing data (does NOT truncate)
- Normalizes Start Date from DD-MM-YYYY to YYYY-MM-DD
- Maps column names to match table schema:
    customer_name, customer_mobile_number, campaign_name, bonus_points, start_date
"""

import pandas as pd
import clickhouse_connect
from datetime import datetime

# ── Config ─────────────────────────────────────────────────────────────────────
EXCEL_FILE  = 'refer point latest.xlsx'

CH_HOST     = 'pdhsuv47ec.ap-south-1.aws.clickhouse.cloud'
CH_PORT     = 8443
CH_USER     = 'default'
CH_PASSWORD = 'ZFlujj9SA_Iei'

# ── Read Excel ─────────────────────────────────────────────────────────────────
print(f'Reading {EXCEL_FILE}...')
df = pd.read_excel(EXCEL_FILE, dtype=str)
print(f'  Raw rows : {len(df):,}')
print(f'  Columns  : {list(df.columns)}')

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

df['start_date']             = df['Start Date'].apply(normalize_date)
df['customer_name']          = df['Customer Name'].fillna('').astype(str).str.strip()
df['customer_mobile_number'] = df['Customer Mobile'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
df['campaign_name']          = df['Campaign Name'].fillna('').astype(str).str.strip()
df['bonus_points']           = pd.to_numeric(df['Bonus Point'], errors='coerce').fillna(0).astype(float)

# Keep only the 5 table columns in correct order
insert_df = df[['customer_name', 'customer_mobile_number', 'campaign_name', 'bonus_points', 'start_date']]

print(f'\n  Date range : {insert_df["start_date"].min()} to {insert_df["start_date"].max()}')
print(f'\n  Sample rows:')
print(insert_df.head(5).to_string())

# ── Connect to ClickHouse ──────────────────────────────────────────────────────
print('\nConnecting to ClickHouse...')
client = clickhouse_connect.get_client(
    host=CH_HOST, port=CH_PORT,
    username=CH_USER, password=CH_PASSWORD,
    secure=True
)

before = client.query('SELECT count() FROM refer_point_data').result_rows[0][0]
print(f'  Rows BEFORE insert : {before:,}')

# ── Insert (APPEND - no truncate) ──────────────────────────────────────────────
print(f'\nInserting {len(insert_df):,} rows into refer_point_data...')
client.insert_df('refer_point_data', insert_df)
print('[OK] Insert complete.')

# ── Verify ─────────────────────────────────────────────────────────────────────
after    = client.query('SELECT count() FROM refer_point_data').result_rows[0][0]
max_date = client.query("SELECT MAX(start_date) FROM refer_point_data").result_rows[0][0]
min_date = client.query("SELECT MIN(start_date) FROM refer_point_data").result_rows[0][0]

print(f'\n[OK] Verification:')
print(f'  Rows BEFORE insert : {before:,}')
print(f'  Rows AFTER  insert : {after:,}  (+{after - before:,} new rows)')
print(f'  Full date range    : {min_date} -> {max_date}')
