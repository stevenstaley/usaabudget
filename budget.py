import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine
from stuff import DBIP, DBPSWD, DBUSER

DB_PORT = "3306"
DB_NAME = "budget"
CSV_FILES = {
    "main": ("main.csv", "Main"),
    "bills": ("bills.csv", "Bills"),
    "savings": ("savings.csv", "Main Savings"),
}
FILTER_PATTERNS = ["Therapy Trails", "Childcare"]


def build_engine(user: str, password: str, host: str, port: str, database: str):
    url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    return create_engine(url)


def read_budget_files(data_dir: Path) -> pd.DataFrame:
    frames = []
    for _, (filename, account) in CSV_FILES.items():
        csv_path = data_dir / filename
        df = pd.read_csv(csv_path)
        df["Account"] = account
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def normalize_dates(df: pd.DataFrame, date_column: str = "Date") -> pd.DataFrame:
    df = df.copy()
    df[date_column] = pd.to_datetime(df[date_column])
    return df


def drop_transfers(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["Category"] != "Transfer"].copy()


def add_month_column(df: pd.DataFrame, date_column: str = "Date") -> pd.DataFrame:
    df = df.copy()
    df["month"] = df[date_column].dt.to_period("M")
    df["time"] = df["month"].dt.to_timestamp()
    return df


def summarize_monthly(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby("month")
        .agg(
            income=("Amount", lambda x: x[x > 0].sum()),
            expenses=("Amount", lambda x: abs(x[x < 0].sum()))
        )
        .reset_index()
    )
    summary["month"] = summary["month"].astype(str)
    summary["overunder"] = summary["income"] - summary["expenses"]
    return summary


def filter_descriptions(df: pd.DataFrame, patterns: list[str]) -> pd.DataFrame:
    regex = "|".join(patterns)
    return df[~df["Description"].str.contains(regex, regex=True, na=False)].copy()


def summarize_expenses_by_category(df: pd.DataFrame) -> pd.DataFrame:
    expenses = df[df["Amount"] < 0].copy()
    summary = (
        expenses.groupby(["month", "Category"], as_index=False)["Amount"].sum()
    )
    summary["time"] = summary["month"].dt.to_timestamp()
    return summary.sort_values(by="month", ascending=True).reset_index(drop=True)


def post_to_sql(df: pd.DataFrame, table_name: str, engine) -> None:
    df.to_sql(table_name, engine, if_exists="replace", index=False)


def main() -> dict[str, pd.DataFrame]:
    project_root = Path(__file__).resolve().parent
    engine = build_engine(DBUSER, DBPSWD, DBIP, DB_PORT, DB_NAME)

    full_df = read_budget_files(project_root)
    full_df = normalize_dates(full_df)
    clean_df = drop_transfers(full_df)
    clean_df = add_month_column(clean_df)

    monthly_summary = summarize_monthly(clean_df)
    filtered_df = filter_descriptions(clean_df, FILTER_PATTERNS)
    filtered_monthly = summarize_monthly(filtered_df)
    monthly_category_df = summarize_expenses_by_category(clean_df)

    post_to_sql(clean_df, "clean", engine)
    post_to_sql(full_df, "full", engine)
    post_to_sql(filtered_df, "filtered", engine)
    post_to_sql(filtered_monthly, "filtered_monthly", engine)
    post_to_sql(monthly_summary, "monthly", engine)
    post_to_sql(monthly_category_df, "month_by_category", engine)

    return {
        "monthly_summary": monthly_summary,
        "filtered_monthly": filtered_monthly,
        "monthly_category": monthly_category_df,
    }


if __name__ == "__main__":
    main()

print("Budget data processed and uploaded to SQL database.")
