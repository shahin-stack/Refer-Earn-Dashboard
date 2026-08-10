# sheets_config.py
# ──────────────────────────────────────────────────────────────────────────────
# Google Sheets Configuration for Refer & Earn Dashboard
#
# SETUP INSTRUCTIONS:
#   1. Create a Google Cloud Project at https://console.cloud.google.com
#   2. Enable the Google Sheets API
#   3. Create a Service Account and download the JSON key
#   4. Save the key as: credentials/service_account.json
#   5. Share your Google Sheet with the service account email (Editor access)
#   6. Paste your Google Sheet ID below (from the sheet URL)
# ──────────────────────────────────────────────────────────────────────────────

import os

# ── Your Google Sheet ID ──────────────────────────────────────────────────────
# Get this from the URL: https://docs.google.com/spreadsheets/d/THIS_PART/edit
SPREADSHEET_ID = "1Dh933ZoKOh0ssefiEwbxlevrC83c1jVPdSaIZRZwQeM"

# ── Sheet Tab Names ───────────────────────────────────────────────────────────
# These must match the exact tab names in your Google Sheet
SHEET_TABS = {
    "members"          : "Sheet1",             # R&E member list (Tab 1 = core performance metrics)
    "customer_profiles": "Customer_Profiles",  # DOB, district, anniversary (replaces eaas.db)
    "base_customers"   : "Base_Customers",     # Pre-programme mobile numbers (replaces total data.db)
}

# ── Credentials ───────────────────────────────────────────────────────────────
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "credentials", "service_account.json")

# ── Cache Settings ────────────────────────────────────────────────────────────
# How long (seconds) to cache sheet data before re-fetching
CACHE_TTL_SECONDS = 300   # 5 minutes

# ── Data Source Mode ──────────────────────────────────────────────────────────
# "sheets"   -> use Google Sheets (live data)
# "database" -> use local SQLite DB (offline fallback)
# "auto"     -> try Sheets first, fallback to DB if unavailable
DATA_SOURCE = "auto"
