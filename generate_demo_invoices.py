import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time
import random

# Set random seed for reproducibility
np.random.seed(42)
random.seed(42)

# Generate 5000 invoices
num_invoices = 5000

# Invoice numbers: INV-0004 to INV-5003
invoice_numbers = [f"INV-{str(i).zfill(4)}" for i in range(4, 5004)]

# Invoice type: all "Sale Invoice"
invoice_types = ["Sale Invoice"] * num_invoices

# Invoice dates: distribute from 2026-05-07 to 2026-05-30 (24 days)
start_date = datetime(2026, 5, 7)
end_date = datetime(2026, 5, 30)
date_range = (end_date - start_date).days + 1
invoice_dates = [start_date + timedelta(days=random.randint(0, date_range - 1)) for _ in range(num_invoices)]

# Buyer information (all same)
buyer_ntn_cnic = ["4269497"] * num_invoices
buyer_business_name = ["Zubaida Associates"] * num_invoices
buyer_province = ["PUNJAB"] * num_invoices
buyer_address = ["456 Business Ave, punjab"] * num_invoices
buyer_registration_type = ["Registered"] * num_invoices

# Saved item codes: B2 to B47 (randomly selected)
item_codes = [f"B{i}" for i in range(2, 48)]
saved_item_codes = [random.choice(item_codes) for _ in range(num_invoices)]

# Quantity: random between 1 and 40
quantities = [random.randint(1, 40) for _ in range(num_invoices)]

# Value sales excluding ST: random between 10000 and 4500000
value_sales = [random.randint(10000, 4500000) for _ in range(num_invoices)]

# Fixed notified value or retail price: same as value_sales
fixed_notified_values = value_sales.copy()

# Further tax: 0 for all
further_tax = [0] * num_invoices

# Scheduled date: 5/8/2026 for all
scheduled_date = [datetime(2026, 5, 8)] * num_invoices

# Scheduled time: between 13:30 and 14:00 (30 minutes range)
def random_time_between(start_hour, start_min, end_hour, end_min):
    start_minutes = start_hour * 60 + start_min
    end_minutes = end_hour * 60 + end_min
    random_minutes = random.randint(start_minutes, end_minutes)
    hours = random_minutes // 60
    minutes = random_minutes % 60
    return time(hours, minutes)

scheduled_times = [random_time_between(13, 30, 14, 0) for _ in range(num_invoices)]

# Status and reason: NaN
status = [np.nan] * num_invoices
reason = [np.nan] * num_invoices

# Create DataFrame
df = pd.DataFrame({
    'invoice_number': invoice_numbers,
    'invoice_type': invoice_types,
    'invoice_date': [d.strftime('%Y-%m-%d') for d in invoice_dates],
    'buyer_ntn_cnic': buyer_ntn_cnic,
    'buyer_business_name': buyer_business_name,
    'buyer_province': buyer_province,
    'buyer_address': buyer_address,
    'buyer_registration_type': buyer_registration_type,
    'saved_item_code': saved_item_codes,
    'quantity': quantities,
    'value_sales_excluding_st': value_sales,
    'fixed_notified_value_or_retail_price': fixed_notified_values,
    'further_tax': further_tax,
    'scheduled_date': [d.strftime('%Y-%m-%d') for d in scheduled_date],
    'scheduled_time': scheduled_times,
    'status': status,
    'reason': reason
})

# Save to Excel
df.to_excel('demo_invoices.xlsx', index=False)

print(f"Generated {len(df)} demo invoices")
print(f"Invoice numbers: {df['invoice_number'].iloc[0]} to {df['invoice_number'].iloc[-1]}")
print(f"Invoice dates range: {df['invoice_date'].min()} to {df['invoice_date'].max()}")
print(f"Item codes: {sorted(df['saved_item_code'].unique())}")
print(f"Quantity range: {df['quantity'].min()} to {df['quantity'].max()}")
print(f"Value range: {df['value_sales_excluding_st'].min()} to {df['value_sales_excluding_st'].max()}")
print(f"Scheduled times range: {df['scheduled_time'].min()} to {df['scheduled_time'].max()}")
print(f"\nFirst 5 rows:")
print(df.head())
