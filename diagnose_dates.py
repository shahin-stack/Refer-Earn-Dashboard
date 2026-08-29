import clickhouse_connect

client = clickhouse_connect.get_client(
    host='pdhsuv47ec.ap-south-1.aws.clickhouse.cloud',
    port=8443, username='default', password='ZFlujj9SA_Iei', secure=True
)

# Check dates beyond Aug 2026
print('=== Dates beyond 2026-08-28 ===')
r = client.query(
    "SELECT start_date, count() as cnt FROM refer_point_data "
    "WHERE start_date > '2026-08-28' GROUP BY start_date ORDER BY start_date"
)
for row in r.result_rows:
    print(f'  {row[0]}  ->  {row[1]:,} rows')

print()
print('=== Total rows with date > 2026-08-28 ===')
r2 = client.query("SELECT count() FROM refer_point_data WHERE start_date > '2026-08-28'")
print(f'  {r2.result_rows[0][0]:,} rows')

print()
print('=== Sample rows with bad dates ===')
r3 = client.query(
    "SELECT customer_name, customer_mobile_number, campaign_name, bonus_points, start_date "
    "FROM refer_point_data WHERE start_date > '2026-08-28' LIMIT 10"
)
for row in r3.result_rows:
    print(f'  {row}')

print()
print('=== Min/Max/Total ===')
r4 = client.query('SELECT MIN(start_date), MAX(start_date), count() FROM refer_point_data')
print(f'  Min: {r4.result_rows[0][0]}, Max: {r4.result_rows[0][1]}, Total: {r4.result_rows[0][2]:,}')
