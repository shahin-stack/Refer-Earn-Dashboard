import sqlite3
import pandas as pd
conn = sqlite3.connect('eaas.db')
df = pd.read_sql_query("SELECT * FROM eaas_users LIMIT 1", conn)
for column in df.columns.tolist():
    print(column)
conn.close()
