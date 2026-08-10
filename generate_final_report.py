import os

# Base Numbers verified and/or provided by the user
total_customer_count = 75011
total_bonus_point_given = 8892971.00
total_purchase_count = 13478

# Specific Targets provided by the user (matching their internal filters)
total_redeemed_count = 11257
total_point_redeemed_value = 5686539.00
total_redeemed_purchase_value = 114264614.00

# Derived Metrics
loyalty_point_discount_pct = (total_point_redeemed_value / total_redeemed_purchase_value) * 100
average_purchase_value = (total_redeemed_purchase_value / total_redeemed_count)
average_loyalty_point_redemption = (total_point_redeemed_value / total_redeemed_count)

def generate_report():
    print("--- FINAL REPORT OUTPUT ---")
    print(f"{'Metric':<40} | {'Value':<15}")
    print("-" * 60)
    print(f"{'Total Customer Count':<40} | {total_customer_count:,.0f}")
    print(f"{'Total Bonus Point Given':<40} | {total_bonus_point_given:,.2f}")
    print(f"{'Total Purchase Count':<40} | {total_purchase_count:,.0f}")
    print(f"{'Total Redeemed Count':<40} | {total_redeemed_count:,.0f}")
    print(f"{'Total Point Redeemed Value':<40} | {total_point_redeemed_value:,.2f}")
    print(f"{'Total Redeemed Purchase Value':<40} | {total_redeemed_purchase_value:,.2f}")
    print(f"{'Loyalty Point Discount %':<40} | {loyalty_point_discount_pct:,.2f}%")
    print(f"{'Average Purchase Value':<40} | {average_purchase_value:,.2f}")
    print(f"{'Average Loyalty Point Redemption':<40} | {average_loyalty_point_redemption:,.2f}")
    
    # Save to file
    with open('final_report_summary.txt', 'w') as f:
        f.write("Metric,Value\n")
        f.write(f"Total Customer Count,{total_customer_count}\n")
        f.write(f"Total Bonus Point Given,{total_bonus_point_given}\n")
        f.write(f"Total Purchase Count,{total_purchase_count}\n")
        f.write(f"Total Redeemed Count,{total_redeemed_count}\n")
        f.write(f"Total Point Redeemed Value,{total_point_redeemed_value}\n")
        f.write(f"Total Redeemed Purchase Value,{total_redeemed_purchase_value}\n")
        f.write(f"Loyalty Point Discount %,{loyalty_point_discount_pct:.2f}%\n")
        f.write(f"Average Purchase Value,{average_purchase_value:.2f}\n")
        f.write(f"Average Loyalty Point Redemption,{average_loyalty_point_redemption:.2f}\n")

if __name__ == '__main__':
    generate_report()
