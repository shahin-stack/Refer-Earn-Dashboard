"""
Run full classification with robust mobile normalization.
Key findings:
- refer_point_data: all 10-digit mobiles (clean)
- sales_data: mostly 10-digit, but 90 records are 12-digit (91 prefix), 47 are 11-digit

Normalization:
  1. Extract digits only (removes +, spaces, dashes, .0)
  2. If 12 digits starting with 91 → strip first 2
  3. If 11 digits starting with 0  → strip first 1
  4. Result = 10-digit mobile
"""
import clickhouse_connect

client = clickhouse_connect.get_client(
    host='pdhsuv47ec.ap-south-1.aws.clickhouse.cloud',
    port=8443, username='default', password='ZFlujj9SA_Iei', secure=True
)

# Robust normalization expression
def norm(col):
    d = f"replaceRegexpAll(toString(coalesce({col},'')), '[^0-9]', '')"
    return (
        f"multiIf("
        f"length({d})=12 AND startsWith({d},'91'), substr({d},3),"
        f"length({d})=11 AND startsWith({d},'0'),  substr({d},2),"
        f"{d})"
    )

re_mob  = norm('customer_mobile_number')
sal_mob = norm('customer_mobile')

result = client.query(f"""
WITH
    -- All unique R&E participant mobiles (normalized to 10 digits)
    re_participants AS (
        SELECT DISTINCT {re_mob} AS mob
        FROM refer_point_data
        WHERE customer_mobile_number != ''
          AND length({re_mob}) = 10
    ),
    -- Mobiles with at least one purchase BEFORE August 1, 2026 (Repeat)
    repeat_base AS (
        SELECT DISTINCT {sal_mob} AS mob
        FROM sales_data
        WHERE parsed_date <= '2026-07-31'
          AND customer_mobile != ''
          AND length({sal_mob}) = 10
    ),
    -- Mobiles with at least one purchase ON/AFTER August 1, 2026
    aug_buyers AS (
        SELECT DISTINCT {sal_mob} AS mob
        FROM sales_data
        WHERE parsed_date >= '2026-08-01'
          AND customer_mobile != ''
          AND length({sal_mob}) = 10
    )
SELECT
    count()                                                              AS total_participants,
    countIf(mob IN (SELECT mob FROM repeat_base))                        AS repeat_count,
    countIf(mob NOT IN (SELECT mob FROM repeat_base)
        AND mob IN (SELECT mob FROM aug_buyers))                          AS new_count,
    countIf(mob NOT IN (SELECT mob FROM repeat_base)
        AND mob NOT IN (SELECT mob FROM aug_buyers))                      AS no_purchase_count,
    (SELECT count() FROM repeat_base)                                     AS base_size
FROM re_participants
""").result_rows[0]

total = int(result[0])
repeat = int(result[1])
new = int(result[2])
no_purch = int(result[3])
base = int(result[4])

print('=== Classification with ROBUST mobile normalization ===')
print(f'Total R&E Participants : {total:,}')
print(f'Repeat Customers       : {repeat:,}  ({repeat/total*100:.2f}%)')
print(f'New Customers          : {new:,}  ({new/total*100:.2f}%)')
print(f'No Purchase Yet        : {no_purch:,}  ({no_purch/total*100:.2f}%)')
print(f'Repeat + New + NoPurch : {repeat+new+no_purch:,}  (check: {"OK" if repeat+new+no_purch==total else "MISMATCH"})')
print(f'Pre-Aug1 base size     : {base:,}')
