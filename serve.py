from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
import sqlite3
import pandas as pd
import os
import json
from sheets_connector import (
    get_members_df, get_all_members_df,
    get_customer_profiles_df, get_base_customers_set,
    invalidate_cache, sheets_status
)

app = Flask(__name__, static_folder='.', static_url_path='')

# -----------------------------------------------------------------------
# All dashboard metrics are now fetched live from ClickHouse.
# Refer & Earn programme data is up to date as of the last ingest.
# -----------------------------------------------------------------------

def get_db_connection(db_name):
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return send_from_directory('.', 'dashboard.html')


@app.route('/api/sheets-status')
def api_sheets_status():
    """Returns Google Sheets connection status for the dashboard."""
    return jsonify(sheets_status())


@app.route('/api/cache-refresh', methods=['POST'])
def api_cache_refresh():
    """Force-clear the Google Sheets cache so next request re-fetches live data."""
    invalidate_cache()
    return jsonify({'ok': True, 'message': 'Cache cleared. Next request will fetch fresh data from Google Sheets.'})


@app.route('/download/redeemer-customers')
def download_redeemer_excel():
    """Serve the pre-generated redeemer customers Excel as a browser download."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'redeemer_customers_16859.xlsx')
    return send_file(path, as_attachment=True, download_name='redeemer_customers_16859.xlsx')

def get_ch_client():
    import clickhouse_connect
    return clickhouse_connect.get_client(
        host=os.environ.get('CLICKHOUSE_HOST', 'pdhsuv47ec.ap-south-1.aws.clickhouse.cloud'),
        port=int(os.environ.get('CLICKHOUSE_PORT', 8443)),
        username=os.environ.get('CLICKHOUSE_USER', 'default'),
        password=os.environ.get('CLICKHOUSE_PASSWORD', 'ZFlujj9SA_Iei'),
        secure=True
    )

@app.route('/api/dashboard')
def dashboard_metrics():
    start_date = request.args.get('start', '')
    end_date   = request.args.get('end', '')

    try:
        client = get_ch_client()
    except Exception as e:
        print("Clickhouse connection error:", e)
        return jsonify({"error": "DB connection failed"}), 500

    is_full_range = False
    date_filter = "1=1"
    master_date_filter = ""
    if not start_date or not end_date:
        is_full_range = True
        date_filter = "parsed_date >= '2026-01-16'"  # programme start date
    else:
        from datetime import datetime
        try:
            sd = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y-%m-%d')
            ed = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y-%m-%d')
            date_filter = f"parsed_date >= '{sd}' AND parsed_date <= '{ed}'"
            master_date_filter = f"WHERE start_date >= '{sd}' AND start_date <= '{ed}'"
        except Exception:
            return jsonify({"error": "Invalid date format"}), 400

    master_query = f"""
        SELECT 
            count(distinct if(endsWith(customer_mobile_number, '.0'), substr(customer_mobile_number, 1, length(customer_mobile_number) - 2), customer_mobile_number)) as total_customers,
            sum(bonus_points) as total_bonus
        FROM refer_point_data
        {master_date_filter}
    """
    try:
        master_res = client.query(master_query).result_rows[0]
        master_total_customer_count = int(master_res[0])
        master_total_bonus_point_given = float(master_res[1])
    except Exception as e:
        print("Clickhouse master query error:", e)
        master_total_customer_count = 0
        master_total_bonus_point_given = 0.0

    # Only sales / redemptions made ON or AFTER the customer's refer_point_data
    # date are counted (see _re_sales_ctes), and only those inside the
    # referral-point validity window (see _re_window_ctes). Point Redeemed
    # Value is capped at the referral points actually available (FIFO).
    # When a date filter is applied, we restrict purchases to the exact cohort 
    # of customers whose start_date in refer_point_data falls in the selected date range.
    cohort_filter = ""
    if not is_full_range:
        mob_re = _normalize_mob_expr('customer_mobile_number')
        cohort_filter = f"AND mob IN (SELECT {mob_re} FROM refer_point_data WHERE start_date >= '{sd}' AND start_date <= '{ed}')"
    else:
        sd, ed = '2026-01-16', '2100-12-31'   # programme start → open end

    try:
        m = _windowed_re_metrics(client, sd, ed, scope_filter=cohort_filter)
        range_purchase_count   = m['purchase_count']
        range_redeemed_count   = m['redeemed_count']
        range_point_redeemed   = m['point_redeemed_value']
        range_redeemed_purch_v = m['redeemed_purchase_value']
    except Exception as e:
        print("Clickhouse range query error:", e)
        range_purchase_count = 0
        range_redeemed_count = 0
        range_point_redeemed = 0.0
        range_redeemed_purch_v = 0.0

    if range_redeemed_purch_v > 0:
        range_discount_pct = (range_point_redeemed / range_redeemed_purch_v) * 100
        range_avg_purchase = range_redeemed_purch_v / range_redeemed_count if range_redeemed_count else 0
        range_avg_points   = range_point_redeemed / range_redeemed_count if range_redeemed_count else 0
    else:
        range_discount_pct = 0
        range_avg_purchase = 0
        range_avg_points   = 0

    return jsonify({
        "master_stats": {
            "total_customer_count": master_total_customer_count,
            "total_bonus_point_given": master_total_bonus_point_given
        },
        "range_stats": {
            "purchase_count":          range_purchase_count,
            "redeemed_count":          range_redeemed_count,
            "point_redeemed_value":    range_point_redeemed,
            "redeemed_purchase_value": range_redeemed_purch_v,
            "loyalty_discount_pct":    round(range_discount_pct, 2),
            "avg_purchase_value":      round(range_avg_purchase, 2),
            "avg_loyalty_redemption":  round(range_avg_points, 2)
        },
        "is_full_range": is_full_range
    })


@app.route('/api/daily-customer-trend')
def daily_customer_trend():
    start_date = request.args.get('start', '')
    end_date   = request.args.get('end', '')

    try:
        client = get_ch_client()

        date_filter = ""
        if start_date and end_date:
            date_filter = f"WHERE start_date >= '{start_date}' AND start_date <= '{end_date}'"

        query = f"""
            SELECT
                start_date as date,
                count(distinct if(
                    endsWith(customer_mobile_number, '.0'),
                    substr(customer_mobile_number, 1, length(customer_mobile_number) - 2),
                    customer_mobile_number
                )) as unique_customers
            FROM refer_point_data
            {date_filter}
            GROUP BY start_date
            ORDER BY start_date ASC
        """
        result = client.query(query)
        labels = [str(row[0]) for row in result.result_rows]
        data   = [int(row[1]) for row in result.result_rows]
        return jsonify({'labels': labels, 'data': data})

    except Exception as e:
        print("daily-customer-trend error:", e)
        # Fallback to Google Sheets / monthly.db
        try:
            df = get_all_members_df()
            if 'START_DATE' in df.columns:
                df['date'] = df['START_DATE'].astype(str).str[:10]
            elif 'start_date' in df.columns:
                df['date'] = df['start_date'].astype(str).str[:10]
            else:
                return jsonify({'labels': [], 'data': []})

            if start_date and end_date:
                df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]

            mob_col = 'MOBILE_NUMBER' if 'MOBILE_NUMBER' in df.columns else 'Mobile'
            trend = df.groupby('date')[mob_col].nunique().reset_index()
            trend.columns = ['date', 'count']
            trend = trend.sort_values('date')
            return jsonify({'labels': trend['date'].tolist(), 'data': trend['count'].tolist()})
        except Exception as e2:
            print("Fallback trend error:", e2)
            return jsonify({'labels': [], 'data': []})

@app.route('/api/age-report')
def age_report():
    from datetime import date, datetime
    today = date.today()
    start_date = request.args.get('start', '')
    end_date   = request.args.get('end', '')

    AGE_BANDS = [
        ('0-10',      0,   10),
        ('11-16',    11,   16),
        ('17-20',    17,   20),
        ('21-25',    21,   25),
        ('26-30',    26,   30),
        ('31-40',    31,   40),
        ('41-50',    41,   50),
        ('51-60',    51,   60),
        ('Above 60', 61, 9999),
    ]
    counts = {band[0]: 0 for band in AGE_BANDS}

    try:
        client = get_ch_client()
        date_filter = ""
        if start_date and end_date:
            date_filter = f"AND substr(created_at, 1, 10) >= '{start_date}' AND substr(created_at, 1, 10) <= '{end_date}'"
        query = f"""
            SELECT date_of_birth FROM loyalty_user_data
            WHERE date_of_birth != '' {date_filter}
        """
        result = client.query(query)
        dobs = [row[0] for row in result.result_rows]
    except Exception as e:
        print("age-report CH error:", e)
        try:
            profiles_df = get_customer_profiles_df()
            filtered = profiles_df[profiles_df['date_of_birth'].notna() & (profiles_df['date_of_birth'].astype(str).str.strip() != '')]
            if start_date and 'created_at' in filtered.columns:
                filtered = filtered[filtered['created_at'].astype(str).str[:10] >= start_date]
            if end_date and 'created_at' in filtered.columns:
                filtered = filtered[filtered['created_at'].astype(str).str[:10] <= end_date]
            dobs = filtered['date_of_birth'].tolist()
        except Exception as e2:
            return jsonify({'error': str(e2)}), 500

    skipped = 0
    for dob_str in dobs:
        dob_str = str(dob_str).strip()
        dob = None
        for fmt in ('%d-%m-%Y', '%Y-%m-%d', '%Y-%m-%d %H:%M:%S'):
            try:
                dob = datetime.strptime(dob_str[:len(fmt.replace('%d','00').replace('%m','00').replace('%Y','0000').replace('%H','00').replace('%M','00').replace('%S','00'))], fmt).date()
                break
            except:
                pass
        if dob is None or dob > today:
            skipped += 1
            continue
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        for label, lo, hi in AGE_BANDS:
            if lo <= age <= hi:
                counts[label] += 1
                break

    total = sum(counts.values())
    bands_list = [{'age_group': label, 'count': counts[label]} for label, _, _ in AGE_BANDS]
    return jsonify({'bands': bands_list, 'total': total, 'skipped': skipped, 'reference_date': today.strftime('%d-%m-%Y')})


@app.route('/api/district-report')
def district_report():
    start_date = request.args.get('start', '')
    end_date   = request.args.get('end', '')
    try:
        client = get_ch_client()
        date_filter = ""
        if start_date and end_date:
            date_filter = f"AND substr(created_at, 1, 10) >= '{start_date}' AND substr(created_at, 1, 10) <= '{end_date}'"
        # Fetch ALL districts (no LIMIT) so we can compute Others correctly
        query = f"""
            SELECT district, count() as cnt
            FROM loyalty_user_data
            WHERE district != '' {date_filter}
            GROUP BY district
            ORDER BY cnt DESC
        """
        result = client.query(query)
        all_rows = result.result_rows

        # Top 19 named districts
        top19 = [{'rank': i+1, 'district': row[0], 'count': int(row[1])}
                 for i, row in enumerate(all_rows[:19])]

        # "Others (20+)" = sum of all districts from rank 20 onwards
        others_count = sum(int(r[1]) for r in all_rows[19:])
        others_label = f"Others (20+)"

        districts = top19
        if others_count > 0:
            districts = top19 + [{'rank': 20, 'district': others_label, 'count': others_count}]

        total = sum(d['count'] for d in districts)
        return jsonify({'districts': districts, 'total': total})

    except Exception as e:
        print("district-report CH error:", e)
        try:
            df = get_customer_profiles_df()
            col = 'District' if 'District' in df.columns else ('state' if 'state' in df.columns else None)
            if col is None:
                return jsonify({'districts': [], 'total': 0})
            df = df[df[col].notna() & (df[col].astype(str).str.strip() != '')]
            if start_date and 'created_at' in df.columns:
                df = df[df['created_at'].astype(str).str[:10] >= start_date]
            if end_date and 'created_at' in df.columns:
                df = df[df['created_at'].astype(str).str[:10] <= end_date]
            counts = df[col].value_counts()
            top19 = [{'rank': i+1, 'district': str(d), 'count': int(c)}
                     for i, (d, c) in enumerate(list(counts.items())[:19])]
            others_count = int(counts.iloc[19:].sum()) if len(counts) > 19 else 0
            districts = top19
            if others_count > 0:
                districts = top19 + [{'rank': 20, 'district': 'Others (20+)', 'count': others_count}]
            return jsonify({'districts': districts, 'total': sum(d['count'] for d in districts)})
        except Exception as e2:
            return jsonify({'error': str(e2)}), 500

MONTH_NAMES = {
    1: 'January', 2: 'February', 3: 'March', 4: 'April',
    5: 'May', 6: 'June', 7: 'July', 8: 'August',
    9: 'September', 10: 'October', 11: 'November', 12: 'December'
}

@app.route('/api/birth-month-summary')
def birth_month_summary():
    try:
        client = get_ch_client()
        query = """
            SELECT
                toInt32OrZero(splitByChar('-', date_of_birth)[2]) as month_num,
                count() as cnt
            FROM loyalty_user_data
            WHERE date_of_birth != '' AND length(date_of_birth) >= 8
            GROUP BY month_num
            HAVING month_num >= 1 AND month_num <= 12
        """
        result = client.query(query)
        ch_counts = {int(row[0]): int(row[1]) for row in result.result_rows}
        results = []
        total = 0
        for i in range(1, 13):
            count = ch_counts.get(i, 0)
            total += count
            results.append({'month_id': i, 'month': MONTH_NAMES[i], 'count': count})
        return jsonify({'months': results, 'total': total})
    except Exception as e:
        print("birth-month CH error:", e)
        try:
            df = get_customer_profiles_df()
            df = df[df['date_of_birth'].notna() & (df['date_of_birth'].astype(str).str.strip() != '')].copy()
            df['month_num'] = df['date_of_birth'].astype(str).str.split('-').str[1]
            df['month_num'] = pd.to_numeric(df['month_num'], errors='coerce')
            df = df.dropna(subset=['month_num'])
            df['month_num'] = df['month_num'].astype(int)
            df = df[(df['month_num'] >= 1) & (df['month_num'] <= 12)]
            counts = df['month_num'].value_counts().to_dict()
            results = []
            total = 0
            for i in range(1, 13):
                count = int(counts.get(i, 0))
                total += count
                results.append({'month_id': i, 'month': MONTH_NAMES[i], 'count': count})
            return jsonify({'months': results, 'total': total})
        except Exception as e2:
            return jsonify({'error': str(e2)}), 500


@app.route('/api/birth-month-export')
def birth_month_export():
    try:
        month_id = request.args.get('month', type=int)
        if not month_id or month_id < 1 or month_id > 12:
            return jsonify({'error': 'Invalid month parameter'}), 400
        client = get_ch_client()
        query = f"""
            SELECT firstname, lastname, user_phone, date_of_birth
            FROM loyalty_user_data
            WHERE date_of_birth != ''
            AND toInt32OrZero(splitByChar('-', date_of_birth)[2]) = {month_id}
        """
        result = client.query(query)
        records = [{
            'name': (str(r[0]) + ' ' + str(r[1])).strip(),
            'phone': str(r[2]),
            'dob': str(r[3])
        } for r in result.result_rows]
        return jsonify({'data': records, 'month_name': MONTH_NAMES[month_id]})
    except Exception as e:
        print("birth-month-export CH error:", e)
        try:
            df = get_customer_profiles_df()
            df = df[df['date_of_birth'].notna() & (df['date_of_birth'].astype(str).str.strip() != '')].copy()
            df['month_num'] = df['date_of_birth'].astype(str).str.split('-').str[1]
            df['month_num'] = pd.to_numeric(df['month_num'], errors='coerce')
            df_month = df[df['month_num'] == month_id].copy()
            df_month['name'] = df_month.get('firstname', pd.Series()).fillna('').astype(str) + ' ' + df_month.get('lastname', pd.Series()).fillna('').astype(str)
            df_month['name'] = df_month['name'].str.strip()
            df_month['phone'] = df_month.get('user_phone', pd.Series()).fillna('').astype(str)
            df_month['dob'] = df_month['date_of_birth'].fillna('')
            records = df_month[['name', 'phone', 'dob']].to_dict('records')
            return jsonify({'data': records, 'month_name': MONTH_NAMES[month_id]})
        except Exception as e2:
            return jsonify({'error': str(e2)}), 500

@app.route('/api/anniversary-month-summary')
def anniversary_month_summary():
    try:
        client = get_ch_client()
        query = """
            SELECT
                toInt32OrZero(splitByChar('-', wedding_anniversary)[2]) as month_num,
                count() as cnt
            FROM loyalty_user_data
            WHERE wedding_anniversary != '' AND wedding_anniversary != 'null'
            AND length(wedding_anniversary) >= 8
            GROUP BY month_num
            HAVING month_num >= 1 AND month_num <= 12
        """
        result = client.query(query)
        ch_counts = {int(row[0]): int(row[1]) for row in result.result_rows}
        results = []
        total = 0
        for i in range(1, 13):
            count = ch_counts.get(i, 0)
            total += count
            results.append({'month_id': i, 'month': MONTH_NAMES[i], 'count': count})
        return jsonify({'months': results, 'total': total})
    except Exception as e:
        print("anniversary-month CH error:", e)
        try:
            df = get_customer_profiles_df()
            if 'wedding_anniversary' not in df.columns:
                return jsonify({'months': [{'month_id': i, 'month': MONTH_NAMES[i], 'count': 0} for i in range(1,13)], 'total': 0})
            df = df[df['wedding_anniversary'].notna()].copy()
            df = df[~df['wedding_anniversary'].astype(str).str.strip().str.lower().isin(['', 'null'])]
            df['month_num'] = df['wedding_anniversary'].astype(str).str.split('-').str[1]
            df['month_num'] = pd.to_numeric(df['month_num'], errors='coerce')
            df = df.dropna(subset=['month_num'])
            df['month_num'] = df['month_num'].astype(int)
            df = df[(df['month_num'] >= 1) & (df['month_num'] <= 12)]
            counts = df['month_num'].value_counts().to_dict()
            results = [{'month_id': i, 'month': MONTH_NAMES[i], 'count': int(counts.get(i, 0))} for i in range(1, 13)]
            return jsonify({'months': results, 'total': sum(r['count'] for r in results)})
        except Exception as e2:
            return jsonify({'error': str(e2)}), 500

@app.route('/api/anniversary-month-export')
def anniversary_month_export():
    try:
        month_id = request.args.get('month', type=int)
        if not month_id or month_id < 1 or month_id > 12:
            return jsonify({'error': 'Invalid month parameter'}), 400
        client = get_ch_client()
        query = f"""
            SELECT firstname, lastname, user_phone, wedding_anniversary
            FROM loyalty_user_data
            WHERE wedding_anniversary != '' AND wedding_anniversary != 'null'
            AND toInt32OrZero(splitByChar('-', wedding_anniversary)[2]) = {month_id}
        """
        result = client.query(query)
        records = [{
            'name': (str(r[0]) + ' ' + str(r[1])).strip(),
            'phone': str(r[2]),
            'anniversary': str(r[3])
        } for r in result.result_rows]
        return jsonify({'data': records, 'month_name': MONTH_NAMES[month_id]})
    except Exception as e:
        print("anniversary-export CH error:", e)
        try:
            df = get_customer_profiles_df()
            if 'wedding_anniversary' not in df.columns:
                return jsonify({'data': [], 'month_name': MONTH_NAMES[month_id]})
            df = df[df['wedding_anniversary'].notna()].copy()
            df['month_num'] = df['wedding_anniversary'].astype(str).str.split('-').str[1]
            df['month_num'] = pd.to_numeric(df['month_num'], errors='coerce')
            df_month = df[df['month_num'] == month_id].copy()
            df_month['name'] = df_month.get('firstname', pd.Series()).fillna('').astype(str) + ' ' + df_month.get('lastname', pd.Series()).fillna('').astype(str)
            df_month['name'] = df_month['name'].str.strip()
            df_month['phone'] = df_month.get('user_phone', pd.Series()).fillna('').astype(str)
            df_month['anniversary'] = df_month['wedding_anniversary'].fillna('')
            records = df_month[['name', 'phone', 'anniversary']].to_dict('records')
            return jsonify({'data': records, 'month_name': MONTH_NAMES[month_id]})
        except Exception as e2:
            return jsonify({'error': str(e2)}), 500
_BASE_MOBILES_CACHE = None

# ── Repeat cutoff used by new-customer-metrics (legacy fallback) ─────────────
# This is the programme start boundary used when no date filter is selected.
REPEAT_CUTOFF_DATE = '2026-07-31'   # day before programme launch

def _normalize_mob_expr(col):
    """
    Robust mobile number normalization to standard 10-digit Indian format.

    Handles all known formats in the data:
      9876543210       →  9876543210  (already clean)
      9876543210.0     →  9876543210  (Excel float artifact)
      919876543210     →  9876543210  (91 country-code prefix, 12 digits)
      +919876543210    →  9876543210  (+ sign + country code)
      09876543210      →  9876543210  (leading 0, 11 digits)
      98765 43210      →  9876543210  (spaces)

    Steps:
      1. Cast to string, remove ALL non-digit characters (strips .0, +, spaces, -)
      2. If 12 digits starting with '91'  → strip first 2 chars
      3. If 11 digits starting with '0'   → strip first char
      4. Result should be a valid 10-digit mobile
    """
    d = f"replaceRegexpAll(toString(coalesce({col}, '')), '[^0-9]', '')"
    return (
        f"multiIf("
        f"  length({d}) = 12 AND startsWith({d}, '91'), substr({d}, 3), "
        f"  length({d}) = 11 AND startsWith({d}, '0'),  substr({d}, 2), "
        f"  {d}"
        f")"
    )


def _re_sales_ctes():
    """
    Returns two comma-separated CTE definitions (without the leading WITH):

      re_join  : one row per R&E participant -> join_date = earliest
                 refer_point_data.start_date (the app download / join date).
      re_sales : sales_data rows of R&E participants made ON or AFTER their
                 join_date. Columns: mob, parsed_date, total_value, redemption.

    Rule: a sale / redemption only counts if it happened on or after the
    customer's refer_point_data date. e.g. downloaded in Aug 2026 but bought
    and redeemed in Feb 2026 -> the Feb transaction is NOT counted.
    """
    mob_re = _normalize_mob_expr('customer_mobile_number')
    mob_s  = _normalize_mob_expr('customer_mobile')
    return f"""
            re_join AS (
                SELECT {mob_re} AS mob,
                       min(toDateOrNull(substr(start_date, 1, 10))) AS join_date
                FROM refer_point_data
                WHERE customer_mobile_number != ''
                  AND length({mob_re}) = 10
                GROUP BY mob
                HAVING join_date IS NOT NULL
            ),
            re_sales AS (
                SELECT s.mob         AS mob,
                       s.parsed_date AS parsed_date,
                       s.total_value AS total_value,
                       s.redemption  AS redemption
                FROM (
                    SELECT {mob_s} AS mob,
                           parsed_date,
                           total_value,
                           abs(toFloat64OrZero(point_redemption)) AS redemption
                    FROM sales_data
                    WHERE customer_mobile != ''
                      AND length({mob_s}) = 10
                ) s
                INNER JOIN re_join r ON s.mob = r.mob
                WHERE s.parsed_date >= r.join_date
            )
    """


# Referral points expire this many days after the date they were credited.
# A credit on day D is usable on D, D+1, ... D+(REFERRAL_POINT_VALIDITY_DAYS-1).
REFERRAL_POINT_VALIDITY_DAYS = 30


def _re_window_ctes():
    """
    Returns comma-separated CTE definitions (without leading WITH / comma).
    Must be used AFTER _re_sales_ctes() in the same WITH block.

      re_credits      : one row per (mob, credit_date) with the referral points
                        credited that day (a customer can be credited many times).
      re_windows      : one row per mob with arrays of credit dates / points.
      re_window_sales : re_sales rows that fall inside the validity window of
                        at least one referral credit of that customer, i.e.
                        credit_date <= parsed_date < credit_date + VALIDITY_DAYS.
    """
    mob_re = _normalize_mob_expr('customer_mobile_number')
    days = int(REFERRAL_POINT_VALIDITY_DAYS)
    return f"""
            re_credits AS (
                SELECT {mob_re} AS mob,
                       assumeNotNull(toDateOrNull(substr(start_date, 1, 10))) AS credit_date,
                       sum(bonus_points) AS points
                FROM refer_point_data
                WHERE customer_mobile_number != ''
                  AND length({mob_re}) = 10
                  AND toDateOrNull(substr(start_date, 1, 10)) IS NOT NULL
                GROUP BY mob, credit_date
            ),
            re_windows AS (
                SELECT mob,
                       groupArray(credit_date) AS credit_dates,
                       groupArray(points)      AS credit_points
                FROM re_credits
                GROUP BY mob
            ),
            re_window_sales AS (
                SELECT s.mob AS mob, s.parsed_date AS parsed_date,
                       s.total_value AS total_value, s.redemption AS redemption
                FROM re_sales s
                INNER JOIN re_windows w ON s.mob = w.mob
                WHERE arrayExists(
                    d -> s.parsed_date >= d AND s.parsed_date < d + {days},
                    w.credit_dates
                )
            )
    """


def _attribute_referral_redemptions(credits, txns):
    """
    FIFO attribution of redemptions to referral point lots for ONE customer.

      credits : list of (credit_date, points)
      txns    : list of (txn_date, redemption) - in-window redemptions

    Each credit is a lot valid on [credit_date, credit_date + VALIDITY_DAYS).
    A redemption consumes points from lots that are active on its date,
    earliest-expiring first. Anything beyond the available referral points
    (already used up / expired / never received) is NOT attributed.

    Returns a list of (txn_date, attributed_points) in chronological order.
    """
    from datetime import timedelta
    validity = timedelta(days=REFERRAL_POINT_VALIDITY_DAYS)
    lots = sorted(
        [[d, d + validity, float(p or 0)] for d, p in credits],
        key=lambda l: (l[1], l[0])
    )
    out = []
    for txn_date, redemption in sorted(txns, key=lambda t: t[0]):
        need = float(redemption or 0)
        used = 0.0
        for lot in lots:
            if need <= 0:
                break
            start, expiry, remaining = lot
            if remaining <= 0 or not (start <= txn_date < expiry):
                continue
            take = min(remaining, need)
            lot[2] -= take
            need -= take
            used += take
        out.append((txn_date, used))
    return out


def _windowed_re_metrics(client, sd, ed, scope_ctes='', scope_filter=''):
    """
    Computes the four headline Refer & Earn metrics honouring the referral
    point validity window (REFERRAL_POINT_VALIDITY_DAYS) and the referral
    point cap:

      purchase_count          : distinct customers with >= 1 in-window purchase
                                in [sd, ed]
      redeemed_count          : distinct customers whose in-window redemptions
                                in [sd, ed] consumed > 0 referral points
      point_redeemed_value    : referral points consumed in [sd, ed] (capped at
                                the referral points actually available)
      redeemed_purchase_value : in-window purchase value in [sd, ed] of the
                                redeemed customers

    scope_ctes   : extra CTE definitions (no leading comma) that scope_filter
                   may reference, e.g. new_customers / repeat_customers.
    scope_filter : extra SQL condition on `mob`, starting with AND.
    """
    from datetime import date as _date
    sd_d = _date.fromisoformat(sd)
    ed_d = _date.fromisoformat(ed)
    extra = f",\n{scope_ctes}" if scope_ctes.strip() else ""
    with_block = f"""
        WITH
        {_re_sales_ctes()},
        {_re_window_ctes()}{extra}
    """

    # 1) In-range, in-window purchases -> purchase value per customer
    purchase_q = with_block + f"""
        SELECT mob, sum(total_value) AS value
        FROM re_window_sales
        WHERE parsed_date >= '{sd}' AND parsed_date <= '{ed}' {scope_filter}
        GROUP BY mob
    """
    value_by_mob = {r[0]: float(r[1] or 0) for r in client.query(purchase_q).result_rows}

    # 2) For customers with an in-range, in-window redemption: every in-window
    #    redemption up to `ed` (earlier ones may already have used up points)
    #    plus all their referral credits, for FIFO attribution in Python.
    redeem_q = with_block + f"""
        , redeem_txns AS (
            SELECT mob,
                   groupArray(parsed_date) AS txn_dates,
                   groupArray(redemption)  AS txn_amounts
            FROM re_window_sales
            WHERE redemption > 0 AND parsed_date <= '{ed}' {scope_filter}
            GROUP BY mob
            HAVING countIf(parsed_date >= '{sd}') > 0
        )
        SELECT t.mob, t.txn_dates, t.txn_amounts, w.credit_dates, w.credit_points
        FROM redeem_txns t
        INNER JOIN re_windows w ON t.mob = w.mob
    """
    point_redeemed = 0.0
    redeemers = set()
    for mob, txn_dates, txn_amounts, credit_dates, credit_points in client.query(redeem_q).result_rows:
        attributed = _attribute_referral_redemptions(
            list(zip(credit_dates, credit_points)),
            list(zip(txn_dates, txn_amounts)),
        )
        in_range = sum(pts for d, pts in attributed if sd_d <= d <= ed_d)
        if in_range > 0:
            point_redeemed += in_range
            redeemers.add(mob)

    return {
        'purchase_count':          len(value_by_mob),
        'redeemed_count':          len(redeemers),
        'point_redeemed_value':    point_redeemed,
        'redeemed_purchase_value': sum(value_by_mob.get(m, 0.0) for m in redeemers),
    }

@app.route('/api/customer-classification')
def customer_classification():
    """
    Dynamically classify R&E participants as New or Repeat based on the
    selected filter date range.

    Logic (per the user spec):
      - Repeat Customer : the customer has at least one purchase BEFORE the
                          filter start date (sd). They are an existing buyer.
      - New Customer    : the filter start date (sd) is on or after their
                          first-ever purchase date AND they have no purchase
                          before sd.  i.e. first_purchase_date >= sd.

    Only customers who made at least one purchase within [sd, ed] AND are
    R&E participants are counted.  "No Purchase Yet" is excluded entirely.

    Match key   : Customer Mobile (normalized to 10-digit Indian format)
    Data sources: refer_point_data (R&E members) + sales_data (purchase history)
    """
    from datetime import datetime
    start_date = request.args.get('start', '')
    end_date   = request.args.get('end', '')

    # Default: programme full range when no filter is applied
    if start_date and end_date:
        try:
            sd = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y-%m-%d')
            ed = datetime.strptime(end_date,   '%Y-%m-%d').strftime('%Y-%m-%d')
        except Exception:
            return jsonify({'error': 'Invalid date format'}), 400
    else:
        sd = '2026-01-16'   # programme launch date
        ed = datetime.today().strftime('%Y-%m-%d')

    try:
        client = get_ch_client()

        mob_sd = _normalize_mob_expr('sd.customer_mobile')
        mob_fp = _normalize_mob_expr('fp.customer_mobile')
        mob_re = _normalize_mob_expr('customer_mobile_number')
        mob_s  = _normalize_mob_expr('customer_mobile')

        query = f"""
            WITH
            {_re_sales_ctes()},
            {_re_window_ctes()},

            -- First-ever purchase date per customer across ALL of sales_data
            first_purchase AS (
                SELECT
                    {_normalize_mob_expr('customer_mobile')} AS mob,
                    min(parsed_date) AS first_date
                FROM sales_data
                WHERE customer_mobile != ''
                  AND length({_normalize_mob_expr('customer_mobile')}) = 10
                GROUP BY mob
            ),

            -- R&E participants who purchased within the selected date range,
            -- counting only purchases inside a referral-point validity window
            in_range_buyers AS (
                SELECT DISTINCT mob
                FROM re_window_sales
                WHERE parsed_date >= '{sd}'
                  AND parsed_date <= '{ed}'
            )

            -- Classify each in-range buyer:
            --   New    = their first-ever purchase date >= sd (no prior purchase)
            --   Repeat = their first-ever purchase date <  sd (bought before this range)
            SELECT
                count()                                AS total_buyers,
                countIf(fp.first_date >= '{sd}')       AS new_count,
                countIf(fp.first_date <  '{sd}')       AS repeat_count
            FROM in_range_buyers irb
            LEFT JOIN first_purchase fp ON irb.mob = fp.mob
        """

        row = client.query(query).result_rows[0]
        total_buyers  = int(row[0]) if row[0] else 0
        new_count     = int(row[1]) if row[1] else 0
        repeat_count  = int(row[2]) if row[2] else 0

        # Percentages are out of buyers in range (Repeat + New = total_buyers)
        repeat_pct = round(repeat_count / total_buyers * 100, 2) if total_buyers else 0
        new_pct    = round(new_count    / total_buyers * 100, 2) if total_buyers else 0

        # Total R&E participants (always 91,550 reference)
        total_re_query = f"""
            SELECT count(DISTINCT {_normalize_mob_expr('customer_mobile_number')}) AS cnt
            FROM refer_point_data
            WHERE customer_mobile_number != ''
              AND length({_normalize_mob_expr('customer_mobile_number')}) = 10
        """
        re_row = client.query(total_re_query).result_rows[0]
        total_re_participants = int(re_row[0]) if re_row[0] else 0

        return jsonify({
            'total_participants':  total_re_participants,   # full R&E base (for header card)
            'total_buyers':        total_buyers,            # buyers in selected range
            'repeat_count':        repeat_count,
            'new_count':           new_count,
            'repeat_pct':          repeat_pct,
            'new_pct':             new_pct,
            'cutoff_date':         sd,                      # dynamic – the filter start date
            'date_range':          {'start': sd, 'end': ed}
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/new-customer-metrics')
def new_customer_metrics():
    """
    Performance Metrics for NEW customers only.
    Uses the SAME classification logic as /api/customer-classification:
      New = R&E participant who bought in range AND first-ever purchase >= sd
    """
    from datetime import datetime
    start_date = request.args.get('start', '')
    end_date   = request.args.get('end', '')

    if start_date and end_date:
        try:
            sd = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y-%m-%d')
            ed = datetime.strptime(end_date,   '%Y-%m-%d').strftime('%Y-%m-%d')
        except Exception:
            return jsonify({'error': 'Invalid date format'}), 400
    else:
        sd = '2026-01-16'
        ed = datetime.today().strftime('%Y-%m-%d')

    try:
        client = get_ch_client()
        mob_re = _normalize_mob_expr('customer_mobile_number')
        mob_s  = _normalize_mob_expr('customer_mobile')

        # Segment CTEs ─ identical to customer-classification logic
        scope_ctes = f"""
            first_purchase AS (
                SELECT {mob_s} AS mob, min(parsed_date) AS first_date
                FROM sales_data
                WHERE customer_mobile != ''
                  AND length({mob_s}) = 10
                GROUP BY mob
            ),
            -- Only purchases inside a referral-point validity window
            in_range_buyers AS (
                SELECT DISTINCT mob
                FROM re_window_sales
                WHERE parsed_date >= '{sd}' AND parsed_date <= '{ed}'
            ),
            -- New = first-ever purchase date >= sd (same as classification)
            new_customers AS (
                SELECT irb.mob
                FROM in_range_buyers irb
                LEFT JOIN first_purchase fp ON irb.mob = fp.mob
                WHERE fp.first_date >= '{sd}'
            )
        """
        # Shared CTEs (re_sales + validity windows + segment)
        shared = f"""
            WITH
            {_re_sales_ctes()},
            {_re_window_ctes()},
            {scope_ctes}
        """

        # Segment size + bonus points given
        metrics_q = shared + f"""
            SELECT
                (SELECT count() FROM new_customers)           AS nc_count,
                (SELECT sum(rpd.bonus_points)
                 FROM (
                     SELECT {mob_re} AS mob, bonus_points
                     FROM refer_point_data WHERE customer_mobile_number != ''
                       AND start_date >= '{sd}' AND start_date <= '{ed}'
                 ) rpd
                 WHERE rpd.mob IN (SELECT mob FROM new_customers)) AS nc_bonus
        """
        row = client.query(metrics_q).result_rows[0]
        nc_count         = int(row[0])   if row[0] else 0
        nc_bonus         = float(row[1]) if row[1] else 0.0

        # Purchase / redemption metrics: referral-point validity window + cap
        m = _windowed_re_metrics(
            client, sd, ed,
            scope_ctes=scope_ctes,
            scope_filter="AND mob IN (SELECT mob FROM new_customers)",
        )
        purchase_count   = m['purchase_count']
        redeemed_count   = m['redeemed_count']
        point_redeemed   = m['point_redeemed_value']
        redeemed_purch_v = m['redeemed_purchase_value']

        if redeemed_purch_v > 0:
            discount_pct = (point_redeemed / redeemed_purch_v) * 100
            avg_purchase = redeemed_purch_v / redeemed_count if redeemed_count else 0
            avg_points   = point_redeemed   / redeemed_count if redeemed_count else 0
        else:
            discount_pct = avg_purchase = avg_points = 0

        # Daily trend for new customers
        trend_q = shared + f"""
            ,
            daily AS (
                SELECT mob, parsed_date
                FROM re_window_sales
                WHERE parsed_date >= '{sd}' AND parsed_date <= '{ed}'
                  AND mob IN (SELECT mob FROM new_customers)
            )
            SELECT parsed_date, count(DISTINCT mob) AS cnt
            FROM daily
            GROUP BY parsed_date
            ORDER BY parsed_date
        """
        trend_rows   = client.query(trend_q).result_rows
        trend_labels = [str(r[0]) for r in trend_rows]
        trend_data   = [int(r[1]) for r in trend_rows]

        return jsonify({
            "master_stats": {
                "total_customer_count":    nc_count,
                "total_bonus_point_given": nc_bonus
            },
            "range_stats": {
                "purchase_count":          purchase_count,
                "redeemed_count":          redeemed_count,
                "point_redeemed_value":    point_redeemed,
                "redeemed_purchase_value": redeemed_purch_v,
                "loyalty_discount_pct":    round(discount_pct, 2),
                "avg_purchase_value":      round(avg_purchase, 2),
                "avg_loyalty_redemption":  round(avg_points, 2)
            },
            "trend": {"labels": trend_labels, "data": trend_data},
            "is_full_range": not (start_date and end_date)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/repeat-customer-metrics')
def repeat_customer_metrics():
    """
    Performance Metrics for REPEAT customers only.
    Uses the SAME classification logic as /api/customer-classification:
      Repeat = R\u0026E participant who bought in range AND first-ever purchase < sd
    """
    from datetime import datetime
    start_date = request.args.get('start', '')
    end_date   = request.args.get('end', '')

    if start_date and end_date:
        try:
            sd = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y-%m-%d')
            ed = datetime.strptime(end_date,   '%Y-%m-%d').strftime('%Y-%m-%d')
        except Exception:
            return jsonify({'error': 'Invalid date format'}), 400
    else:
        sd = '2026-01-16'
        ed = datetime.today().strftime('%Y-%m-%d')

    try:
        client = get_ch_client()
        mob_re = _normalize_mob_expr('customer_mobile_number')
        mob_s  = _normalize_mob_expr('customer_mobile')

        # Segment CTEs ─ identical to customer-classification logic
        scope_ctes = f"""
            first_purchase AS (
                SELECT {mob_s} AS mob, min(parsed_date) AS first_date
                FROM sales_data
                WHERE customer_mobile != ''
                  AND length({mob_s}) = 10
                GROUP BY mob
            ),
            -- Only purchases inside a referral-point validity window
            in_range_buyers AS (
                SELECT DISTINCT mob
                FROM re_window_sales
                WHERE parsed_date >= '{sd}' AND parsed_date <= '{ed}'
            ),
            -- Repeat = first-ever purchase date < sd (same as classification)
            repeat_customers AS (
                SELECT irb.mob
                FROM in_range_buyers irb
                LEFT JOIN first_purchase fp ON irb.mob = fp.mob
                WHERE fp.first_date < '{sd}'
            )
        """
        # Shared CTEs (re_sales + validity windows + segment)
        shared = f"""
            WITH
            {_re_sales_ctes()},
            {_re_window_ctes()},
            {scope_ctes}
        """

        # Segment size + bonus points given
        metrics_q = shared + f"""
            SELECT
                (SELECT count() FROM repeat_customers)        AS rc_count,
                (SELECT sum(rpd.bonus_points)
                 FROM (
                     SELECT {mob_re} AS mob, bonus_points
                     FROM refer_point_data WHERE customer_mobile_number != ''
                       AND start_date >= '{sd}' AND start_date <= '{ed}'
                 ) rpd
                 WHERE rpd.mob IN (SELECT mob FROM repeat_customers)) AS rc_bonus
        """
        row = client.query(metrics_q).result_rows[0]
        rc_count         = int(row[0])   if row[0] else 0
        rc_bonus         = float(row[1]) if row[1] else 0.0

        # Purchase / redemption metrics: referral-point validity window + cap
        m = _windowed_re_metrics(
            client, sd, ed,
            scope_ctes=scope_ctes,
            scope_filter="AND mob IN (SELECT mob FROM repeat_customers)",
        )
        purchase_count   = m['purchase_count']
        redeemed_count   = m['redeemed_count']
        point_redeemed   = m['point_redeemed_value']
        redeemed_purch_v = m['redeemed_purchase_value']

        if redeemed_purch_v > 0:
            discount_pct = (point_redeemed / redeemed_purch_v) * 100
            avg_purchase = redeemed_purch_v / redeemed_count if redeemed_count else 0
            avg_points   = point_redeemed   / redeemed_count if redeemed_count else 0
        else:
            discount_pct = avg_purchase = avg_points = 0

        # Daily trend for repeat customers
        trend_q = shared + f"""
            ,
            daily AS (
                SELECT mob, parsed_date
                FROM re_window_sales
                WHERE parsed_date >= '{sd}' AND parsed_date <= '{ed}'
                  AND mob IN (SELECT mob FROM repeat_customers)
            )
            SELECT parsed_date, count(DISTINCT mob) AS cnt
            FROM daily
            GROUP BY parsed_date
            ORDER BY parsed_date
        """
        trend_rows   = client.query(trend_q).result_rows
        trend_labels = [str(r[0]) for r in trend_rows]
        trend_data   = [int(r[1]) for r in trend_rows]

        return jsonify({
            "master_stats": {
                "total_customer_count":    rc_count,
                "total_bonus_point_given": rc_bonus
            },
            "range_stats": {
                "purchase_count":          purchase_count,
                "redeemed_count":          redeemed_count,
                "point_redeemed_value":    point_redeemed,
                "redeemed_purchase_value": redeemed_purch_v,
                "loyalty_discount_pct":    round(discount_pct, 2),
                "avg_purchase_value":      round(avg_purchase, 2),
                "avg_loyalty_redemption":  round(avg_points, 2)
            },
            "trend": {"labels": trend_labels, "data": trend_data},
            "is_full_range": not (start_date and end_date)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500




@app.route('/api/cohort-analysis')
def cohort_analysis():
    """
    Monthly Cohort Retention Analysis — R&E Programme Period Only.

    Cohort month = calendar month of a customer's first purchase on or after
    the R&E programme start date (2026-01-16). Historical pre-programme purchases
    are excluded so cohorts align with the 24,337 unique buyers in the programme.
    Only R&E participants (those in refer_point_data) are included.
    Same mobile on same day → counted once per (cohort_month, month_offset) cell.

    Response:
      cohorts  : list of cohort rows, each with cohort_label, cohort_size, and cells list
      max_offset: highest month offset present in the data
    """
    from datetime import datetime

    try:
        client   = get_ch_client()
        mob_re   = _normalize_mob_expr('customer_mobile_number')
        mob_s    = _normalize_mob_expr('customer_mobile')

        # ── Step 1: cohort sizes ─────────────────────────────────────────
        size_q = f"""
            WITH
            {_re_sales_ctes()},
            -- Cohort = month of first purchase ON/AFTER the refer_point_data date
            first_purchase AS (
                SELECT
                    mob,
                    toStartOfMonth(min(parsed_date)) AS cohort_month
                FROM re_sales
                WHERE parsed_date >= '2026-01-16'
                GROUP BY mob
            )
            SELECT
                cohort_month,
                count() AS cohort_size
            FROM first_purchase
            GROUP BY cohort_month
            ORDER BY cohort_month ASC
        """
        size_rows = client.query(size_q).result_rows
        # Build a dict: cohort_month_str -> size
        cohort_sizes = {}
        cohort_months_ordered = []
        for r in size_rows:
            cm = str(r[0])[:7]   # 'YYYY-MM'
            cohort_sizes[cm] = int(r[1])
            cohort_months_ordered.append(cm)

        if not cohort_months_ordered:
            return jsonify({'cohorts': [], 'max_offset': 0})

        # ── Step 2: per-cohort per-month-offset metrics ──────────────────
        metrics_q = f"""
            WITH
            {_re_sales_ctes()},
            first_purchase AS (
                SELECT
                    mob,
                    toStartOfMonth(min(parsed_date)) AS cohort_month
                FROM re_sales
                WHERE parsed_date >= '2026-01-16'
                GROUP BY mob
            ),
            -- Daily dedup: one row per (mob, day) to avoid double-counting
            -- same customer purchasing multiple times in one day
            daily_purchases AS (
                SELECT
                    mob,
                    parsed_date,
                    sum(total_value) AS day_revenue,
                    sum(redemption)  AS day_redemption
                FROM re_sales
                WHERE parsed_date >= '2026-01-16'
                GROUP BY mob, parsed_date
            ),
            monthly_activity AS (
                SELECT
                    fp.cohort_month,
                    dp.mob,
                    toStartOfMonth(dp.parsed_date)                                      AS activity_month,
                    dateDiff('month', fp.cohort_month, toStartOfMonth(dp.parsed_date))  AS month_offset,
                    sum(dp.day_revenue)                                                 AS revenue,
                    sum(dp.day_redemption)                                              AS redemption
                FROM daily_purchases dp
                JOIN first_purchase fp ON dp.mob = fp.mob
                WHERE month_offset >= 0
                GROUP BY fp.cohort_month, dp.mob, toStartOfMonth(dp.parsed_date), month_offset
            )
            SELECT
                formatDateTime(cohort_month, '%Y-%m')  AS cohort_ym,
                month_offset,
                countDistinct(mob)                     AS active_customers,
                round(sum(revenue), 2)                 AS total_revenue,
                round(sum(redemption), 2)              AS total_redemption,
                round(sum(revenue) / countDistinct(mob), 2) AS avg_purchase_value
            FROM monthly_activity
            GROUP BY cohort_ym, month_offset
            ORDER BY cohort_ym ASC, month_offset ASC
        """
        metrics_rows = client.query(metrics_q).result_rows

        # ── Step 3: assemble response ────────────────────────────────────
        # Build dict: cohort_ym -> { month_offset -> metrics }
        cell_map = {}
        max_offset = 0
        for r in metrics_rows:
            ym          = str(r[0])
            offset      = int(r[1])
            active      = int(r[2])
            revenue     = float(r[3]) if r[3] else 0.0
            redemption  = float(r[4]) if r[4] else 0.0
            avg_purch   = float(r[5]) if r[5] else 0.0
            if ym not in cell_map:
                cell_map[ym] = {}
            cell_map[ym][offset] = {
                'active':        active,
                'revenue':       revenue,
                'bonus_redeemed': redemption,
                'avg_purchase':  avg_purch
            }
            if offset > max_offset:
                max_offset = offset

        cohorts = []
        for ym in cohort_months_ordered:
            size = cohort_sizes.get(ym, 0)
            cells_raw = cell_map.get(ym, {})
            cells = []
            for offset in range(0, max_offset + 1):
                if offset in cells_raw:
                    d = cells_raw[offset]
                    cells.append({
                        'month_offset':   offset,
                        'active':         d['active'],
                        'retention_pct':  round(d['active'] / size * 100, 1) if size else 0,
                        'revenue':        d['revenue'],
                        'bonus_redeemed': d['bonus_redeemed'],
                        'avg_purchase':   d['avg_purchase'],
                    })
                else:
                    cells.append(None)   # future/no data → renders as "—"

            # Parse friendly label: '2026-01' → 'Jan 2026'
            try:
                dt = datetime.strptime(ym, '%Y-%m')
                label = dt.strftime('%b %Y')
            except Exception:
                label = ym

            cohorts.append({
                'cohort_month': ym,
                'cohort_label': label,
                'cohort_size':  size,
                'cells':        cells,
            })

        return jsonify({'cohorts': cohorts, 'max_offset': max_offset})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("Starting Flask Dashboard Server on port 8080...")
    app.run(port=8080, debug=False)


if __name__ == "__main__":
    print("Starting Flask Dashboard Server on port 8080...")
    app.run(port=8080, debug=False)
