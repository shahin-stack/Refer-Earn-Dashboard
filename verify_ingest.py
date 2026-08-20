import clickhouse_connect

client = clickhouse_connect.get_client(
    host='pdhsuv47ec.ap-south-1.aws.clickhouse.cloud',
    port=8443, username='default', password='ZFlujj9SA_Iei', secure=True
)

count = client.query("SELECT count() FROM sales_data WHERE source_file = 'dsr august 8-9 2026.xlsx'").result_rows[0][0]
print(f'Rows for dsr august 8-9 2026.xlsx: {count:,}')

total = client.query('SELECT count() FROM sales_data').result_rows[0][0]
print(f'Total rows in sales_data        : {total:,}')

max_date = client.query('SELECT MAX(parsed_date) FROM sales_data').result_rows[0][0]
print(f'Latest date in sales_data       : {max_date}')
