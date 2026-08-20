"""
Proof breakdown of the 54,666 New Customers:
- Who among them purchased after August 1?
- Who has no purchase at all?
"""
import clickhouse_connect
import pandas as pd

client = clickhouse_connect.get_client(
    host='pdhsuv47ec.ap-south-1.aws.clickhouse.cloud',
    port=8443, username='default', password='ZFlujj9SA_Iei', secure=True
)

print('=== Proof: Breakdown of 54,666 New Customers ===\n')

# Step 1: Get the 54,666 new customer mobiles
# (R&E participants with NO purchase before Aug 1)
result = client.query("""
WITH
    -- All R&E participants
    re AS (
        SELECT DISTINCT
            if(endsWith(customer_mobile_number,'.0'),
               substr(customer_mobile_number,1,length(customer_mobile_number)-2),
               customer_mobile_number) AS mob
        FROM refer_point_data
        WHERE customer_mobile_number != ''
    ),
    -- Mobiles with purchase before Aug 1 = Repeat
    repeat_base AS (
        SELECT DISTINCT
            if(endsWith(customer_mobile,'.0'),
               substr(customer_mobile,1,length(customer_mobile)-2),
               customer_mobile) AS mob
        FROM sales_data
        WHERE parsed_date <= '2026-07-31' AND customer_mobile != ''
    ),
    -- New customers = R&E but NOT in repeat_base
    new_customers AS (
        SELECT mob FROM re WHERE mob NOT IN (SELECT mob FROM repeat_base)
    ),
    -- Among new customers, who bought after Aug 1?
    aug_purchases AS (
        SELECT DISTINCT
            if(endsWith(customer_mobile,'.0'),
               substr(customer_mobile,1,length(customer_mobile)-2),
               customer_mobile) AS mob
        FROM sales_data
        WHERE parsed_date >= '2026-08-01' AND customer_mobile != ''
    )
SELECT
    count()                                                AS total_new_customers,
    countIf(mob IN (SELECT mob FROM aug_purchases))        AS purchased_after_aug1,
    countIf(mob NOT IN (SELECT mob FROM aug_purchases))    AS never_purchased_in_sales_data
FROM new_customers
""").result_rows[0]

total_new   = int(result[0])
bought_aug  = int(result[1])
never_bought = int(result[2])

print(f'Total New Customers (no purchase before Aug 1): {total_new:,}')
print(f'  Of these:')
print(f'    Who HAVE purchased in sales_data on/after Aug 1 : {bought_aug:,}')
print(f'    Who have NO purchase record in sales_data at all : {never_bought:,}')
print(f'  Total: {bought_aug + never_bought:,}')

print()
print('=== IMPORTANT CLARIFICATION ===')
print(f'The 54,666 are classified as "New" because they had')
print(f'NO purchase before August 1, 2026 -- they were NOT existing customers.')
print(f'Only {bought_aug:,} of them have made a purchase after Aug 1 in our sales data.')
print(f'The remaining {never_bought:,} joined R&E but have no confirmed purchase in sales_data yet.')

print()
print('=== Aug 1-9 purchases by R&E New Customers ===')
result2 = client.query("""
WITH
    re AS (
        SELECT DISTINCT
            if(endsWith(customer_mobile_number,'.0'),
               substr(customer_mobile_number,1,length(customer_mobile_number)-2),
               customer_mobile_number) AS mob
        FROM refer_point_data WHERE customer_mobile_number != ''
    ),
    repeat_base AS (
        SELECT DISTINCT
            if(endsWith(customer_mobile,'.0'),
               substr(customer_mobile,1,length(customer_mobile)-2),
               customer_mobile) AS mob
        FROM sales_data WHERE parsed_date <= '2026-07-31' AND customer_mobile != ''
    ),
    new_customers AS (
        SELECT mob FROM re WHERE mob NOT IN (SELECT mob FROM repeat_base)
    )
SELECT
    parsed_date,
    count(DISTINCT if(endsWith(customer_mobile,'.0'),
          substr(customer_mobile,1,length(customer_mobile)-2),
          customer_mobile)) AS unique_buyers,
    count() AS total_transactions,
    sum(total_value) AS revenue
FROM sales_data
WHERE parsed_date >= '2026-08-01'
  AND if(endsWith(customer_mobile,'.0'),
         substr(customer_mobile,1,length(customer_mobile)-2),
         customer_mobile) IN (SELECT mob FROM new_customers)
GROUP BY parsed_date
ORDER BY parsed_date
""")

print(f'{"Date":<15} {"Unique Buyers":>15} {"Transactions":>15} {"Revenue (Rs)":>18}')
print('-' * 65)
for row in result2.result_rows:
    print(f'{str(row[0]):<15} {int(row[1]):>15,} {int(row[2]):>15,} {float(row[3]):>18,.2f}')
