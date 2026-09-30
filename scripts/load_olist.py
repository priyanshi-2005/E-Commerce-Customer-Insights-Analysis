#!/usr/bin/env python3
"""Load Olist CSV files into QueryQuest SQLite database."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "queryquest.db"
SCHEMA_PATH = ROOT / "schema" / "01_schema.sql"
VIEWS_PATH = ROOT / "views" / "kpi_views.sql"

FILE_MAP = {
    "customers": "olist_customers_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "products": "olist_products_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
}


def run_sql_file(conn: sqlite3.Connection, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    conn.executescript(sql)


def load_table(conn: sqlite3.Connection, table: str, filename: str) -> int:
    csv_path = RAW_DIR / filename
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing CSV: {csv_path}")

    df = pd.read_csv(csv_path)
    df.to_sql(table, conn, if_exists="append", index=False)
    return len(df)


def main() -> None:
    if not RAW_DIR.exists():
        raise SystemExit(
            "data/raw/ not found.\n"
            "Download Olist from Kaggle and unzip CSVs into data/raw/."
        )

    missing = [name for name in FILE_MAP.values() if not (RAW_DIR / name).exists()]
    if missing:
        raise SystemExit("Missing files in data/raw/:\n- " + "\n- ".join(missing))

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    with sqlite3.connect(DB_PATH) as conn:
        run_sql_file(conn, SCHEMA_PATH)

        for table, filename in FILE_MAP.items():
            rows = load_table(conn, table, filename)
            print(f"Loaded {table}: {rows:,} rows")

        run_sql_file(conn, VIEWS_PATH)
        conn.commit()

    print(f"\nDone. Database ready at {DB_PATH}")


if __name__ == "__main__":
    main()
