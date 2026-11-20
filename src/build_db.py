"""Build data/northwind.db from the Northwind Google Sheet snapshot.

Run from anywhere with ``python src/build_db.py``.
"""

import json
import sqlite3
import sys
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SOURCE_XLSX = DATA_DIR / "northwind_source.xlsx"
DB_PATH = DATA_DIR / "northwind.db"
SOURCE_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1mD4Hn4NZdJlXMC4EJcSp27vg-_jbxUYJ95vQvMbSpVM/export?format=xlsx"
)

EXPECTED_TABS = {
    "Categories", "Customers", "Employees", "Orders Details",
    "Orders", "Shippers", "Product", "Suppliers",
}
# Leftover classroom-exercise columns in the Product tab; not part of Northwind.
PRODUCT_JUNK_COLS = ["Cheap", "NewPrice", "Cheap.1", "IsCheap", "Unnamed: 14", "NewPrice.1"]

EXPECTED_ORDERS = 830
EXPECTED_ORDER_LINES = 2155
EXPECTED_CUSTOMERS = 91
EXPECTED_PRODUCTS = 77
EXPECTED_FIRST_ORDER = "1996-07-04"
EXPECTED_LAST_ORDER = "1998-05-06"


def ensure_snapshot():
    """Download the source workbook if the local snapshot is missing.

    Args:
        None.

    Returns:
        None. Writes ``data/northwind_source.xlsx`` only when absent.
    """
    if SOURCE_XLSX.exists():
        print(f"Using existing snapshot: {SOURCE_XLSX.relative_to(ROOT)}")
        return
    print(f"Snapshot missing; downloading from Google Sheets to {SOURCE_XLSX.relative_to(ROOT)}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = SOURCE_XLSX.with_suffix(".xlsx.part")
    urllib.request.urlretrieve(SOURCE_URL, tmp)
    tmp.replace(SOURCE_XLSX)


def load_tabs():
    """Load every workbook tab and clean it for SQLite.

    Drops the leftover exercise columns from ``Product`` and converts
    date columns to ISO ``YYYY-MM-DD`` text.

    Args:
        None.

    Returns:
        dict[str, pandas.DataFrame]: One DataFrame per tab, keyed by
        tab name.

    Raises:
        SystemExit: If the tab names differ from ``EXPECTED_TABS`` or a
            date column holds a time of day.
    """
    tabs = pd.read_excel(SOURCE_XLSX, sheet_name=None, engine="openpyxl")
    found = set(tabs)
    if found != EXPECTED_TABS:
        sys.exit(
            "FAIL: workbook tabs do not match.\n"
            f"  missing: {sorted(EXPECTED_TABS - found)}\n"
            f"  unexpected: {sorted(found - EXPECTED_TABS)}"
        )

    product = tabs["Product"]
    missing_junk = [c for c in PRODUCT_JUNK_COLS if c not in product.columns]
    if missing_junk:
        print(f"Note: expected leftover Product columns not found: {missing_junk}")
    tabs["Product"] = product.drop(columns=PRODUCT_JUNK_COLS, errors="ignore")

    # Store dates as ISO 'YYYY-MM-DD' text so SQLite date functions work directly.
    for name, df in tabs.items():
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                has_time = (df[col].dropna() != df[col].dropna().dt.normalize()).any()
                if has_time:
                    sys.exit(f"FAIL: {name}.{col} has time-of-day values; refusing to truncate.")
                df[col] = df[col].dt.strftime("%Y-%m-%d")
    return tabs


def write_db(tabs):
    """Write all tabs to a temporary SQLite file.

    Args:
        tabs (dict[str, pandas.DataFrame]): Tables keyed by table name.

    Returns:
        pathlib.Path: The temporary ``northwind.db.part`` file; any
        earlier copy of it is deleted first.
    """
    tmp = DB_PATH.with_suffix(".db.part")
    tmp.unlink(missing_ok=True)
    with sqlite3.connect(tmp) as con:
        for name, df in tabs.items():
            df.to_sql(name, con, index=False)
    con.close()
    return tmp


def validate(db_file):
    """Check the required row counts and order-date range.

    Prints a PASS or FAIL line for each check.

    Args:
        db_file (pathlib.Path): SQLite database to check.

    Returns:
        list[str]: One message per failed check; empty if all pass.
    """
    con = sqlite3.connect(db_file)
    q = lambda sql: con.execute(sql).fetchone()
    checks = [
        ("orders", q('SELECT COUNT(*) FROM "Orders"')[0], EXPECTED_ORDERS),
        ("order lines", q('SELECT COUNT(*) FROM "Orders Details"')[0], EXPECTED_ORDER_LINES),
        ("customers", q('SELECT COUNT(*) FROM "Customers"')[0], EXPECTED_CUSTOMERS),
        ("products", q('SELECT COUNT(*) FROM "Product"')[0], EXPECTED_PRODUCTS),
        ("first OrderDate", q('SELECT MIN(OrderDate) FROM "Orders"')[0], EXPECTED_FIRST_ORDER),
        ("last OrderDate", q('SELECT MAX(OrderDate) FROM "Orders"')[0], EXPECTED_LAST_ORDER),
    ]
    con.close()

    failures = []
    print("\nValidation:")
    for label, actual, expected in checks:
        ok = actual == expected
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}: {actual} (expected {expected})")
        if not ok:
            failures.append(f"{label}: got {actual}, expected {expected}")
    return failures


