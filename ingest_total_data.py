import os
import sqlite3
import pandas as pd
import io
import warnings
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

warnings.filterwarnings('ignore')

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
SERVICE_ACCOUNT_FILE = 'idyllic-pact-491410-q3-f01793b42fc1.json'
DB_OUTPUT = 'total data.db'
SEARCH_RESULTS_FILE = 'search_results.json'

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def download_file(service, file_id, file_name, mime_type):
    """Download a Drive file and return a BytesIO buffer."""
    if mime_type == 'application/vnd.google-apps.spreadsheet':
        request = service.files().export_media(
            fileId=file_id, mimeType='text/csv')
    elif mime_type in (
        'text/csv',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    ):
        request = service.files().get_media(fileId=file_id)
    else:
        print(f"  ⚠ Skipping '{file_name}' – unsupported type: {mime_type}")
        return None

    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        print(f"  Downloading {int(status.progress() * 100)}%...", end='\r')
    print(f"  Download complete.          ")
    fh.seek(0)
    return fh

def load_into_db(fh, file_name, mime_type, conn):
    """Parse the buffer into a DataFrame and write to SQLite."""
    table_name = os.path.splitext(file_name)[0]
    table_name = "".join(c if c.isalnum() else '_' for c in table_name)
    table_name = table_name.strip('_')
    if not table_name:
        table_name = 'data_table'

    try:
        if mime_type in ('application/vnd.google-apps.spreadsheet', 'text/csv'):
            df = pd.read_csv(fh)
            df.to_sql(table_name, conn, if_exists='replace', index=False)
            print(f"  ✓ Loaded → table '{table_name}' ({len(df)} rows × {len(df.columns)} cols)")
        else:
            xl = pd.ExcelFile(fh)
            sheet_names = xl.sheet_names
            print(f"  Sheets found: {sheet_names}")

            for sheet in sheet_names:
                df = xl.parse(sheet)
                if df.empty:
                    print(f"  ⚠ Sheet '{sheet}' is empty – skipping.")
                    continue
                tname = table_name if len(sheet_names) == 1 else (
                    table_name + '_' + "".join(
                        c if c.isalnum() else '_' for c in str(sheet)
                    ).strip('_')
                )
                df.to_sql(tname, conn, if_exists='replace', index=False)
                print(f"  ✓ Loaded sheet '{sheet}' → table '{tname}' "
                      f"({len(df)} rows × {len(df.columns)} cols)")

    except Exception as e:
        print(f"  ✗ Failed to process '{file_name}': {e}")


def main():
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"ERROR: Service account file '{SERVICE_ACCOUNT_FILE}' not found.")
        return

    print("─" * 60)
    print("  Google Drive → SQLite Ingestion (Total Data)")
    print(f"  DB Output : {DB_OUTPUT}")
    print("─" * 60)

    try:
        service = get_drive_service()
    except Exception as e:
        print(f"  ✗ Auth failed: {e}")
        return

    with open(SEARCH_RESULTS_FILE, 'r', encoding='utf-8') as f:
        files = json.load(f)

    if not files:
        print("  No files found to process.")
        return

    conn = sqlite3.connect(DB_OUTPUT)

    for file in files:
        name = file['name']
        file_id = file['id']
        mime_type = file['mimeType']

        print(f"\n─ Processing: {name}")
        fh = download_file(service, file_id, name, mime_type)
        if fh is None:
            continue

        load_into_db(fh, name, mime_type, conn)

    conn.close()
    print("\n─" * 60)
    print("✓ Done!")
    print(f"  Data successfully written to {DB_OUTPUT}")
    print("─" * 60)

if __name__ == '__main__':
    main()
