import clickhouse_connect
client = clickhouse_connect.get_client(
    host='pdhsuv47ec.ap-south-1.aws.clickhouse.cloud', port=8443,
    username='default', password='ZFlujj9SA_Iei', secure=True
)
q = """
    WITH valid_sales AS (
        SELECT 
            if(endsWith(customer_mobile, '.0'), substr(customer_mobile, 1, length(customer_mobile) - 2), customer_mobile) as mob,
            total_value,
            abs(toFloat64OrZero(point_redemption)) as redemption
        FROM sales_data
        WHERE parsed_date >= '2026-01-16'
        AND if(endsWith(customer_mobile, '.0'), substr(customer_mobile, 1, length(customer_mobile) - 2), customer_mobile) IN (
            SELECT if(endsWith(customer_mobile_number, '.0'), substr(customer_mobile_number, 1, length(customer_mobile_number) - 2), customer_mobile_number) FROM refer_point_data
        )
    )
    SELECT 
        (SELECT count() FROM valid_sales WHERE redemption > 0) as redeemed_transactions,
        (SELECT sum(total_value) FROM valid_sales WHERE redemption > 0) as strict_redeemed_purchase_value,
        (SELECT sum(total_value) FROM valid_sales WHERE mob IN (SELECT DISTINCT mob FROM valid_sales WHERE redemption > 0)) as current_redeemed_purchase_value,
        (SELECT count(DISTINCT mob) FROM valid_sales WHERE redemption > 0) as unique_redeeming_customers
    FROM valid_sales LIMIT 1
"""
res = client.query(q).result_rows[0]
print(f"Redeemed transactions: {res[0]}")
print(f"Strict redeemed purchase value: {res[1]}")
print(f"Current redeemed purchase value: {res[2]}")
print(f"Unique redeeming customers: {res[3]}")
print(f"Strict avg per customer: {res[1] / res[3] if res[3] else 0}")
print(f"Strict avg per transaction: {res[1] / res[0] if res[0] else 0}")