def write_summary():
    """Write the dataset facts quoted on the webpage.

    Args:
        None.

    Returns:
        None. Writes ``output/data_summary.json`` from ``DB_PATH``.
    """
    con = sqlite3.connect(DB_PATH)
    one = lambda sql: con.execute(sql).fetchone()[0]
    summary = {
        "orders": one('SELECT COUNT(*) FROM "Orders"'),
        "order_lines": one('SELECT COUNT(*) FROM "Orders Details"'),
        "customers": one('SELECT COUNT(*) FROM "Customers"'),
        "customer_countries": one('SELECT COUNT(DISTINCT Country) FROM "Customers"'),
        "products": one('SELECT COUNT(*) FROM "Product"'),
        "categories": one('SELECT COUNT(*) FROM "Categories"'),
        "shippers": one('SELECT COUNT(*) FROM "Shippers"'),
        "first_order": one('SELECT MIN(OrderDate) FROM "Orders"'),
        "last_order": one('SELECT MAX(OrderDate) FROM "Orders"'),
        "unshipped_orders": one('SELECT COUNT(*) FROM "Orders" WHERE ShippedDate IS NULL'),
        "lines_price_differs_from_list": one(
            'SELECT COUNT(*) FROM "Orders Details" d JOIN "Product" p USING(ProductID) '
            "WHERE d.UnitPrice <> p.Price"),
        "orders_customer_country_differs_from_ship_country": one(
            'SELECT COUNT(*) FROM "Orders" o JOIN "Customers" c USING(CustomerID) '
            "WHERE c.Country <> o.ShipCountry"),
    }
    con.close()
    out = ROOT / "output"
    out.mkdir(exist_ok=True)
    (out / "data_summary.json").write_text(json.dumps(summary, indent=2))


def main():
    """Build, validate and save the database and its summary.

    Args:
        None.

    Returns:
        None.

    Raises:
        SystemExit: If any validation check fails; the old database is
            deleted so later scripts cannot use it.
    """
    ensure_snapshot()
    tabs = load_tabs()
    tmp_db = write_db(tabs)
    failures = validate(tmp_db)
    if failures:
        tmp_db.unlink(missing_ok=True)
        DB_PATH.unlink(missing_ok=True)  # never leave a stale db for later scripts
        sys.exit("\nFAIL: database not written. " + "; ".join(failures))
    tmp_db.replace(DB_PATH)
    write_summary()
    print("\nTables written:")
    for name, df in tabs.items():
        print(f"  {name:<15} {len(df):>5} rows, {df.shape[1]:>2} cols")
    print(f"\nOK: wrote {DB_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
