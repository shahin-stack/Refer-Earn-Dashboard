import requests
import pandas as pd
import io

SHEET_ID = "1Dh933ZoKOh0ssefiEwbxlevrC83c1jVPdSaIZRZwQeM"
GID = "0"

url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"
print(f"Fetching: {url}")

try:
    r = requests.get(url, timeout=15)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        df = pd.read_csv(io.StringIO(r.text))
        print(f"\nShape: {df.shape[0]} rows x {df.shape[1]} columns")
        print(f"\nColumns:\n{list(df.columns)}")
        print(f"\nFirst 5 rows:")
        print(df.head(5).to_string(index=False))
    else:
        print("Sheet is not publicly accessible or URL is wrong.")
        print(r.text[:300])
except Exception as e:
    print(f"Error: {e}")
