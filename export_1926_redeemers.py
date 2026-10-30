import clickhouse_connect
import pandas as pd

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

    sd = '2026-07-01'
    ed = '2026-10-08'
    
    mob_re = _normalize_mob_expr('customer_mobile_number')

    cohort_filter = f"AND mob IN (SELECT {mob_re} FROM refer_point_data WHERE start_date >= '{sd}' AND start_date <= '{ed}')"
    date_filter = f"parsed_date >= '{sd}' AND parsed_date <= '{ed}'"

    query = f"""
        WITH
        {_re_sales_ctes()},
        valid_sales AS (
            SELECT mob, total_value, redemption
            FROM re_sales
            WHERE {date_filter} {cohort_filter}
        ),
        redeemers AS (
            SELECT DISTINCT mob FROM valid_sales WHERE redemption > 0
        )
        SELECT distinct mob as `Redeemer Mobile`
        FROM redeemers
    """

    print("Running query...")
    res = client.query(query)
    df = pd.DataFrame(res.result_rows, columns=['Redeemer Mobile'])
    
    filename = 'Redeemers_1926_July1_Oct8.xlsx'
    df.to_excel(filename, index=False)
    print(f"Total Rows: {len(df)}")
    print(f"Saved to {filename}")

if __name__ == '__main__':
    run()
