"""
Test robust mobile normalization to see how many more matches we get.
Current: only strips trailing .0
New: handles 91 prefix, +91, spaces, dashes, .0
"""
import clickhouse_connect

client = clickhouse_connect.get_client(
    host='pdhsuv47ec.ap-south-1.aws.clickhouse.cloud',
    port=8443, username='default', password='ZFlujj9SA_Iei', secure=True
)

print('=== Sample raw mobiles from refer_point_data ===')
r = client.query("""
    SELECT customer_mobile_number, count() as cnt
    FROM refer_point_data
    WHERE customer_mobile_number != ''
    GROUP BY customer_mobile_number
    ORDER BY length(customer_mobile_number) DESC
    LIMIT 20
""").result_rows
for row in r:
    print(f'  [{len(str(row[0]))} chars] raw="{row[0]}"  count={row[1]}')

print()
print('=== Sample raw mobiles from sales_data ===')
r2 = client.query("""
    SELECT customer_mobile, count() as cnt
    FROM sales_data
    WHERE customer_mobile != ''
    GROUP BY customer_mobile
    ORDER BY length(customer_mobile) DESC
    LIMIT 20
""").result_rows
for row in r2:
    print(f'  [{len(str(row[0]))} chars] raw="{row[0]}"  count={row[1]}')

print()
print('=== Mobile length distribution in refer_point_data ===')
r3 = client.query("""
    SELECT
        length(replaceRegexpAll(toString(customer_mobile_number), '[^0-9]', '')) AS digit_len,
        count() AS cnt
    FROM refer_point_data
    WHERE customer_mobile_number != ''
    GROUP BY digit_len
    ORDER BY digit_len
""").result_rows
for row in r3:
    print(f'  {int(row[0])} digits: {int(row[1]):,} records')

print()
print('=== Mobile length distribution in sales_data ===')
r4 = client.query("""
    SELECT
        length(replaceRegexpAll(toString(customer_mobile), '[^0-9]', '')) AS digit_len,
        count() AS cnt
    FROM sales_data
    WHERE customer_mobile != ''
    GROUP BY digit_len
    ORDER BY digit_len
""").result_rows
for row in r4:
    print(f'  {int(row[0])} digits: {int(row[1]):,} records')
