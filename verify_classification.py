"""
Verify classification numbers with latest logic:
- Repeat = R&E participant who has purchase in sales_data BEFORE Aug 1, 2026
- New = R&E participant who has NO purchase in sales_data before Aug 1, 2026
"""
import clickhouse_connect

client = clickhouse_connect.get_client(
    host='pdhsuv47ec.ap-south-1.aws.clickhouse.cloud',
    port=8443, username='default', password='ZFlujj9SA_Iei', secure=True
)

CUTOFF = '2026-07-31'

# Current logic (same as serve.py)
r = client.query(f"""
    WITH
    base AS (
        SELECT DISTINCT if(endsWith(customer_mobile,'.0'), substr(customer_mobile,1,length(customer_mobile)-2), customer_mobile) AS mob
        FROM sales_data
        WHERE parsed_date <= '{CUTOFF}' AND customer_mobile != ''
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

print('=== Classification: Repeat = bought before Aug 1, New = did NOT ===')
print(f'  Total R&E participants: {int(r[0]):,}')
print(f'  Repeat customers      : {int(r[1]):,}  ({int(r[1])/int(r[0])*100:.2f}%)')
print(f'  New customers         : {int(r[2]):,}  ({int(r[2])/int(r[0])*100:.2f}%)')
print(f'  Pre-prog base size    : {int(r[3]):,}')

print()
print('=== New customers who have also made purchases AFTER Aug 1 ===')
r2 = client.query("""
    WITH
    base AS (
        SELECT DISTINCT if(endsWith(customer_mobile,'.0'), substr(customer_mobile,1,length(customer_mobile)-2), customer_mobile) AS mob
        FROM sales_data WHERE parsed_date <= '2026-07-31' AND customer_mobile != ''
    ),
    new_re AS (
        SELECT DISTINCT if(endsWith(customer_mobile_number,'.0'), substr(customer_mobile_number,1,length(customer_mobile_number)-2), customer_mobile_number) AS mob
        FROM refer_point_data WHERE customer_mobile_number != ''
        AND if(endsWith(customer_mobile_number,'.0'), substr(customer_mobile_number,1,length(customer_mobile_number)-2), customer_mobile_number)
            NOT IN (SELECT mob FROM base)
    ),
    aug_buyers AS (
        SELECT DISTINCT if(endsWith(customer_mobile,'.0'), substr(customer_mobile,1,length(customer_mobile)-2), customer_mobile) AS mob
        FROM sales_data WHERE parsed_date >= '2026-08-01' AND customer_mobile != ''
    )
    SELECT
        count() AS total_new,
        countIf(mob IN (SELECT mob FROM aug_buyers)) AS new_with_aug_purchase,
        countIf(mob NOT IN (SELECT mob FROM aug_buyers)) AS new_no_aug_purchase
    FROM new_re
""").result_rows[0]
print(f'  Total new customers          : {int(r2[0]):,}')
print(f'  New who bought in Aug+       : {int(r2[1]):,}')
print(f'  New who have NOT bought yet  : {int(r2[2]):,}')
