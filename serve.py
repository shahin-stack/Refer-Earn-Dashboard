from flask import Flask, render_template, request, jsonify, send_from_directory
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

    range_query = f"""
        WITH valid_sales AS (
            SELECT 
                if(endsWith(customer_mobile, '.0'), substr(customer_mobile, 1, length(customer_mobile) - 2), customer_mobile) as mob,
                total_value,
                abs(toFloat64OrZero(point_redemption)) as redemption
            FROM sales_data
            WHERE {date_filter}
            AND if(endsWith(customer_mobile, '.0'), substr(customer_mobile, 1, length(customer_mobile) - 2), customer_mobile) IN (
                SELECT if(endsWith(customer_mobile_number, '.0'), substr(customer_mobile_number, 1, length(customer_mobile_number) - 2), customer_mobile_number) FROM refer_point_data
            )
        ),
        redeemers AS (
            SELECT DISTINCT mob FROM valid_sales WHERE redemption > 0
        )
        SELECT 
            count(distinct mob) as purchase_count,
            (SELECT count() FROM redeemers) as redeemed_count,
            sum(redemption) as point_redeemed_value,
            (SELECT sum(total_value) FROM valid_sales WHERE mob IN (SELECT mob FROM redeemers)) as redeemed_purchase_value
        FROM valid_sales
    """
    
    try:
        range_res = client.query(range_query).result_rows[0]
        range_purchase_count = int(range_res[0]) if range_res[0] else 0
        range_redeemed_count = int(range_res[1]) if range_res[1] else 0
        range_point_redeemed = float(range_res[2]) if range_res[2] else 0.0
        range_redeemed_purch_v = float(range_res[3]) if range_res[3] else 0.0
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
        query = f"""
            SELECT state, count() as cnt
            FROM loyalty_user_data
            WHERE state != '' {date_filter}
            GROUP BY state
            ORDER BY cnt DESC
            LIMIT 20
        """
        result = client.query(query)
        districts = [{'rank': i+1, 'district': row[0], 'count': int(row[1])} for i, row in enumerate(result.result_rows)]
        total_top_20 = sum(d['count'] for d in districts)
        return jsonify({'districts': districts, 'total': total_top_20})
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
            counts = df[col].value_counts().head(20)
            districts = [{'rank': i+1, 'district': str(d), 'count': int(c)} for i, (d, c) in enumerate(counts.items())]
            return jsonify({'districts': districts, 'total': int(counts.sum())})
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

# ── Classification cutoff: August 1, 2026 ────────────────────────────────────
# Repeat Customer : has at least one purchase on or BEFORE July 31, 2026
# New Customer    : has NO purchase before August 1, 2026
#                   (first purchase on/after Aug 1, or no purchase history)
CLASSIFICATION_CUTOFF = '2026-07-31'   # inclusive upper bound for Repeat

def _normalize_mob_expr(col):
    """ClickHouse expression to strip trailing .0 from mobile numbers."""
    return f"if(endsWith({col}, '.0'), substr({col}, 1, length({col})-2), {col})"

