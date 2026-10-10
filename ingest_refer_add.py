"""
Ingest 'refer add.xlsx' into ClickHouse refer_point_data table.
- Appends to existing data (does NOT truncate)
- Normalizes Start Date (DD-MM-YYYY) to YYYY-MM-DD
- Maps columns: Customer Name, Customer Mobile, Campaign Name, Bonus Point, Start Date
- Usage: python ingest_refer_add.py          (dry run)
         python ingest_refer_add.py --commit (insert)
"""

import sys
import pandas as pd
import clickhouse_connect

EXCEL_FILE  = 'refer add.xlsx'
CH_HOST     = 'pdhsuv47ec.ap-south-1.aws.clickhouse.cloud'
CH_PORT     = 8443
CH_USER     = 'default'
CH_PASSWORD = 'ZFlujj9SA_Iei'

COMMIT = '--commit' in sys.argv

df = pd.read_excel(EXCEL_FILE, dtype=str)
print(f'Raw rows: {len(df):,}  Columns: {list(df.columns)}')

parsed = pd.to_datetime(df['Start Date'].astype(str).str.strip(), format='%d-%m-%Y', errors='coerce')
bad = parsed.isna().sum()
if bad:
    # fallback for values with a time part / other formats
    fallback = pd.to_datetime(df.loc[parsed.isna(), 'Start Date'], dayfirst=True, errors='coerce')
    parsed[parsed.isna()] = fallback
    bad = parsed.isna().sum()
print(f'Unparseable dates: {bad}')
if bad:
    print(df[parsed.isna()].head(10).to_string())
    sys.exit('Aborting: fix unparseable dates first.')

ins = pd.DataFrame({
    'customer_name':          df['Customer Name'].fillna('').astype(str).str.strip(),
    'customer_mobile_number': df['Customer Mobile'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True),
    'campaign_name':          df['Campaign Name'].fillna('').astype(str).str.strip(),
    'bonus_points':           pd.to_numeric(df['Bonus Point'], errors='coerce').fillna(0).astype(float),
    'start_date':             parsed.dt.strftime('%Y-%m-%d'),
})

print(f'Date range: {ins.start_date.min()} -> {ins.start_date.max()}')
print(ins.groupby('start_date').size().to_string())

client = clickhouse_connect.get_client(host=CH_HOST, port=CH_PORT, username=CH_USER,
                                       password=CH_PASSWORD, secure=True)
before = client.query('SELECT count() FROM refer_point_data').result_rows[0][0]
print(f'\nRows before: {before:,}')
ex = client.query(
    f"SELECT start_date, count() FROM refer_point_data WHERE start_date >= '{ins.start_date.min()}' "
    f"GROUP BY start_date ORDER BY start_date").result_rows
print('Existing rows in the file date range:', ex)

if not COMMIT:
    print('\nDRY RUN - nothing inserted. Re-run with --commit.')
    sys.exit(0)

client.insert_df('refer_point_data', ins)
after = client.query('SELECT count() FROM refer_point_data').result_rows[0][0]
r = client.query('SELECT MIN(start_date), MAX(start_date) FROM refer_point_data').result_rows[0]
print(f'[OK] Rows after: {after:,} (+{after - before:,}); range {r[0]} -> {r[1]}')
