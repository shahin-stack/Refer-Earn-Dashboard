import sqlite3, pandas as pd

# --- Check OG members ---
conn_mon = sqlite3.connect('monthly.db')
og = pd.read_sql('SELECT [Mobile], [Sum of Point] FROM r_f_monthly_OG', conn_mon)
conn_mon.close()
og['mob'] = og['Mobile'].astype(str).str.strip().str.replace('.0', '', regex=False)
og_mobs = set(og['mob'].tolist())
print(f'OG unique members: {len(og_mobs)}')
print(f'Sample OG mobs: {sorted(list(og_mobs))[:5]}')

# --- Check detailed_split tables ---
conn_det = sqlite3.connect('detailed_split.db')
tables = [r[0] for r in conn_det.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() if r[0] != 'sqlite_sequence']

all_rows = []
for t in tables:
    try:
        df = pd.read_sql(f'SELECT [Customer Mobile], [Total Value], [POINT REDUMPTION (DEDUCTION)] FROM "{t}"', conn_det)
        all_rows.append(df)
    except Exception as e:
        print(f'Error in {t}: {e}')
conn_det.close()

df_all = pd.concat(all_rows, ignore_index=True)
df_all['mob'] = df_all['Customer Mobile'].astype(str).str.strip().str.replace('.0', '', regex=False)
col = 'POINT REDUMPTION (DEDUCTION)'
df_all[col] = pd.to_numeric(df_all[col], errors='coerce').fillna(0).abs()
df_all['Total Value'] = pd.to_numeric(df_all['Total Value'], errors='coerce').fillna(0)

print(f'Unique mobs in detailed: {df_all["mob"].nunique()}')
print(f'Sample detailed mobs: {sorted(df_all["mob"].unique().tolist())[:5]}')

# Without OG filter
df_red_all = df_all[df_all[col] > 0]
print(f'\n--- UNFILTERED ---')
print(f'Redeemed mobs: {df_red_all["mob"].nunique()}')
print(f'Point Redeemed: {df_red_all[col].sum():,.0f}')
print(f'Purchase Value: {df_red_all["Total Value"].sum():,.0f}')

# With OG filter
df_og = df_all[df_all['mob'].isin(og_mobs)]
df_red_og = df_og[df_og[col] > 0]
print(f'\n--- OG FILTERED ---')
print(f'Redeemed mobs: {df_red_og["mob"].nunique()}')
print(f'Point Redeemed: {df_red_og[col].sum():,.0f}')
print(f'Purchase Value: {df_red_og["Total Value"].sum():,.0f}')

# Check overlap
matched = og_mobs.intersection(set(df_all['mob'].tolist()))
print(f'\nOG mobs matched in detailed: {len(matched)}')
print(f'OG mobs NOT found in detailed: {len(og_mobs) - len(matched)}')

# Check a sample OG mob in detailed
sample_mob = sorted(list(og_mobs))[0]
print(f'\nLooking for OG mob "{sample_mob}" in detailed...')
found = df_all[df_all['mob'] == sample_mob]
print(f'Found {len(found)} rows for this mob in detailed')
