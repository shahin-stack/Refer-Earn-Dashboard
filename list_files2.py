import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
SERVICE_ACCOUNT_FILE = 'idyllic-pact-491410-q3-f01793b42fc1.json'
FOLDER_ID = '1jxNkdbGMWRJ8QCv6plN8aKheUmg4A6Qf'

creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('drive', 'v3', credentials=creds)

query = "'" + FOLDER_ID + "' in parents and trashed=false"
results = service.files().list(q=query, fields='files(id, name, mimeType)').execute()
items = results.get('files', [])

with open('files_list.json', 'w', encoding='utf-8') as f:
    json.dump(items, f, indent=2)

print('Done. Saved', len(items), 'files to files_list.json')
for item in items:
    print(item['name'], '|', item['mimeType'])
