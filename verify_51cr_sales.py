import clickhouse_connect
import pandas as pd

client = clickhouse_connect.get_client(
    host='pdhsuv47ec.ap-south-1.aws.clickhouse.cloud', port=8443,
    username='default', password='ZFlujj9SA_Iei', secure=True
)

query = """
WITH valid_sales AS (
    SELECT 
        if(endsWith(customer_mobile, '.0'), substr(customer_mobile, 1, length(customer_mobile) - 2), customer_mobile) as mob,
        total_value,
        abs(toFloat64OrZero(point_redemption)) as redemption,
        invoice_number,
        parsed_date
    FROM sales_data
    WHERE parsed_date >= '2026-01-16'
    AND if(endsWith(customer_mobile, '.0'), substr(customer_mobile, 1, length(customer_mobile) - 2), customer_mobile) IN (
        SELECT if(endsWith(customer_mobile_number, '.0'), substr(customer_mobile_number, 1, length(customer_mobile_number) - 2), customer_mobile_number) FROM refer_point_data
    )
),
redeeming_customers AS (
    SELECT DISTINCT mob FROM valid_sales WHERE redemption > 0
),
redeemer_purchases AS (
    SELECT * FROM valid_sales 
    WHERE mob IN (SELECT mob FROM redeeming_customers)
)
SELECT 
    count(DISTINCT mob) as unique_customers,
    count() as total_transactions,
    sum(total_value) as total_sales_value,
    min(total_value) as min_purchase,
    max(total_value) as max_purchase,
    avg(total_value) as avg_transaction_value
FROM redeemer_purchases
"""
res = client.query(query).result_rows[0]
print(f"Unique Customers: {res[0]:,}")
print(f"Total Transactions: {res[1]:,}")
print(f"Total Sales Value: Rs {res[2]:,.2f}")
print(f"Min Purchase: Rs {res[3]:,.2f}")
print(f"Max Purchase: Rs {res[4]:,.2f}")
print(f"Avg Transaction Value: Rs {res[5]:,.2f}")

print("\nTop 5 Customers by Total Spend:")
top5_query = """
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
),
redeeming_customers AS (
    SELECT DISTINCT mob FROM valid_sales WHERE redemption > 0
)
SELECT 
    mob, 
    count() as transactions, 
    sum(total_value) as total_spend 
FROM valid_sales 
WHERE mob IN (SELECT mob FROM redeeming_customers)
GROUP BY mob
ORDER BY total_spend DESC
LIMIT 5
"""
top5 = client.query(top5_query).result_rows
for row in top5:
    print(f"Mobile {row[0][:4]}******: {row[1]} transactions, Rs {row[2]:,.2f}")
