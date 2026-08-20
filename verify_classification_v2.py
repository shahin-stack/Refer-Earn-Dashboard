"""
Verify classification matches user's exact specification:
- Repeat = at least one purchase on or before July 31, 2026
- New    = no purchase before Aug 1, 2026 (first purchase >= Aug 1 OR no purchase at all)
- Repeat + New must = 91,550
"""
import clickhouse_connect

client = clickhouse_connect.get_client(
    host='pdhsuv47ec.ap-south-1.aws.clickhouse.cloud',
    port=8443, username='default', password='ZFlujj9SA_Iei', secure=True
)

result = client.query("""
WITH
    -- All distinct R&E participants (normalize mobile)
    re AS (
        SELECT DISTINCT
            if(endsWith(customer_mobile_number, '.0'),
               substr(customer_mobile_number, 1, length(customer_mobile_number) - 2),
               customer_mobile_number) AS mob
        FROM refer_point_data
        WHERE customer_mobile_number != '' AND customer_mobile_number IS NOT NULL
    ),
    -- All mobiles that made at least one purchase on or before July 31 2026
    pre_aug_buyers AS (
        SELECT DISTINCT
            if(endsWith(customer_mobile, '.0'),
               substr(customer_mobile, 1, length(customer_mobile) - 2),
               customer_mobile) AS mob
        FROM sales_data
        WHERE parsed_date <= '2026-07-31'
          AND customer_mobile != ''
    ),
    -- Mobiles that made a purchase ONLY on/after Aug 1 (and not before)
    aug_only_buyers AS (
        SELECT DISTINCT
            if(endsWith(customer_mobile, '.0'),
               substr(customer_mobile, 1, length(customer_mobile) - 2),
               customer_mobile) AS mob
        FROM sales_data
        WHERE parsed_date >= '2026-08-01'
          AND customer_mobile != ''
    )
SELECT
    count()                                                    AS total_re_participants,
    countIf(mob IN (SELECT mob FROM pre_aug_buyers))           AS repeat_customers,
    countIf(mob NOT IN (SELECT mob FROM pre_aug_buyers))       AS new_customers,
    -- Sub-breakdown of New:
    countIf(mob NOT IN (SELECT mob FROM pre_aug_buyers)
        AND mob IN (SELECT mob FROM aug_only_buyers))          AS new_with_aug_purchase,
    countIf(mob NOT IN (SELECT mob FROM pre_aug_buyers)
        AND mob NOT IN (SELECT mob FROM aug_only_buyers))      AS new_no_purchase_yet,
    (SELECT count() FROM pre_aug_buyers)                       AS base_size
FROM re
""").result_rows[0]

total    = int(result[0])
repeat   = int(result[1])
new      = int(result[2])
new_aug  = int(result[3])
new_none = int(result[4])
base     = int(result[5])

print('=== Customer Classification Verification ===')
print(f'Total R&E Participants : {total:,}')
print(f'Repeat Customers       : {repeat:,}  ({repeat/total*100:.2f}%)')
print(f'New Customers          : {new:,}  ({new/total*100:.2f}%)')
print(f'  ↳ New who bought Aug+: {new_aug:,}')
print(f'  ↳ New with no purchase: {new_none:,}')
print(f'Repeat + New = {repeat+new:,}  ✓' if repeat+new == total else f'MISMATCH: {repeat+new:,} != {total:,}')
print(f'Pre-Aug base size      : {base:,}')
print(f'Repeat %  = {repeat/total*100:.2f}%')
print(f'New %     = {new/total*100:.2f}%')
