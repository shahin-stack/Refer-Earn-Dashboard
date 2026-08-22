"""
clarity_16859_redeemers.py
──────────────────────────
Explains and verifies:
  - 16,859  = Total Redeemed Count  (R&E participants who redeemed points ≥ 1 time)
  - ₹51,97,80,781 = Redeemed Purchase Value (ALL purchases by those 16,859 customers)

Exports a detailed CSV of all 16,859 customers.
"""

import os
import csv
import clickhouse_connect

# ── ClickHouse connection ────────────────────────────────────────────────────
client = clickhouse_connect.get_client(
    host    = os.environ.get('CLICKHOUSE_HOST', 'pdhsuv47ec.ap-south-1.aws.clickhouse.cloud'),
    port    = int(os.environ.get('CLICKHOUSE_PORT', 8443)),
    username= os.environ.get('CLICKHOUSE_USER', 'default'),
    password= os.environ.get('CLICKHOUSE_PASSWORD', 'ZFlujj9SA_Iei'),
    secure  = True
)

PROG_START = '2026-01-16'

# ── Mobile normalisation (same as serve.py) ──────────────────────────────────
def mob_norm(col):
    d = f"replaceRegexpAll(toString(coalesce({col}, '')), '[^0-9]', '')"
    return (
        f"multiIf("
        f"  length({d}) = 12 AND startsWith({d}, '91'), substr({d}, 3), "
        f"  length({d}) = 11 AND startsWith({d}, '0'),  substr({d}, 2), "
        f"  {d}"
        f")"
    )

mob_re = mob_norm('customer_mobile_number')
mob_s  = mob_norm('customer_mobile')

# ── STEP 1: Verify the headline numbers ─────────────────────────────────────
print("=" * 70)
print("STEP 1 — Reproducing dashboard headline numbers")
print("=" * 70)

verify_q = f"""
WITH valid_sales AS (
    SELECT
        {mob_s} AS mob,
        total_value,
        abs(toFloat64OrZero(point_redemption)) AS redemption
    FROM sales_data
    WHERE parsed_date >= '{PROG_START}'
      AND {mob_s} IN (
          SELECT {mob_re} FROM refer_point_data
          WHERE customer_mobile_number != ''
            AND length({mob_re}) = 10
      )
      AND customer_mobile != ''
      AND length({mob_s}) = 10
),
redeemers AS (
    SELECT DISTINCT mob FROM valid_sales WHERE redemption > 0
)
SELECT
    count(DISTINCT mob)                                                    AS total_buyers,
    (SELECT count() FROM redeemers)                                        AS redeemed_count,
    round(sum(redemption), 2)                                              AS total_pts_redeemed,
    (SELECT round(sum(total_value), 2) FROM valid_sales
     WHERE mob IN (SELECT mob FROM redeemers))                             AS redeemed_purch_val
FROM valid_sales
"""
row = client.query(verify_q).result_rows[0]
total_buyers, redeemed_count, total_pts, redeemed_sale = row
print(f"  Total Buyers (Purchase Count) : {int(total_buyers):>12,}")
print(f"  Redeemed Count (16,859 target): {int(redeemed_count):>12,}")
print(f"  Total Points Redeemed         : {float(total_pts):>15,.2f}")
print(f"  Redeemed Purchase Value       : Rs.{float(redeemed_sale):>14,.2f}")
print()

# ── STEP 2: Explanation ──────────────────────────────────────────────────────
print("=" * 70)
print("EXPLANATION")
print("=" * 70)
print("""
  HOW 16,859 IS COMPUTED:
    1. From sales_data (since 2026-01-16), find all R&E participants
       who made at least one purchase  --> 24,337 unique buyers
    2. Filter to those who had at least ONE row with point_redemption > 0
       --> 16,859 customers  (Total Redeemed Count)

  HOW Rs.51,97,80,781 IS COMPUTED:
    SUM of total_value for ALL purchases by those 16,859 customers.
    This INCLUDES their non-redemption bills too.
    It is the COMPLETE sale value contributed by the 16,859 redeemers,
    not just the redemption-specific transactions.

  So 16,859 customers out of 24,337 buyers redeemed at least once,
  and their combined purchases total Rs.51,97,80,781.
""")

