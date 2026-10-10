import clickhouse_connect

def _normalize_mob_expr(col):
    d = f"replaceRegexpAll(toString(coalesce({col}, '')), '[^0-9]', '')"
    return (
        f"multiIf("
        f"  length({d}) = 12 AND startsWith({d}, '91'), substr({d}, 3), "
        f"  length({d}) = 11 AND startsWith({d}, '0'),  substr({d}, 2), "
        f"  {d}"
        f")"
    )

def _re_sales_ctes():
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

def run():
    client = clickhouse_connect.get_client(
        host='pdhsuv47ec.ap-south-1.aws.clickhouse.cloud',
        port=8443,
        username='default',
        password='ZFlujj9SA_Iei',
        secure=True
    )

    sd = '2026-09-01'
    ed = '2026-10-08'

    q = f"""
        WITH {_re_sales_ctes()},
        new_customers AS (
            SELECT distinct if(endsWith(customer_mobile_number, '.0'), substr(customer_mobile_number, 1, length(customer_mobile_number) - 2), customer_mobile_number) as mob
            FROM refer_point_data
            WHERE start_date >= '{sd}' AND start_date <= '{ed}'
        ),
        valid_sales AS (
            SELECT mob
            FROM re_sales
            WHERE parsed_date >= '{sd}' AND parsed_date <= '{ed}'
        )
        SELECT 
            (SELECT count() FROM new_customers) as joined_in_period,
            (SELECT count(distinct mob) FROM valid_sales) as total_purchasers_in_period,
            (SELECT count(distinct mob) FROM valid_sales WHERE mob IN (SELECT mob FROM new_customers)) as intersection_count
    """
    
    res = client.query(q).result_rows[0]
    print(f"Customers who joined between Sep 1 and Oct 8: {res[0]}")
    print(f"Total Program members who purchased between Sep 1 and Oct 8: {res[1]}")
    print(f"Customers who BOTH joined in that period AND purchased in that period: {res[2]}")

if __name__ == '__main__':
    run()
