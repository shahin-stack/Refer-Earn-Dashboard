import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
SERVICE_ACCOUNT_FILE = 'idyllic-pact-491410-q3-f01793b42fc1.json'

creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('drive', 'v3', credentials=creds)

query = "name contains '2020' or name contains '2021' or name contains '2022' or name contains '2023' or name contains '2024' or name contains '2025' or name contains '2026'"
results = service.files().list(
    q=query,
    fields='nextPageToken, files(id, name, mimeType)',
    pageSize=100
).execute()
items = results.get('files', [])

print(f"Found {len(items)} files:")
print("-" * 80)
for i, item in enumerate(items, 1):
    print(f"{i}. Name     : {item['name']}")
    print(f"   ID       : {item['id']}")
    print(f"   MimeType : {item['mimeType']}")
    print()

with open('search_results.json', 'w', encoding='utf-8') as f:
    json.dump(items, f, indent=2, ensure_ascii=False)
