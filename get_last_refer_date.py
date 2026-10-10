import clickhouse_connect

CH_HOST     = 'pdhsuv47ec.ap-south-1.aws.clickhouse.cloud'
CH_PORT     = 8443
CH_USER     = 'default'
CH_PASSWORD = 'ZFlujj9SA_Iei'

client = clickhouse_connect.get_client(
    host=CH_HOST, port=CH_PORT,
    username=CH_USER, password=CH_PASSWORD,
    secure=True
)

max_date = client.query("SELECT MAX(start_date) FROM refer_point_data").result_rows[0][0]
print(f"LAST DATE FOR REFER_POINT_DATA: {max_date}")
