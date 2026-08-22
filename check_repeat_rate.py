import clickhouse_connect

client = clickhouse_connect.get_client(
    host='pdhsuv47ec.ap-south-1.aws.clickhouse.cloud', port=8443,
    username='default', password='ZFlujj9SA_Iei', secure=True
)

query = """
WITH re_customers AS (
    SELECT DISTINCT if(endsWith(customer_mobile_number, '.0'), substr(customer_mobile_number, 1, length(customer_mobile_number) - 2), customer_mobile_number) as mob
    FROM refer_point_data
),
customer_purchases AS (
    SELECT 
        if(endsWith(customer_mobile, '.0'), substr(customer_mobile, 1, length(customer_mobile) - 2), customer_mobile) as mob,
        count(DISTINCT toDate(parsed_date)) as total_purchase_days,
        min(parsed_date) as first_purchase_date,
        max(parsed_date) as last_purchase_date
    FROM sales_data
    WHERE parsed_date >= '2026-01-16'
    AND if(endsWith(customer_mobile, '.0'), substr(customer_mobile, 1, length(customer_mobile) - 2), customer_mobile) IN (SELECT mob FROM re_customers)
    GROUP BY mob
)
SELECT 
    count() as total_purchasing_re_customers,
    countIf(total_purchase_days = 1) as single_purchase_customers,
    countIf(total_purchase_days > 1) as repeat_purchase_customers,
    avg(total_purchase_days) as avg_purchases_per_customer
FROM customer_purchases
"""
res = client.query(query).result_rows[0]
total = res[0]
single = res[1]
repeat = res[2]
avg_purch = res[3]

print(f"Total R&E Customers who made a purchase: {total:,}")
print(f"Customers with exactly 1 purchase: {single:,} ({(single/total)*100:.1f}%)")
print(f"Customers with 2+ purchases (Repeat): {repeat:,} ({(repeat/total)*100:.1f}%)")
print(f"Average purchases per R&E customer: {avg_purch:.2f}")
