import sqlite3, pandas as pd

conn_mon = sqlite3.connect('monthly.db')
og = pd.read_sql('SELECT [Mobile] FROM r_f_monthly_OG', conn_mon)
conn_mon.close()
og['mob'] = og['Mobile'].astype(str).str.strip().str.replace('.0', '', regex=False)
og_mobs = set(og['mob'].tolist())

conn_det = sqlite3.connect('detailed_split.db')
tables = [r[0] for r in conn_det.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() if r[0] != 'sqlite_sequence']
all_parts = []
for t in tables:
    try:
        df = pd.read_sql(f'SELECT [Customer Mobile], [Total Value], [POINT REDUMPTION (DEDUCTION)] FROM "{t}"', conn_det)
        all_parts.append(df)
    except:
        pass
conn_det.close()

df_all = pd.concat(all_parts, ignore_index=True)
df_all['mob'] = df_all['Customer Mobile'].astype(str).str.strip().str.replace('.0', '', regex=False)
col = 'POINT REDUMPTION (DEDUCTION)'
df_all[col] = pd.to_numeric(df_all[col], errors='coerce').fillna(0).abs()
df_all['Total Value'] = pd.to_numeric(df_all['Total Value'], errors='coerce').fillna(0)

# Filter to OG members only
df = df_all[df_all['mob'].isin(og_mobs)]

# NEW LOGIC
df_red = df[df[col] > 0]
redeemed_count = df_red['mob'].nunique()
point_redeemed = df_red[col].sum()
redeemed_mobs = set(df_red['mob'].tolist())
df_redeemers_all = df[df['mob'].isin(redeemed_mobs)]
redeemed_purch_v = df_redeemers_all['Total Value'].sum()

discount_pct = (point_redeemed / redeemed_purch_v) * 100 if redeemed_purch_v > 0 else 0
avg_purchase = redeemed_purch_v / redeemed_count if redeemed_count else 0
avg_points = point_redeemed / redeemed_count if redeemed_count else 0

results = f"""
=== NEW LOGIC RESULTS ===
Redeemed Count:          {redeemed_count:,}    (correct: 12,022)
Point Redeemed Value:    {point_redeemed:,.0f}  (correct: 60,54,020)
Redeemed Purchase Value: {redeemed_purch_v:,.0f}  (correct: 13,95,76,416)
Loyalty Discount %:      {discount_pct:.2f}%         (correct: 4%)
Avg Purchase Value:      {avg_purchase:,.0f}         (correct: 11,628)
Avg Point Redemption:    {avg_points:.0f}            (correct: 504)
"""
print(results)
with open('verify_fix.txt', 'w') as f:
    f.write(results)
print('Saved to verify_fix.txt')
