import sqlite3
import pandas as pd

DB_PATH = 'eaas.db'
TABLE_NAME = 'eaas_users'

conn = sqlite3.connect(DB_PATH)

# Row count
count = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
print(f"Total rows: {count:,}")

# Column info
df = pd.read_sql(f"SELECT * FROM {TABLE_NAME} LIMIT 5", conn)
print(f"\nColumns ({len(df.columns)}):")
for col in df.columns:
    print(f"  - {col}")

print("\nFirst 5 rows:")
print(df.to_string())

conn.close()
