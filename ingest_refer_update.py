import pandas as pd
import clickhouse_connect, os

# ── Load Excel ──────────────────────────────────────────────────────────────
df = pd.read_excel('refer update.xlsx')
print(f'Loaded {len(df)} rows from Excel')

# ── Normalise columns to match CH schema ────────────────────────────────────
df = df.rename(columns={
    'Customer Name'  : 'customer_name',
    'Customer Mobile': 'customer_mobile_number',
    'Campaign Name'  : 'campaign_name',
    'Bonus Point'    : 'bonus_points',
    'Start Date'     : 'start_date'
})

# Mobile: int64 -> 10-digit string
df['customer_mobile_number'] = df['customer_mobile_number'].astype(str).str.strip()

# start_date: DD-MM-YYYY -> YYYY-MM-DD (matches existing '2026-01-25' format)
df['start_date'] = pd.to_datetime(df['start_date'], dayfirst=True).dt.strftime('%Y-%m-%d')

# bonus_points: float64
df['bonus_points'] = df['bonus_points'].astype(float)

# strings
df['customer_name'] = df['customer_name'].astype(str).str.strip()
df['campaign_name'] = df['campaign_name'].astype(str).str.strip()

print('Sample after transform:')
print(df.head(3).to_string())
print()
print('Date range:', df['start_date'].min(), '->', df['start_date'].max())

# ── Connect ──────────────────────────────────────────────────────────────────
client = clickhouse_connect.get_client(
    host    = os.environ.get('CLICKHOUSE_HOST', 'pdhsuv47ec.ap-south-1.aws.clickhouse.cloud'),
    port    = int(os.environ.get('CLICKHOUSE_PORT', 8443)),
    username= os.environ.get('CLICKHOUSE_USER', 'default'),
    password= os.environ.get('CLICKHOUSE_PASSWORD', 'ZFlujj9SA_Iei'),
    secure  = True
)

# ── Insert ───────────────────────────────────────────────────────────────────
cols = ['customer_name', 'customer_mobile_number', 'campaign_name', 'bonus_points', 'start_date']
data = [list(row) for row in df[cols].itertuples(index=False, name=None)]

client.insert('refer_point_data', data, column_names=cols)
print(f'Inserted {len(data)} rows into refer_point_data')

# ── Verify ───────────────────────────────────────────────────────────────────
res = client.query(
    'SELECT max(start_date), count(), countDistinct(customer_mobile_number) FROM refer_point_data'
).result_rows[0]
print(f'Table now: last_date={res[0]}, total_rows={int(res[1]):,}, unique_mobs={int(res[2]):,}')
