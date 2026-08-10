# -*- coding: utf-8 -*-
import sqlite3
import sys

results = []

def log(msg=""):
    results.append(msg)

log("=== FAST AUDIT (pure SQL) ===")
log()

conn = sqlite3.connect('detailed_split.db')
conn.execute("ATTACH DATABASE 'monthly.db' AS mon")

# Row counts
r1 = conn.execute("SELECT COUNT(*) FROM Detailed_split_1").fetchone()[0]
r2 = conn.execute("SELECT COUNT(*) FROM Detailed_split_2").fetchone()[0]
log(f"Detailed_split_1 rows : {r1:,}")
log(f"Detailed_split_2 rows : {r2:,}")

total_members = conn.execute("SELECT COUNT(DISTINCT [Mobile Number]) FROM mon.r_f_monthly").fetchone()[0]
log(f"Unique members in monthly.db: {total_members:,}")
log()

# ── Total Point Redeemed (ABS of non-zero deduction) ─────────────────────
pts1 = conn.execute("""
    SELECT COALESCE(SUM(ABS(CAST([POINT REDUMPTION (DEDUCTION)] AS REAL))), 0)
    FROM Detailed_split_1
    WHERE CAST([POINT REDUMPTION (DEDUCTION)] AS REAL) != 0
""").fetchone()[0]

pts2 = conn.execute("""
    SELECT COALESCE(SUM(ABS(CAST([POINT REDUMPTION (DEDUCTION)] AS REAL))), 0)
    FROM Detailed_split_2
    WHERE CAST([POINT REDUMPTION (DEDUCTION)] AS REAL) != 0
""").fetchone()[0]

total_pts = pts1 + pts2
log(f"Points redeemed - split_1 : {pts1:,.2f}")
log(f"Points redeemed - split_2 : {pts2:,.2f}")
log(f"TOTAL Point Redeemed Value : {total_pts:,.2f}")
log(f"Dashboard shows            : 5,715,819")
log(f"Difference                 : {5715819 - total_pts:,.2f}")
log()

# ── Redeemed Purchase Value ───────────────────────────────────────────────
pv1 = conn.execute("""
    SELECT COALESCE(SUM(CAST([Total Value] AS REAL)), 0)
    FROM Detailed_split_1
    WHERE CAST([POINT REDUMPTION (DEDUCTION)] AS REAL) != 0
""").fetchone()[0]

pv2 = conn.execute("""
    SELECT COALESCE(SUM(CAST([Total Value] AS REAL)), 0)
    FROM Detailed_split_2
    WHERE CAST([POINT REDUMPTION (DEDUCTION)] AS REAL) != 0
""").fetchone()[0]

total_pv = pv1 + pv2
log(f"Redeemed Purchase Value - split_1 : {pv1:,.2f}")
log(f"Redeemed Purchase Value - split_2 : {pv2:,.2f}")
log(f"TOTAL Redeemed Purchase Value     : {total_pv:,.2f}")
log(f"Dashboard shows                   : 34,626,942")
log(f"Difference                        : {34626942 - total_pv:,.2f}")
log()

# ── Unique Redeemed Mobiles ───────────────────────────────────────────────
conn.execute("DROP TABLE IF EXISTS temp_red_mobs")
conn.execute("""
    CREATE TEMP TABLE temp_red_mobs AS
    SELECT DISTINCT REPLACE(TRIM(CAST([Customer Mobile] AS TEXT)), '.0', '') AS mob
    FROM Detailed_split_1
    WHERE CAST([POINT REDUMPTION (DEDUCTION)] AS REAL) != 0
    UNION
    SELECT DISTINCT REPLACE(TRIM(CAST([Customer Mobile] AS TEXT)), '.0', '') AS mob
    FROM Detailed_split_2
    WHERE CAST([POINT REDUMPTION (DEDUCTION)] AS REAL) != 0
""")
unique_redeemed = conn.execute("SELECT COUNT(*) FROM temp_red_mobs").fetchone()[0]
log(f"Unique Redeemed Mobiles (combined): {unique_redeemed:,}")
log(f"Dashboard shows                   : 11,273")
log()

