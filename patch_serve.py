with open('serve.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_func = """def get_ch_client():
    import clickhouse_connect
    return clickhouse_connect.get_client(
        host='pdhsuv47ec.ap-south-1.aws.clickhouse.cloud',
        port=8443,
        username='default',
        password='ZFlujj9SA_Iei',
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

    master_query = \"\"\"
        SELECT 
            count(distinct if(endsWith(customer_mobile_number, '.0'), substr(customer_mobile_number, 1, length(customer_mobile_number) - 2), customer_mobile_number)) as total_customers,
            sum(bonus_points) as total_bonus
        FROM refer_point_data
    \"\"\"
    try:
        master_res = client.query(master_query).result_rows[0]
        master_total_customer_count = int(master_res[0])
        master_total_bonus_point_given = float(master_res[1])
    except Exception as e:
        print("Clickhouse master query error:", e)
        master_total_customer_count = 0
        master_total_bonus_point_given = 0.0

    is_full_range = False
    date_filter = "parsed_date >= '2026-01-01'"
    if not start_date or not end_date:
        is_full_range = True
    else:
        from datetime import datetime
        try:
            sd = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y-%m-%d')
            ed = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y-%m-%d')
            date_filter += f" AND parsed_date >= '{sd}' AND parsed_date <= '{ed}'"
        except Exception:
            return jsonify({"error": "Invalid date format"}), 400

    range_query = f\"\"\"
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
    \"\"\"
    
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
    })\n"""

new_content = lines[:49] + [new_func] + lines[178:]

with open('serve.py', 'w', encoding='utf-8') as f:
    f.writelines(new_content)

print("Patch applied to serve.py")
