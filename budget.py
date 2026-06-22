import pandas as pd
from sqlalchemy import create_engine
import os
from stuff import DBUSER, DBPSWD, DBIP

DB_PORT = "3306"
DB_NAME = "budget"

engine = create_engine(
    f"mysql+pymysql://{DBUSER}:{DBPSWD}@{DBIP}:{DB_PORT}/{DB_NAME}"
)

def post_to_sql(df, table):
    df.to_sql(
    table,
    engine,
    if_exists="replace",
    index=False
)

main = pd.read_csv('main.csv')
main['Account'] = "Main"

bills = pd.read_csv('bills.csv')
bills['Account'] = "Bills"

savings = pd.read_csv('savings.csv')
savings['Account'] = "Main Savings"

full = pd.concat([bills, main, savings])

full['Date'] = pd.to_datetime(full['Date'])

df_clean = full[full["Category"] != "Transfer"].copy()

df_clean["month"] = df_clean["Date"].dt.to_period("M")

monthly = (
    df_clean
    .groupby("month")
    .agg(
        income=("Amount", lambda x: x[x > 0].sum()),
        expenses=("Amount", lambda x: abs(x[x < 0].sum()))
    )
    .reset_index()
)

monthly["month"] = monthly["month"].astype(str)

monthly['overunder'] = monthly['income'] - monthly['expenses']

# Only expenses
expenses_df = df_clean[df_clean["Amount"] < 0].copy()

# Sum expenses by Month and Category
monthly_category_df = (
    expenses_df
    .groupby(["month", "Category"], as_index=False)["Amount"]
    .sum()
)
monthly_category_df.sort_values(by="month", ascending=True, inplace=True)

patterns = ["Therapy Trails", "Childcare"]

regex = "|".join(patterns)

filtered_df = df_clean[~df_clean["Description"].str.contains(regex, regex=True, na=False)]

filtered_monthly = (
    filtered_df
    .groupby("month")
    .agg(
        income=("Amount", lambda x: x[x > 0].sum()),
        expenses=("Amount", lambda x: abs(x[x < 0].sum()))
    )
    .reset_index()
)

filtered_monthly["month"] = filtered_monthly["month"].astype(str)

filtered_monthly['overunder'] = filtered_monthly['income'] - filtered_monthly['expenses']

total = monthly['income'].sum() - monthly['expenses'].sum()

filtered_total = filtered_monthly['income'].sum() - filtered_monthly['expenses'].sum()

post_to_sql(df_clean, "clean")

post_to_sql(full, "full")

post_to_sql(filtered_df, "filtered")

post_to_sql(filtered_monthly, "filtered_monthly")

post_to_sql(monthly, "monthly")

post_to_sql(monthly_category_df, "month_by_category")