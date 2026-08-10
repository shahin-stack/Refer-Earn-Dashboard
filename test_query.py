import clickhouse_connect

client = clickhouse_connect.get_client(
    host='pdhsuv47ec.ap-south-1.aws.clickhouse.cloud',
    port=8443,
    username='default',
    password='ZFlujj9SA_Iei',
    secure=True
)

query = """
WITH valid_sales AS (
    SELECT 
        replaceRegexpOne(customer_mobile, '\\\\.0$', '') as mob, 
        total_value, 
        abs(toFloat64OrZero(point_redemption)) as redemption 
    FROM sales_data 
    WHERE parsed_date >= '2026-01-01' 
    AND replaceRegexpOne(customer_mobile, '\\\\.0$', '') IN (
        SELECT replaceRegexpOne(customer_mobile_number, '\\\\.0$', '') FROM refer_point_data
    )
), 
redeemers AS (
    SELECT DISTINCT mob FROM valid_sales WHERE redemption > 0
) 
SELECT 
    count(distinct mob) as purchase_count, 
    (SELECT count() FROM redeemers) as redeemed_count, 
    sum(redemption) as point_redeemed_value, 
    (SELECT sum(total_value) FROM valid_sales WHERE mob IN (SELECT mob FROM redeemers)) as redeemed_purchase_value 
FROM valid_sales
"""

print(client.query(query).result_rows)
