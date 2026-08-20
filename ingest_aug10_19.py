"""
Ingest refer_point_data august 10 - 19.xlsx into ClickHouse refer_point_data table.
Maps Excel columns → ClickHouse columns:
  Customer Name        → customer_name
  Customer Mobile      → customer_mobile_number  (int → string)
  Campaign Name        → campaign_name
  Bonus Point          → bonus_points
  Start Date (DD-MM-YYYY) → start_date (YYYY-MM-DD)
End Date and Days columns are not in the CH table, so they are dropped.
"""
import pandas as pd
import clickhouse_connect
from datetime import datetime

EXCEL_FILE = r'C:\Users\SHAHIN\Desktop\Refer & Earn Dashboard\refer_point_data august 10 - 19.xlsx'

# ── 1. Load Excel ──────────────────────────────────────────────────────────────
print("Loading Excel file...")
df = pd.read_excel(EXCEL_FILE)
print(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")

# ── 2. Transform ───────────────────────────────────────────────────────────────
# Convert Start Date from DD-MM-YYYY  →  YYYY-MM-DD string
df['start_date'] = pd.to_datetime(df['Start Date'], format='%d-%m-%Y').dt.strftime('%Y-%m-%d')

# Mobile number as string (drop any .0 suffix if it appeared)
df['customer_mobile_number'] = df['Customer Mobile'].astype(str).str.replace(r'\.0$', '', regex=True)

# Rename remaining columns
df = df.rename(columns={
    'Customer Name': 'customer_name',
    'Campaign Name': 'campaign_name',
    'Bonus Point':   'bonus_points',
})

# Keep only the 5 columns that exist in ClickHouse
df = df[['customer_name', 'customer_mobile_number', 'campaign_name', 'bonus_points', 'start_date']]

# Ensure bonus_points is float
df['bonus_points'] = df['bonus_points'].astype(float)

print(f"  Date range in file: {df['start_date'].min()} -> {df['start_date'].max()}")
print(f"  Sample row: {df.iloc[0].to_dict()}")

# ── 3. Connect to ClickHouse ───────────────────────────────────────────────────
print("\nConnecting to ClickHouse...")
client = clickhouse_connect.get_client(
    host='pdhsuv47ec.ap-south-1.aws.clickhouse.cloud',
    port=8443, username='default', password='ZFlujj9SA_Iei', secure=True
)

# Verify count before insert
before = client.query('SELECT count() FROM refer_point_data').result_rows[0][0]
before_max = client.query("SELECT MAX(start_date) FROM refer_point_data").result_rows[0][0]
print(f"  Rows BEFORE insert : {int(before):,}")
print(f"  Last date BEFORE   : {before_max}")

# -- 4. Insert ------------------------------------------------------------------
print(f"\nInserting {len(df):,} rows into refer_point_data...")
client.insert_df('refer_point_data', df)
print("  Insert complete OK")

# -- 5. Verify ------------------------------------------------------------------
after = client.query('SELECT count() FROM refer_point_data').result_rows[0][0]
after_max = client.query("SELECT MAX(start_date) FROM refer_point_data").result_rows[0][0]
print(f"\n  Rows AFTER insert  : {int(after):,}  (+{int(after)-int(before):,})")
print(f"  Last date AFTER    : {after_max}")
print("\nDone! OK")
