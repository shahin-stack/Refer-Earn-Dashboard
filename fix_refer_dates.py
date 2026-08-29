"""
Fix bad dates in refer_point_data ClickHouse table.

Problem: 163 rows have start_date = '2026-12-08' which is actually '2026-08-12'
         (the date was parsed as MM-DD instead of DD-MM).

Fix strategy (ClickHouse ReplacingMergeTree / MergeTree approach):
  1. Fetch all 163 bad rows
  2. Delete them using ALTER TABLE DELETE
  3. Re-insert with corrected date '2026-08-12'
"""

import clickhouse_connect
import time

client = clickhouse_connect.get_client(
    host='pdhsuv47ec.ap-south-1.aws.clickhouse.cloud',
    port=8443, username='default', password='ZFlujj9SA_Iei', secure=True
)

BAD_DATE     = '2026-12-08'
CORRECT_DATE = '2026-08-12'

# ── Step 1: Fetch all bad rows ─────────────────────────────────────────────────
print(f'Fetching rows with start_date = {BAD_DATE}...')
r = client.query(
    f"SELECT customer_name, customer_mobile_number, campaign_name, bonus_points, start_date "
    f"FROM refer_point_data WHERE start_date = '{BAD_DATE}'"
)
bad_rows = r.result_rows
print(f'  Found {len(bad_rows):,} rows to fix.')

if not bad_rows:
    print('Nothing to fix. Exiting.')
    exit()

print(f'  Sample: {bad_rows[:3]}')

# ── Step 2: Delete bad rows from ClickHouse ────────────────────────────────────
print(f'\nDeleting {len(bad_rows):,} rows with start_date = {BAD_DATE}...')
client.command(f"ALTER TABLE refer_point_data DELETE WHERE start_date = '{BAD_DATE}'")
print('  DELETE issued. Waiting for mutation to settle...')
time.sleep(5)  # give ClickHouse time to apply the lightweight delete

# Confirm deletion
count_after_delete = client.query(
    f"SELECT count() FROM refer_point_data WHERE start_date = '{BAD_DATE}'"
).result_rows[0][0]
print(f'  Rows with bad date remaining: {count_after_delete}')

# ── Step 3: Re-insert with corrected date ─────────────────────────────────────
print(f'\nRe-inserting {len(bad_rows):,} rows with corrected date {CORRECT_DATE}...')

fixed_rows = [
    (row[0], row[1], row[2], row[3], CORRECT_DATE)
    for row in bad_rows
]

column_names = ['customer_name', 'customer_mobile_number', 'campaign_name', 'bonus_points', 'start_date']
client.insert('refer_point_data', fixed_rows, column_names=column_names)
print('[OK] Re-insert complete.')

# ── Step 4: Final verification ─────────────────────────────────────────────────
time.sleep(3)
r_final = client.query('SELECT MIN(start_date), MAX(start_date), count() FROM refer_point_data')
min_d, max_d, total = r_final.result_rows[0]

bad_remaining = client.query(
    f"SELECT count() FROM refer_point_data WHERE start_date = '{BAD_DATE}'"
).result_rows[0][0]

fixed_count = client.query(
    f"SELECT count() FROM refer_point_data WHERE start_date = '{CORRECT_DATE}'"
).result_rows[0][0]

print(f'\n[OK] Final Verification:')
print(f'  Total rows        : {total:,}')
print(f'  Min date          : {min_d}')
print(f'  Max date          : {max_d}')
print(f'  Rows on {BAD_DATE}  : {bad_remaining}  (should be 0)')
print(f'  Rows on {CORRECT_DATE} : {fixed_count:,}  (should be ~{len(bad_rows)})')
