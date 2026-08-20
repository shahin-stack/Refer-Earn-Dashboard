"""
Check current state of ClickHouse data for dashboard reflection.
"""
import clickhouse_connect

client = clickhouse_connect.get_client(
    host='pdhsuv47ec.ap-south-1.aws.clickhouse.cloud',
    port=8443, username='default', password='ZFlujj9SA_Iei', secure=True
)

print('=== refer_point_data ===')
r = client.query("""
    SELECT
        count(distinct if(endsWith(customer_mobile_number,'.0'), substr(customer_mobile_number,1,length(customer_mobile_number)-2), customer_mobile_number)) as unique_customers,
        sum(bonus_points) as total_bonus,
        MIN(start_date) as earliest,
        MAX(start_date) as latest,
        count() as total_rows
    FROM refer_point_data
""").result_rows[0]
print(f'  Unique customers : {int(r[0]):,}')
print(f'  Total bonus pts  : {float(r[1]):,.2f}')
print(f'  Date range       : {r[2]} -> {r[3]}')
print(f'  Total rows       : {int(r[4]):,}')

print()
print('=== sales_data ===')
r2 = client.query("""
    SELECT
        count() as total_rows,
        MIN(parsed_date) as earliest,
        MAX(parsed_date) as latest
    FROM sales_data
""").result_rows[0]
print(f'  Total rows  : {int(r2[0]):,}')
print(f'  Date range  : {r2[1]} -> {r2[2]}')

print()
print('=== Customer classification (Repeat vs New) ===')
r3 = client.query("""
    WITH
    base AS (
        SELECT DISTINCT if(endsWith(customer_mobile,'.0'), substr(customer_mobile,1,length(customer_mobile)-2), customer_mobile) AS mob
        FROM sales_data WHERE parsed_date <= '2026-07-31' AND customer_mobile != ''
    ),
    re_participants AS (
        SELECT DISTINCT if(endsWith(customer_mobile_number,'.0'), substr(customer_mobile_number,1,length(customer_mobile_number)-2), customer_mobile_number) AS mob
        FROM refer_point_data WHERE customer_mobile_number != ''
    )
    SELECT
        count() AS total,
        countIf(mob IN (SELECT mob FROM base)) AS repeat_count,
        countIf(mob NOT IN (SELECT mob FROM base)) AS new_count,
        (SELECT count() FROM base) AS base_size
    FROM re_participants
""").result_rows[0]
print(f'  Total participants : {int(r3[0]):,}')
print(f'  Repeat customers   : {int(r3[1]):,}')
print(f'  New customers      : {int(r3[2]):,}')
print(f'  Base set size      : {int(r3[3]):,}')

print()
print('=== Aug 2026 Sales Summary ===')
r4 = client.query("""
    SELECT
        count(distinct if(endsWith(customer_mobile,'.0'), substr(customer_mobile,1,length(customer_mobile)-2), customer_mobile)) as unique_buyers,
        sum(total_value) as revenue,
        MIN(parsed_date), MAX(parsed_date)
    FROM sales_data
    WHERE parsed_date >= '2026-08-01'
""").result_rows[0]
print(f'  Unique buyers (Aug): {int(r4[0]):,}')
print(f'  Revenue (Aug)      : {float(r4[1]):,.2f}')
print(f'  Date range         : {r4[2]} -> {r4[3]}')
