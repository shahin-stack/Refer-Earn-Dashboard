import pandas as pd

df = pd.read_excel('refer point data august 1-9 2026.xlsx', dtype=str)
print(f'Rows: {len(df)}')
print(f'Columns: {list(df.columns)}')
print()
print(df.head(5).to_string())