# ── Derived Metrics ───────────────────────────────────────────────────────
disc_pct  = (total_pts / total_pv * 100) if total_pv > 0 else 0
avg_purch = total_pv / unique_redeemed if unique_redeemed > 0 else 0
avg_pts   = total_pts / unique_redeemed if unique_redeemed > 0 else 0

log(f"Loyalty Discount % (pts/purch*100) : {disc_pct:.4f}%  | Dashboard: 16.51%")
log(f"Avg Purchase Value (purch/redeemed): Rs {avg_purch:,.2f}  | Dashboard: Rs 3,072")
log(f"Avg Point Redemption (pts/redeemed): {avg_pts:,.2f}  | Dashboard: 507")
log()

# ── Also check what happens AFTER member filtering ────────────────────────
log("--- After filtering to VALID members only (joined with monthly.db) ---")
conn.execute("DROP TABLE IF EXISTS temp_valid_mobs")
conn.execute("""
    CREATE TEMP TABLE temp_valid_mobs AS
    SELECT DISTINCT REPLACE(TRIM(CAST([Mobile Number] AS TEXT)), '.0', '') AS mob
    FROM mon.r_f_monthly
""")

conn.execute("DROP TABLE IF EXISTS temp_red_valid")
conn.execute("""
    CREATE TEMP TABLE temp_red_valid AS
    SELECT REPLACE(TRIM(CAST([Customer Mobile] AS TEXT)), '.0', '') AS mob,
           ABS(CAST([POINT REDUMPTION (DEDUCTION)] AS REAL)) AS pts,
           CAST([Total Value] AS REAL) AS val
    FROM Detailed_split_1
    WHERE CAST([POINT REDUMPTION (DEDUCTION)] AS REAL) != 0
    UNION ALL
    SELECT REPLACE(TRIM(CAST([Customer Mobile] AS TEXT)), '.0', '') AS mob,
           ABS(CAST([POINT REDUMPTION (DEDUCTION)] AS REAL)) AS pts,
           CAST([Total Value] AS REAL) AS val
    FROM Detailed_split_2
    WHERE CAST([POINT REDUMPTION (DEDUCTION)] AS REAL) != 0
""")

row = conn.execute("""
    SELECT COUNT(DISTINCT r.mob), SUM(r.pts), SUM(r.val)
    FROM temp_red_valid r
    JOIN temp_valid_mobs v ON r.mob = v.mob
""").fetchone()

v_redeemed = row[0] or 0
v_pts      = row[1] or 0
v_pv       = row[2] or 0

v_disc  = (v_pts / v_pv * 100) if v_pv > 0 else 0
v_avpv  = v_pv / v_redeemed if v_redeemed > 0 else 0
v_avpt  = v_pts / v_redeemed if v_redeemed > 0 else 0

log(f"Valid-member redeemed count        : {v_redeemed:,}  | Dashboard: 11,273")
log(f"Valid-member pts redeemed          : {v_pts:,.2f}  | Dashboard: 5,715,819")
log(f"Valid-member purchase value        : {v_pv:,.2f}  | Dashboard: 34,626,942")
log(f"Valid-member Discount %            : {v_disc:.4f}%  | Dashboard: 16.51%")
log(f"Valid-member Avg Purchase Value    : Rs {v_avpv:,.2f}  | Dashboard: Rs 3,072")
log(f"Valid-member Avg Pts/customer      : {v_avpt:,.2f}  | Dashboard: 507")

conn.close()
log()
log("=== AUDIT COMPLETE ===")

output = "\n".join(results)
with open("audit_results.txt", "w", encoding="utf-8") as f:
    f.write(output)
print(output)
