import pandas as pd

# Preview the Excel file structure
df = pd.read_excel('Bonus sep 1 to 20.xlsx', dtype=str)
print(f'Rows: {len(df):,}')
print(f'Columns: {list(df.columns)}')
print()
print(df.head(5).to_string())
