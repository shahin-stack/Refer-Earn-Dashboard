import pandas as pd
df = pd.read_excel('Bonus Customer Report_export_1791525965418.xlsx', dtype=str)
print("Columns:", df.columns.tolist())
print(df.head(2).to_string())
