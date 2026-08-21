"""
Re-ingest Loyalty user data.xlsx into ClickHouse loyalty_user_data table.
Includes District column this time.
"""
import pandas as pd
import clickhouse_connect
import uuid

EXCEL_FILE = 'Loyalty user data.xlsx'
CH_HOST     = 'pdhsuv47ec.ap-south-1.aws.clickhouse.cloud'
CH_PORT     = 8443
CH_USER     = 'default'
CH_PASSWORD = 'ZFlujj9SA_Iei'

print(f'Reading {EXCEL_FILE}...')
df = pd.read_excel(EXCEL_FILE, dtype=str)
print(f'  Rows    : {len(df):,}')
print(f'  Columns : {list(df.columns)}')

# Generate UUID for id
df['id'] = [str(uuid.uuid4()) for _ in range(len(df))]

# Clean all columns
for col in df.columns:
    df[col] = df[col].fillna('').astype(str).str.strip()
    df[col] = df[col].replace('nan', '')

# Map District -> district
df['district'] = df['District'].str.upper().str.strip()

# Show sample
top5 = df['district'].value_counts().head(5)
print('\n  Top 5 districts in Excel:')
for d, c in top5.items():
    print(f'    {d}: {c:,}')

# Select CH columns in correct order (now with district)
insert_df = df[[
    'id', 'created_at', 'user_phone', 'user_email', 'firstname', 'lastname',
    'updated_at', 'user_id', 'address', 'pincode', 'state', 'district',
    'date_of_birth', 'wedding_anniversary', 'married', 'update_count',
    'profile_status', 'gender'
]]

print(f'\nSample:')
print(insert_df[['user_phone', 'firstname', 'state', 'district']].head(5).to_string())

# Connect and insert
print('\nConnecting to ClickHouse...')
client = clickhouse_connect.get_client(
    host=CH_HOST, port=CH_PORT,
    username=CH_USER, password=CH_PASSWORD,
    secure=True
)

before = client.query('SELECT count() FROM loyalty_user_data').result_rows[0][0]
print(f'  Rows BEFORE: {before:,}')

print(f'\nInserting {len(insert_df):,} rows...')
client.insert_df('loyalty_user_data', insert_df)
print('[OK] Insert complete.')

# Verify
after = client.query('SELECT count() FROM loyalty_user_data').result_rows[0][0]
top5_ch = client.query(
    "SELECT district, count() as c FROM loyalty_user_data WHERE district != '' GROUP BY district ORDER BY c DESC LIMIT 5"
).result_rows

print(f'\n[OK] Verification:')
print(f'  Rows AFTER : {after:,}  (+{after - before:,})')
print('  Top 5 districts in ClickHouse:')
for r in top5_ch:
    print(f'    {r[0]}: {int(r[1]):,}')