# ── STEP 3: Per-customer detail for all 16,859 ──────────────────────────────
print("=" * 70)
print("STEP 3 — Per-customer breakdown for all 16,859 redeemers")
print("=" * 70)

detail_q = f"""
WITH
re_participants AS (
    SELECT DISTINCT {mob_re} AS mob
    FROM refer_point_data
    WHERE customer_mobile_number != ''
      AND length({mob_re}) = 10
),
valid_sales AS (
    SELECT
        {mob_s} AS mob,
        total_value,
        abs(toFloat64OrZero(point_redemption)) AS redemption,
        parsed_date
    FROM sales_data
    WHERE parsed_date >= '{PROG_START}'
      AND customer_mobile != ''
      AND length({mob_s}) = 10
      AND {mob_s} IN (SELECT mob FROM re_participants)
),
redeemers AS (
    SELECT DISTINCT mob FROM valid_sales WHERE redemption > 0
)
SELECT
    mob                                                     AS mobile,
    count()                                                 AS purchase_count,
    round(sum(total_value), 2)                              AS total_sale_value,
    round(sum(redemption), 2)                               AS total_pts_redeemed,
    round(sum(redemption) / sum(total_value) * 100, 2)      AS redemption_pct,
    round(avg(total_value), 2)                              AS avg_bill_value,
    min(parsed_date)                                        AS first_purchase,
    max(parsed_date)                                        AS last_purchase
FROM valid_sales
WHERE mob IN (SELECT mob FROM redeemers)
GROUP BY mob
ORDER BY total_sale_value DESC
"""

print("  Querying ClickHouse — may take 20-30 seconds...")
rows = client.query(detail_q).result_rows
print(f"  Got {len(rows):,} customer rows\n")

# Summary stats
total_sale   = sum(float(r[2]) for r in rows)
total_redeem = sum(float(r[3]) for r in rows)
total_txns   = sum(int(r[1]) for r in rows)

print(f"  VERIFICATION:")
print(f"     Customer count        : {len(rows):>10,}  (should be 16,859)")
print(f"     Total sale value      : Rs.{total_sale:>14,.2f}  (should be ~51,97,80,781)")
print(f"     Total pts redeemed    : {total_redeem:>14,.2f}  (should be ~94,20,138)")
print(f"     Total transactions    : {total_txns:>10,}")
print(f"     Avg sale per customer : Rs.{total_sale/len(rows) if rows else 0:>14,.2f}")
print()

# Top 20 by sale value
print("  Top 20 customers by total sale value:")
print(f"  {'Mobile':<13} {'Purchases':>9} {'Total Sale Rs.':>16} {'Pts Redeemed':>13} {'Redm%':>7} {'Avg Bill':>12}")
print("  " + "-" * 75)
for r in rows[:20]:
    mob, pc, sale, pts, pct, avg, fp, lp = r
    print(f"  {mob:<13} {int(pc):>9,} {float(sale):>16,.2f} {float(pts):>13,.2f} {float(pct):>7.2f}% {float(avg):>12,.2f}")

# ── STEP 4: Export CSV ───────────────────────────────────────────────────────
out_file = 'redeemer_customers_16859.csv'
with open(out_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Mobile', 'Purchase_Count', 'Total_Sale_Value', 'Total_Pts_Redeemed',
                     'Redemption_Pct', 'Avg_Bill_Value', 'First_Purchase', 'Last_Purchase'])
    for r in rows:
        writer.writerow([r[0], int(r[1]), float(r[2]), float(r[3]),
                         float(r[4]), float(r[5]), str(r[6]), str(r[7])])

print(f"\n  Exported to: {out_file}  ({len(rows):,} rows)")
print("=" * 70)
