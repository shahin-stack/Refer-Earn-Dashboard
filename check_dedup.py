import clickhouse_connect

client = clickhouse_connect.get_client(
    host='pdhsuv47ec.ap-south-1.aws.clickhouse.cloud',
    port=8443, username='default', password='ZFlujj9SA_Iei', secure=True
)

# Check Aug 9 count and table engine
before_aug9 = client.query("SELECT count() FROM refer_point_data WHERE start_date='2026-08-09'").result_rows[0][0]
print(f'Aug 9 rows before dedup: {int(before_aug9)}')

engine = client.query("SELECT engine FROM system.tables WHERE name='refer_point_data'").result_rows
print('Table engine:', engine)
