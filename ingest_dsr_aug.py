"""
Ingest 'dsr august 8-9 2026.xlsx' into ClickHouse sales_data table.
Filters applied:
  - REMOVE rows where Invoice Number contains 'SMC' or 'EI'
  - REMOVE rows where Branch is 'HEAD OFFICE' or 'UG SMART CHOICE'
"""

import pandas as pd
import clickhouse_connect
from datetime import datetime

# ── Config ─────────────────────────────────────────────────────────────────────
EXCEL_FILE  = 'dsr august 8-9 2026.xlsx'
SOURCE_FILE = 'dsr august 8-9 2026.xlsx'

CH_HOST     = 'pdhsuv47ec.ap-south-1.aws.clickhouse.cloud'
CH_PORT     = 8443
CH_USER     = 'default'
CH_PASSWORD = 'ZFlujj9SA_Iei'

# ── Read Excel ─────────────────────────────────────────────────────────────────
print(f"Reading {EXCEL_FILE}...")
df = pd.read_excel(EXCEL_FILE, dtype=str)
print(f"  Raw rows: {len(df)}")

# ── Filter 1: Remove SMC / EI in Invoice Number ────────────────────────────────
inv_col = 'Invoice Number'
mask_inv = df[inv_col].str.contains('SMC|EI', case=False, na=False)
print(f"  Rows with SMC/EI in Invoice Number (REMOVED): {mask_inv.sum()}")
df = df[~mask_inv]

# ── Filter 2: Remove HEAD OFFICE and UG SMART CHOICE branches ─────────────────
branch_col = 'Branch'
exclude_branches = ['HEAD OFFICE', 'UG SMART CHOICE']
mask_branch = df[branch_col].str.strip().str.upper().isin([b.upper() for b in exclude_branches])
print(f"  Rows with HEAD OFFICE / UG SMART CHOICE (REMOVED): {mask_branch.sum()}")
df = df[~mask_branch]
print(f"  Rows after filters: {len(df)}")

# ── Parse date (DD-MM-YYYY → YYYY-MM-DD) ──────────────────────────────────────
def parse_date(d):
    d = str(d).strip()
    for fmt in ('%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y'):
        try:
            return datetime.strptime(d, fmt).strftime('%Y-%m-%d')
        except:
            pass
    return '1970-01-01'

df['parsed_date'] = pd.to_datetime(df['Date'].apply(parse_date), format='%Y-%m-%d').dt.date

# ── Get current max uid from ClickHouse ────────────────────────────────────────
client = clickhouse_connect.get_client(
    host=CH_HOST, port=CH_PORT,
    username=CH_USER, password=CH_PASSWORD,
    secure=True
)
max_uid = client.query('SELECT max(uid) FROM sales_data').result_rows[0][0] or 0
print(f"  Current max uid in sales_data: {max_uid}")

# ── Build rows for insertion ───────────────────────────────────────────────────
df = df.reset_index(drop=True)
df['uid']             = [int(max_uid) + i + 1 for i in range(len(df))]
df['source_file']     = SOURCE_FILE
df['myg_online_coupon'] = ''
df['total_value']     = pd.to_numeric(df['Total Value'], errors='coerce').fillna(0.0)

# Map Excel → ClickHouse column names
col_map = {
    'Slno':                          'Slno',
    'Date':                          'Date',
    'Time':                          'Time',
    'Invoice Number':                'invoice_number',
    'Enq/Job No.':                   'enq_job_no',
    'RBM':                           'RBM',
    'BDM':                           'BDM',
    'Branch':                        'branch',
    'Staff Code':                    'staff_code',
    'Staff':                         'staff',
    'Customer Name':                 'customer_name',
    'Customer Mobile':               'customer_mobile',
    'Financier':                     'financier',
    'Finance':                       'finance',
    'Delivery Order No.':            'delivery_order_no',
    'Cash':                          'cash',
    'Debit Card':                    'debit_card',
    'Credit Card':                   'credit_card',
    'Benow':                         'benow',
    'Advance Receipt':               'advance_receipt',
    'Bharath QR':                    'bharath_qr',
    'Paytm QR':                      'paytm_qr',
    'Pine Labs QR':                  'pine_labs_qr',
    'UPI Cashback':                  'upi_cashback',
    'Card Reward':                   'card_reward',
    'Card Cashback':                 'card_cashback',
    'Gift Voucher':                  'gift_voucher',
    'Approved Credit':               'approved_credit',
    'EMI':                           'EMI',
    'Customer Type':                 'customer_type',
    'Exchange':                      'exchange',
    'Discount':                      'discount',
    'Indirect Discount':             'indirect_discount',
    'Buyback':                       'buyback',
    'Addition':                      'addition',
    'Deduction':                     'deduction',
    'POINT REDUMPTION (DEDUCTION)':  'point_redemption',
}

df = df.rename(columns=col_map)

# Fill NaN with empty string for all string columns except total_value
str_cols = [c for c in df.columns if c not in ('total_value', 'parsed_date', 'uid')]
for c in str_cols:
    if c in df.columns:
        df[c] = df[c].fillna('').astype(str).str.strip()

# Ordered columns matching ClickHouse table
ch_columns = [
    'Slno', 'Date', 'Time', 'invoice_number', 'enq_job_no', 'RBM', 'BDM',
    'branch', 'staff_code', 'staff', 'customer_name', 'customer_mobile',
    'financier', 'finance', 'delivery_order_no', 'cash', 'debit_card',
    'credit_card', 'benow', 'advance_receipt', 'bharath_qr', 'paytm_qr',
    'pine_labs_qr', 'upi_cashback', 'card_reward', 'card_cashback',
    'gift_voucher', 'approved_credit', 'EMI', 'customer_type',
    'total_value', 'exchange', 'discount', 'indirect_discount',
    'buyback', 'addition', 'deduction', 'point_redemption',
    'myg_online_coupon', 'source_file', 'parsed_date', 'uid'
]

# Only keep columns that exist
available = [c for c in ch_columns if c in df.columns]
insert_df = df[available]

print(f"\nSample after filter:")
print(insert_df[['Date', 'branch', 'invoice_number', 'customer_mobile', 'total_value']].head(5).to_string())
print(f"\nDistinct branches being inserted: {sorted(insert_df['branch'].unique().tolist())}")

# ── Insert into ClickHouse ─────────────────────────────────────────────────────
print(f"\nInserting {len(insert_df)} rows into sales_data...")
client.insert_df('sales_data', insert_df)
print(f"[OK] Done! {len(insert_df)} rows inserted into sales_data.")

# ── Verify ─────────────────────────────────────────────────────────────────────
count = client.query("SELECT count() FROM sales_data WHERE source_file = 'dsr august 8-9 2026.xlsx'").result_rows[0][0]
print(f"[OK] Verification: {count} rows in sales_data with source_file = 'dsr august 8-9 2026.xlsx'")
total = client.query("SELECT count() FROM sales_data").result_rows[0][0]
print(f"[OK] Total rows in sales_data: {total}")