@app.route('/api/customer-classification')
def customer_classification():
    """
    Classify all 91,550 Refer & Earn participants into Repeat vs New.

    Specification:
      - Repeat Customer : mobile appears in sales_data with parsed_date <= 2026-07-31
                          (purchased at least once on or before July 31, 2026)
      - New Customer    : mobile does NOT appear in sales_data before August 1, 2026
                          (no purchase history before the cutoff)

    Match key   : Customer Mobile (normalized — trailing .0 stripped)
    Data sources: refer_point_data (R&E participants) + sales_data (purchase history)
    Guarantee   : Repeat + New = Total Participants (no unclassified records)
    """
    try:
        client = get_ch_client()

        query = f"""
            WITH
            -- Step 1: All unique R&E participant mobiles (normalized)
            re_participants AS (
                SELECT DISTINCT
                    {_normalize_mob_expr('customer_mobile_number')} AS mob
                FROM refer_point_data
                WHERE customer_mobile_number != ''
                  AND customer_mobile_number IS NOT NULL
            ),

            -- Step 2: All mobiles with at least one purchase on or before July 31, 2026
            --         (these are "Repeat" customers per the cutoff definition)
            repeat_base AS (
                SELECT DISTINCT
                    {_normalize_mob_expr('customer_mobile')} AS mob
                FROM sales_data
                WHERE parsed_date <= '{CLASSIFICATION_CUTOFF}'
                  AND customer_mobile != ''
            )

            -- Step 3: Classify every R&E participant
            --   Repeat = mob found in repeat_base
            --   New    = mob NOT found in repeat_base
            --   Total  = Repeat + New (guaranteed, no gaps)
            SELECT
                count()                                                   AS total_participants,
                countIf(mob IN (SELECT mob FROM repeat_base))             AS repeat_customers,
                countIf(mob NOT IN (SELECT mob FROM repeat_base))         AS new_customers,
                (SELECT count() FROM repeat_base)                         AS base_size
            FROM re_participants
        """

        row = client.query(query).result_rows[0]
        total_participants = int(row[0])
        repeat_count       = int(row[1])
        new_count          = int(row[2])
        base_size          = int(row[3])

        # Percentages — new_pct derived from repeat_pct to guarantee they sum to 100%
        repeat_pct = round(repeat_count / total_participants * 100, 2) if total_participants else 0
        new_pct    = round(100 - repeat_pct, 2)

        return jsonify({
            'total_participants': total_participants,
            'repeat_count':       repeat_count,
            'new_count':          new_count,
            'repeat_pct':         repeat_pct,
            'new_pct':            new_pct,
            'base_size':          base_size,
            'cutoff_date':        CLASSIFICATION_CUTOFF
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/new-customer-metrics')
def new_customer_metrics():
    """
    Core Performance Metrics restricted to NEW customers only.

    New Customer = in refer_point_data BUT NOT in sales_data before 2026-08-01
    Sales range  = filtered by the date picker (default: Jan 2026 onwards)
    """
    start_date = request.args.get('start', '')
    end_date   = request.args.get('end', '')

    is_full_range = not (start_date and end_date)

    # Build sales date filter
    if is_full_range:
        sales_date_filter = "parsed_date >= '2026-01-16'"  # programme start date
        ref_date_filter   = ""
    else:
        try:
            from datetime import datetime
            sd = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y-%m-%d')
            ed = datetime.strptime(end_date,   '%Y-%m-%d').strftime('%Y-%m-%d')
            sales_date_filter = f"parsed_date >= '{sd}' AND parsed_date <= '{ed}'"
            ref_date_filter   = f"AND start_date >= '{sd}' AND start_date <= '{ed}'"
        except Exception:
            return jsonify({'error': 'Invalid date format'}), 400

    try:
        client = get_ch_client()

        # ── Step 1: Master stats for New Customers ─────────────────────────
        # New = in refer_point_data BUT NOT in sales_data before Aug 1 2026
        master_query = f"""
            WITH base AS (
                SELECT DISTINCT {_normalize_mob_expr('customer_mobile')} AS mob
                FROM sales_data
                WHERE parsed_date <= '{REPEAT_CUTOFF_DATE}'
                  AND customer_mobile != ''
            )
            SELECT
                count(DISTINCT mob)  AS nc_customer_count,
                sum(bonus_points)    AS nc_bonus_points
            FROM (
                SELECT
                    {_normalize_mob_expr('customer_mobile_number')} AS mob,
                    bonus_points
                FROM refer_point_data
                WHERE customer_mobile_number != '' {ref_date_filter}
            )
            WHERE mob NOT IN (SELECT mob FROM base)
        """
        m = client.query(master_query).result_rows[0]
        nc_total_customer_count    = int(m[0])
        nc_total_bonus_point_given = float(m[1]) if m[1] else 0.0

        # ── Step 2: Sales metrics for New Customers ────────────────────────
        range_query = f"""
            WITH base AS (
                SELECT DISTINCT {_normalize_mob_expr('customer_mobile')} AS mob
                FROM sales_data
                WHERE parsed_date <= '{REPEAT_CUTOFF_DATE}'
                  AND customer_mobile != ''
            ),
            re_new AS (
                SELECT DISTINCT {_normalize_mob_expr('customer_mobile_number')} AS mob
                FROM refer_point_data
                WHERE customer_mobile_number != ''
                  AND mob NOT IN (SELECT mob FROM base)
            ),
            valid_sales AS (
                SELECT
                    {_normalize_mob_expr('customer_mobile')} AS mob,
                    total_value,
                    abs(toFloat64OrZero(point_redemption)) AS redemption
                FROM sales_data
                WHERE {sales_date_filter}
                  AND {_normalize_mob_expr('customer_mobile')} IN (SELECT mob FROM re_new)
            ),
            redeemers AS (
                SELECT DISTINCT mob FROM valid_sales WHERE redemption > 0
            )
            SELECT
                count(DISTINCT mob)                                                            AS purchase_count,
                (SELECT count() FROM redeemers)                                                AS redeemed_count,
                sum(redemption)                                                                AS point_redeemed_value,
                (SELECT sum(total_value) FROM valid_sales WHERE mob IN (SELECT mob FROM redeemers)) AS redeemed_purchase_value
            FROM valid_sales
        """
        r = client.query(range_query).result_rows[0]
        nc_purchase_count    = int(r[0])   if r[0] else 0
        nc_redeemed_count    = int(r[1])   if r[1] else 0
        nc_point_redeemed    = float(r[2]) if r[2] else 0.0
        nc_redeemed_purch_v  = float(r[3]) if r[3] else 0.0

        if nc_redeemed_purch_v > 0:
            nc_discount_pct = (nc_point_redeemed / nc_redeemed_purch_v) * 100
            nc_avg_purchase = nc_redeemed_purch_v / nc_redeemed_count if nc_redeemed_count else 0
            nc_avg_points   = nc_point_redeemed   / nc_redeemed_count if nc_redeemed_count else 0
        else:
            nc_discount_pct = nc_avg_purchase = nc_avg_points = 0

        return jsonify({
            "master_stats": {
                "total_customer_count":    nc_total_customer_count,
                "total_bonus_point_given": nc_total_bonus_point_given
            },
            "range_stats": {
                "purchase_count":          nc_purchase_count,
                "redeemed_count":          nc_redeemed_count,
                "point_redeemed_value":    nc_point_redeemed,
                "redeemed_purchase_value": nc_redeemed_purch_v,
                "loyalty_discount_pct":    round(nc_discount_pct, 2),
                "avg_purchase_value":      round(nc_avg_purchase, 2),
                "avg_loyalty_redemption":  round(nc_avg_points, 2)
            },
            "is_full_range": is_full_range
        })

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
