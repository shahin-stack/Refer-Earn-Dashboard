import sqlite3, pandas as pd

# Check schema of detailed table
conn_det = sqlite3.connect('detailed_split.db')
tables = [r[0] for r in conn_det.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() if r[0] != 'sqlite_sequence']

print(f"Tables: {tables}")
print()

for t in tables[:1]:
    # Get schema
    cols = [r[1] for r in conn_det.execute(f'PRAGMA table_info("{t}")').fetchall()]
    print(f"Columns in {t}:")
    for c in cols:
        print(f"  {repr(c)}")
    
    # Sample rows
    df = pd.read_sql(f'SELECT * FROM "{t}" LIMIT 3', conn_det)
    print(f"\nSample rows:")
    for _, row in df.iterrows():
        for col in cols:
            print(f"  {col}: {repr(row[col])}")
        print("  ---")

conn_det.close()

# Now check hypothesis: sum ALL transactions for redeemed mobs (not just redemption rows)
conn_mon = sqlite3.connect('monthly.db')
og = pd.read_sql('SELECT [Mobile] FROM r_f_monthly_OG', conn_mon)
conn_mon.close()
og['mob'] = og['Mobile'].astype(str).str.strip().str.replace('.0', '', regex=False)
og_mobs = set(og['mob'].tolist())

conn_det = sqlite3.connect('detailed_split.db')
col = 'POINT REDUMPTION (DEDUCTION)'
all_parts = []
for t in tables:
    try:
        df = pd.read_sql(f'SELECT [Customer Mobile], [Total Value], [{col}] FROM "{t}"', conn_det)
        all_parts.append(df)
    except:
        pass
conn_det.close()

df_all = pd.concat(all_parts, ignore_index=True)
df_all['mob'] = df_all['Customer Mobile'].astype(str).str.strip().str.replace('.0', '', regex=False)
df_all[col] = pd.to_numeric(df_all[col], errors='coerce').fillna(0).abs()
df_all['Total Value'] = pd.to_numeric(df_all['Total Value'], errors='coerce').fillna(0)

# OG filter
df_og = df_all[df_all['mob'].isin(og_mobs)]

# Mobs who redeemed
df_red_rows = df_og[df_og[col] > 0]
redeemed_mobs = set(df_red_rows['mob'].tolist())
print(f"\nUnique mobs with redemption (OG): {len(redeemed_mobs)}")

# Hypothesis A: Sum only redemption rows Total Value (current logic)
print(f"[A] Sum only redemption rows Total Value: {df_red_rows['Total Value'].sum():,.0f}")

# Hypothesis B: Sum ALL rows for redeemed mobs
df_all_for_redeemers = df_og[df_og['mob'].isin(redeemed_mobs)]
print(f"[B] Sum ALL rows for redeemed mobs: {df_all_for_redeemers['Total Value'].sum():,.0f}")

print(f"\nCorrect target: 139,576,416")
