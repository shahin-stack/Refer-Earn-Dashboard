import sqlite3
import pandas as pd

print("Loading Detailed DB...")
conn_detailed = sqlite3.connect('detailed_split.db')
query = """
SELECT [Customer Mobile], [Invoice Number]
FROM Detailed_split_1
UNION ALL
SELECT [Customer Mobile], [Invoice Number]
FROM Detailed_split_2
"""
df_detailed = pd.read_sql(query, conn_detailed)
conn_detailed.close()

print("Loading Monthly DB...")
conn_monthly = sqlite3.connect('monthly.db')
df_monthly = pd.read_sql("SELECT [Mobile Number] FROM r_f_monthly", conn_monthly)
conn_monthly.close()

# Clean mobile numbers
df_detailed['Customer Mobile'] = pd.to_numeric(df_detailed['Customer Mobile'], errors='coerce').fillna(0).astype('int64').astype(str)
df_monthly['Mobile Number'] = pd.to_numeric(df_monthly['Mobile Number'], errors='coerce').fillna(0).astype('int64').astype(str)

valid_mobiles = set(df_monthly['Mobile Number'].unique())
valid_mobiles.discard('0')

# Filter
df_merged = df_detailed[df_detailed['Customer Mobile'].isin(valid_mobiles)]

print(f"\nTotal Matching Row Count (what I previously reported): {len(df_merged):,}")
print(f"Total Unique Customers (Mobile Numbers) in both files: {df_merged['Customer Mobile'].nunique():,}")
print(f"Total Unique Invoices (Purchases) for matching customers: {df_merged['Invoice Number'].nunique():,}")
