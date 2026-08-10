import os
import sqlite3
import pandas as pd
import io
import warnings
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

warnings.filterwarnings('ignore')

# ── Configuration ──────────────────────────────────────────────────────────────
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
SERVICE_ACCOUNT_FILE = 'idyllic-pact-491410-q3-f01793b42fc1.json'
FOLDER_ID = '1jxNkdbGMWRJ8QCv6plN8aKheUmg4A6Qf'

# Two output databases
DB_DETAILED  = 'detailed_split.db'   # for "Detailed split 1/2" files
DB_MONTHLY   = 'monthly.db'          # for "r&f monthly" file


def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)


def list_files_in_folder(service, folder_id):
    query = "'" + folder_id + "' in parents and trashed=false"
    results = service.files().list(
        q=query,
        fields="nextPageToken, files(id, name, mimeType)"
    ).execute()
    return results.get('files', [])


def classify_file(file_name):
    """
    Decide which DB a file belongs to based on its name.
    Returns 'detailed' or 'monthly'.
    """
    name_lower = file_name.lower()
    if 'detailed split' in name_lower or 'detailed_split' in name_lower:
        return 'detailed'
    elif 'monthly' in name_lower:
        return 'monthly'
    else:
        return 'other'


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
    # Generate a clean table name from the file name (no extension)
    table_name = os.path.splitext(file_name)[0]
    table_name = "".join(c if c.isalnum() else '_' for c in table_name)
    table_name = table_name.strip('_')
    if not table_name:
        table_name = 'data_table'

    try:
        if mime_type in (
            'application/vnd.google-apps.spreadsheet',
            'text/csv'
        ):
            df = pd.read_csv(fh)
        else:
            # Excel – try every sheet
            xl = pd.ExcelFile(fh)
            sheet_names = xl.sheet_names
            print(f"  Sheets found: {sheet_names}")

            for sheet in sheet_names:
                df = xl.parse(sheet)
                if df.empty:
                    print(f"  ⚠ Sheet '{sheet}' is empty – skipping.")
                    continue
                # Use table_name + sheet suffix if multiple sheets
                tname = table_name if len(sheet_names) == 1 else (
                    table_name + '_' + "".join(
                        c if c.isalnum() else '_' for c in str(sheet)
                    ).strip('_')
                )
                df.to_sql(tname, conn, if_exists='replace', index=False)
                print(f"  ✓ Loaded sheet '{sheet}' → table '{tname}' "
                      f"({len(df)} rows × {len(df.columns)} cols)")
            return  # already wrote all sheets above

        df.to_sql(table_name, conn, if_exists='replace', index=False)
        print(f"  ✓ Loaded → table '{table_name}' "
              f"({len(df)} rows × {len(df.columns)} cols)")

    except Exception as e:
        print(f"  ✗ Failed to process '{file_name}': {e}")


def main():
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"ERROR: Service account file '{SERVICE_ACCOUNT_FILE}' not found.")
        return

    print("─" * 60)
    print("  Google Drive → SQLite Ingestion")
    print(f"  Folder : {FOLDER_ID}")
    print(f"  DB 1   : {DB_DETAILED}  (Detailed Split files)")
    print(f"  DB 2   : {DB_MONTHLY}   (R&F Monthly files)")
    print("─" * 60)

    print("\n[1/3] Authenticating with Google Drive...")
    try:
        service = get_drive_service()
    except Exception as e:
        print(f"  ✗ Auth failed: {e}")
        return

    print("[2/3] Fetching file list...")
    try:
        files = list_files_in_folder(service, FOLDER_ID)
    except Exception as e:
        print(f"  ✗ Failed to list files: {e}")
        return

    if not files:
        print("  No files found in the folder.")
        return

    print(f"  Found {len(files)} file(s):\n")
    for f in files:
        category = classify_file(f['name'])
        db_dest = DB_DETAILED if category == 'detailed' else (
            DB_MONTHLY if category == 'monthly' else 'SKIPPED'
        )
        print(f"  • {f['name']}  →  {db_dest}")

    print("\n[3/3] Downloading & ingesting...\n")

    # Open both connections
    conn_detailed = sqlite3.connect(DB_DETAILED)
    conn_monthly  = sqlite3.connect(DB_MONTHLY)

    for file in files:
        name      = file['name']
        file_id   = file['id']
        mime_type = file['mimeType']
        category  = classify_file(name)

        if category == 'other':
            print(f"─ SKIPPED: {name} (could not classify)")
            continue

        conn = conn_detailed if category == 'detailed' else conn_monthly
        db   = DB_DETAILED   if category == 'detailed' else DB_MONTHLY

        print(f"─ Processing: {name}")
        print(f"  Category : {category.upper()} → {db}")

        fh = download_file(service, file_id, name, mime_type)
        if fh is None:
            continue

        load_into_db(fh, name, mime_type, conn)
        print()

    conn_detailed.close()
    conn_monthly.close()

    print("─" * 60)
    print("✓ Done!")
    print(f"  {DB_DETAILED} — Detailed Split data")
    print(f"  {DB_MONTHLY}  — R&F Monthly data")
    print("─" * 60)


if __name__ == '__main__':
    main()
