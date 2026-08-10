# sheets_connector.py
# ──────────────────────────────────────────────────────────────────────────────
# Google Sheets data connector with caching and DB fallback
# ──────────────────────────────────────────────────────────────────────────────

import os
import time
import pandas as pd
import sqlite3

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

from sheets_config import (
    SPREADSHEET_ID, SHEET_TABS, CREDENTIALS_FILE,
    CACHE_TTL_SECONDS, DATA_SOURCE
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

# ── In-memory cache ───────────────────────────────────────────────────────────
_cache = {}   # { tab_name: (dataframe, timestamp) }


def _get_gspread_client():
    """Authenticate and return a gspread client."""
    if not GSPREAD_AVAILABLE:
        raise RuntimeError("gspread not installed")
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(
            f"Service account credentials not found at: {CREDENTIALS_FILE}\n"
            "Please follow the setup instructions in sheets_config.py"
        )
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return gspread.authorize(creds)


def _sheet_to_df(tab_name: str) -> pd.DataFrame:
    """
    Fetch a Google Sheet tab and return as DataFrame.
    First row is treated as header.
    Uses cache; re-fetches only when TTL expires.
    """
    now = time.time()
    if tab_name in _cache:
        df, ts = _cache[tab_name]
        if now - ts < CACHE_TTL_SECONDS:
            return df

    client = _get_gspread_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    worksheet = spreadsheet.worksheet(tab_name)
    data = worksheet.get_all_values()

    if not data or len(data) < 2:
        df = pd.DataFrame()
    else:
        df = pd.DataFrame(data[1:], columns=data[0])

    _cache[tab_name] = (df, now)
    return df


def get_members_df(start_date: str = '', end_date: str = '') -> pd.DataFrame:
    """
    Returns R&E member DataFrame.
    Columns: CUSTOMER_NAME, MOBILE_NUMBER, CAMPAIGN_NAME, BONUS_POINTS, START_DATE
    Optionally filtered by START_DATE range (YYYY-MM-DD).
    Falls back to monthly.db if Sheets unavailable.
    """
    try:
        if _use_sheets():
            df = _sheet_to_df(SHEET_TABS["members"]).copy()
            df['BONUS_POINTS'] = pd.to_numeric(df.get('BONUS_POINTS', 0), errors='coerce').fillna(0)
            df['mob'] = df['MOBILE_NUMBER'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
            if start_date and end_date and 'START_DATE' in df.columns:
                df = df[
                    (df['START_DATE'].str[:10] >= start_date) &
                    (df['START_DATE'].str[:10] <= end_date)
                ]
            return df
    except Exception as e:
        print(f"[Sheets] members fallback to DB: {e}")

    # ── DB fallback ────────────────────────────────────────────────────────
    conn = sqlite3.connect('monthly.db')
    if start_date and end_date:
        df = pd.read_sql(
            "SELECT CUSTOMER_NAME, MOBILE_NUMBER, CAMPAIGN_NAME, BONUS_POINTS, START_DATE "
            "FROM r_f_monthly_OG WHERE SUBSTR(START_DATE,1,10) >= ? AND SUBSTR(START_DATE,1,10) <= ?",
            conn, params=(start_date, end_date)
        )
    else:
        df = pd.read_sql(
            "SELECT CUSTOMER_NAME, MOBILE_NUMBER, CAMPAIGN_NAME, BONUS_POINTS, START_DATE FROM r_f_monthly_OG",
            conn
        )
    conn.close()
    df['mob'] = df['MOBILE_NUMBER'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
    return df


def get_all_members_df() -> pd.DataFrame:
    """Returns all R&E members (no date filter) for classification logic."""
    return get_members_df()


def get_customer_profiles_df() -> pd.DataFrame:
    """
    Returns customer profiles DataFrame.
    Columns: firstname, lastname, user_phone, date_of_birth, wedding_anniversary, District, created_at
    Falls back to eaas.db if Sheets unavailable.
    """
    try:
        if _use_sheets():
            df = _sheet_to_df(SHEET_TABS["customer_profiles"]).copy()
            return df
    except Exception as e:
        print(f"[Sheets] customer_profiles fallback to DB: {e}")

    conn = sqlite3.connect('eaas.db')
    df = pd.read_sql("SELECT * FROM eaas_users", conn)
    conn.close()
    return df


def get_base_customers_set() -> set:
    """
    Returns the set of pre-programme mobile numbers.
    Falls back to total data.db if Sheets unavailable.
    """
    try:
        if _use_sheets():
            df = _sheet_to_df(SHEET_TABS["base_customers"]).copy()
            if not df.empty:
                col = df.columns[0]
                mobs = df[col].dropna().astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
                base = set(mobs.tolist())
                for noise in ('None', 'nan', ''):
                    base.discard(noise)
                return base
    except Exception as e:
        print(f"[Sheets] base_customers fallback to DB: {e}")

    # ── DB fallback ────────────────────────────────────────────────────────
    conn = sqlite3.connect('total data.db')
    total_tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    base = set()
    for (tname,) in total_tables:
        df = pd.read_sql(f'SELECT * FROM "{tname}"', conn)
        if not df.empty:
            col_name = str(df.columns[0]).strip()
            if col_name.endswith('.0'):
                col_name = col_name[:-2]
            if col_name not in ('None', 'nan', ''):
                base.add(col_name)
            mobs = df.iloc[:, 0].dropna().astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
            base.update(mobs.tolist())
    conn.close()
    for noise in ('None', 'nan', ''):
        base.discard(noise)
    return base


def invalidate_cache(tab_name: str = None):
    """Clear the cache for a specific tab or all tabs."""
    if tab_name:
        _cache.pop(tab_name, None)
    else:
        _cache.clear()


def _use_sheets() -> bool:
    """Decide whether to use Google Sheets based on DATA_SOURCE config."""
    if DATA_SOURCE == "sheets":
        return True
    if DATA_SOURCE == "database":
        return False
    # "auto" mode: use sheets only if credentials file exists
    return GSPREAD_AVAILABLE and os.path.exists(CREDENTIALS_FILE) and SPREADSHEET_ID != "YOUR_SPREADSHEET_ID_HERE"


def sheets_status() -> dict:
    """Returns connection status — used by /api/sheets-status endpoint."""
    cred_exists = os.path.exists(CREDENTIALS_FILE)
    sheet_id_set = SPREADSHEET_ID != "YOUR_SPREADSHEET_ID_HERE"
    connected = False
    error = None

    if cred_exists and sheet_id_set and GSPREAD_AVAILABLE:
        try:
            client = _get_gspread_client()
            sh = client.open_by_key(SPREADSHEET_ID)
            _ = sh.title
            connected = True
        except Exception as e:
            error = str(e)

    return {
        "gspread_installed" : GSPREAD_AVAILABLE,
        "credentials_file"  : cred_exists,
        "spreadsheet_id_set": sheet_id_set,
        "connected"         : connected,
        "data_source"       : DATA_SOURCE,
        "using_sheets"      : _use_sheets(),
        "error"             : error,
        "cached_tabs"       : list(_cache.keys()),
    }
