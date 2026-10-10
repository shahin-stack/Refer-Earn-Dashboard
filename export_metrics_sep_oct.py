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

    sd = '2026-09-01'
    ed = '2026-10-08'

    # 1. Total Customers for range
    q1 = f"""
        SELECT distinct if(endsWith(customer_mobile_number, '.0'), substr(customer_mobile_number, 1, length(customer_mobile_number) - 2), customer_mobile_number) as mob
        FROM refer_point_data
        WHERE start_date >= '{sd}' AND start_date <= '{ed}'
    """
    res1 = client.query(q1)
    df1 = pd.DataFrame(res1.result_rows, columns=['Customer Mobile'])
    print(f"Total Customers Count ({sd} to {ed}): {len(df1)}")

    # 2. Total Purchase for range
    q2 = f"""
        WITH {_re_sales_ctes()},
        valid_sales AS (
            SELECT mob, total_value, redemption
            FROM re_sales
            WHERE parsed_date >= '{sd}' AND parsed_date <= '{ed}'
        )
        SELECT distinct mob FROM valid_sales
    """
    res2 = client.query(q2)
    df2 = pd.DataFrame(res2.result_rows, columns=['Purchaser Mobile'])
    print(f"Total Purchase Count ({sd} to {ed}): {len(df2)}")

    # 3. Total Redeemed for range
    q3 = f"""
        WITH {_re_sales_ctes()},
        valid_sales AS (
            SELECT mob, total_value, redemption
            FROM re_sales
            WHERE parsed_date >= '{sd}' AND parsed_date <= '{ed}'
        ),
        redeemers AS (
            SELECT DISTINCT mob FROM valid_sales WHERE redemption > 0
        )
        SELECT distinct mob FROM redeemers
    """
    res3 = client.query(q3)
    df3 = pd.DataFrame(res3.result_rows, columns=['Redeemer Mobile'])
    print(f"Total Redeemed Count ({sd} to {ed}): {len(df3)}")

    filename = 'Customer_Metrics_Sep1_Oct8.xlsx'
    with pd.ExcelWriter(filename) as writer:
        df1.to_excel(writer, sheet_name='Total Customers', index=False)
        df2.to_excel(writer, sheet_name='Total Purchases', index=False)
        df3.to_excel(writer, sheet_name='Total Redeemers', index=False)
    
    print(f"Saved to {filename}")

if __name__ == '__main__':
    run()
