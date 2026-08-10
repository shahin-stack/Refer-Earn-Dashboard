import io
import sqlite3
import pandas as pd
import warnings
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

warnings.filterwarnings('ignore')

# ── Configuration ──────────────────────────────────────────────────────────────
SCOPES               = ['https://www.googleapis.com/auth/drive.readonly']
SERVICE_ACCOUNT_FILE = 'idyllic-pact-491410-q3-f01793b42fc1.json'

# The specific file to ingest
FILE_ID   = '17AflpBnJt-Wi1v5eRxXBhP5LXear0DLg'
FILE_NAME = 'Supabase Snippet Users with Phone Numbers up to 2026-02-10.csv'
MIME_TYPE = 'text/csv'

# Output database
DB_PATH   = 'eaas.db'
TABLE_NAME = 'eaas_users'

# ── Helpers ────────────────────────────────────────────────────────────────────

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)


def download_file(service, file_id):
    """Download a Drive file by ID and return a BytesIO buffer."""
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        print(f"  Downloading... {int(status.progress() * 100)}%", end='\r')
    print("  Download complete.          ")
    fh.seek(0)
    return fh


def main():
    print("=" * 60)
    print("  EAAS Supabase Data -> SQLite Ingestion")
    print(f"  File  : {FILE_NAME}")
    print(f"  DB    : {DB_PATH}")
    print(f"  Table : {TABLE_NAME}")
    print("=" * 60)

    # 1. Authenticate
    print("\n[1/4] Authenticating with Google Drive...")
    service = get_drive_service()
    print("  [OK] Authenticated")

    # 2. Download
    print(f"\n[2/4] Downloading file (ID: {FILE_ID})...")
    fh = download_file(service, FILE_ID)

    # 3. Parse CSV
    print("\n[3/4] Parsing CSV...")
    try:
        df = pd.read_csv(fh, encoding='utf-8')
    except UnicodeDecodeError:
        fh.seek(0)
        df = pd.read_csv(fh, encoding='latin-1')

    print(f"  [OK] {len(df):,} rows x {len(df.columns)} columns")
    print(f"  Columns: {list(df.columns)}")

    # 4. Load into SQLite
    print(f"\n[4/4] Writing to '{DB_PATH}' -> table '{TABLE_NAME}'...")
    conn = sqlite3.connect(DB_PATH)
    df.to_sql(TABLE_NAME, conn, if_exists='replace', index=False)
    conn.close()
    print(f"  [OK] Done - {len(df):,} rows loaded")

    # Quick verification
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
    count = cur.fetchone()[0]
    conn.close()

    print("\n" + "=" * 60)
    print(f"  [OK] Verification: {count:,} rows in '{TABLE_NAME}'")
    print(f"  Database saved: {DB_PATH}")
    print("=" * 60)


if __name__ == '__main__':
    main()
