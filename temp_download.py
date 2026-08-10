import json
import io
import os
import sqlite3
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
SERVICE_ACCOUNT_FILE = 'idyllic-pact-491410-q3-f01793b42fc1.json'
creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('drive', 'v3', credentials=creds)

query = "name contains 'Bonus point jan 1 to april 21'"
results = service.files().list(q=query, fields='files(id, name, mimeType)').execute()
files = results.get('files', [])
print(json.dumps(files, indent=2))

if files:
    file = files[0]
    file_id = file['id']
    name = file['name']
    mime_type = file['mimeType']
    
    print(f"Downloading {name}...")
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        print(f"Download {int(status.progress() * 100)}%.")
    
    fh.seek(0)
    print("Reading Excel...")
    xl = pd.ExcelFile(fh)
    print("Sheets:", xl.sheet_names)
    
    conn = sqlite3.connect('monthly.db')
    
    # We will clear the existing r_f_monthly_OG or just replace the whole DB?
    # Better to just load all sheets as tables.
    for sheet in xl.sheet_names:
        df = xl.parse(sheet)
        print(f"Sheet {sheet} columns: {list(df.columns)}")
        df.to_sql('r_f_monthly_OG', conn, if_exists='replace', index=False)
        print(f"Saved {sheet} to monthly.db table r_f_monthly_OG with {len(df)} rows.")
        break # Only process first sheet
    
    conn.close()
