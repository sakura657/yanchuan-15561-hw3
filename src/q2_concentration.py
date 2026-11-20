"""Q2: revenue by product category and customer concentration."""

import math

import numpy as np
import pandas as pd

import common as c
from common import plt

TOTAL_REVENUE_CHECK = 1265793.04
TOP_N = 10
TOP_PCT = 20


def category_table(con):
    """Compute revenue and share per category, overall and per half.

    Args:
        con (sqlite3.Connection): Open Northwind database.

    Returns:
        tuple[pandas.DataFrame, float]: The category table sorted by
        revenue (products, order lines, orders, overall and P1/P2
        shares in %, share change in pp), and total revenue.
    """
    sql = f"""
        SELECT cat.CategoryName AS category, o.OrderDate, {c.REVENUE_SQL} AS revenue,
               d.ProductID, d.OrderID
        FROM "Orders Details" d
        JOIN Product p ON p.ProductID = d.ProductID
        JOIN Categories cat ON cat.CategoryID = p.CategoryID
        JOIN Orders o ON o.OrderID = d.OrderID
    """
    lines = pd.read_sql(sql, con)
    total = lines.revenue.sum()
    g = lines.groupby("category").agg(
        revenue=("revenue", "sum"), products=("ProductID", "nunique"),
        order_lines=("revenue", "size"), orders=("OrderID", "nunique"))
    g["share_pct"] = 100 * g.revenue / total
    for name, (start, end) in {"P1": c.P1, "P2": c.P2}.items():
        sub = lines[(lines.OrderDate >= start) & (lines.OrderDate < end)]
        g[f"share_{name}_pct"] = 100 * sub.groupby("category").revenue.sum() / sub.revenue.sum()
    g["share_change_pp"] = g.share_P2_pct - g.share_P1_pct
    return g.reset_index().sort_values("revenue", ascending=False), total


def customer_pareto(con):
    """Rank customers by revenue and compute cumulative shares.

    Only customers with at least one order are included.

    Args:
        con (sqlite3.Connection): Open Northwind database.

    Returns:
        pandas.DataFrame: One row per customer, highest revenue first,
        with revenue, orders, first_order, rank, share_pct,
        cum_share_pct and cum_customers_pct.
    """
    sql = f"""
        SELECT o.CustomerID, cu.CompanyName, cu.Country, SUM({c.REVENUE_SQL}) AS revenue,
               COUNT(DISTINCT o.OrderID) AS orders, MIN(o.OrderDate) AS first_order
        FROM Orders o
        JOIN "Orders Details" d ON d.OrderID = o.OrderID
        JOIN Customers cu ON cu.CustomerID = o.CustomerID
        GROUP BY o.CustomerID
    """
    cust = pd.read_sql(sql, con).sort_values("revenue", ascending=False).reset_index(drop=True)
    cust["rank"] = cust.index + 1
    cust["share_pct"] = 100 * cust.revenue / cust.revenue.sum()
    cust["cum_share_pct"] = cust.share_pct.cumsum()
    cust["cum_customers_pct"] = 100 * cust["rank"] / len(cust)
    return cust


def n_to_reach(cust, pct):
    """Count the top customers needed to reach a share of revenue.

    Args:
        cust (pandas.DataFrame): Ranked table from ``customer_pareto``.
        pct (float): Target cumulative revenue share, in percent.

    Returns:
        int: Smallest number of top customers whose combined share is
        at least ``pct``.
    """
    return int((cust.cum_share_pct < pct).sum() + 1)


def chart_categories(cat):
    """Draw the revenue-by-category bar chart.

    Args:
        cat (pandas.DataFrame): Category table from ``category_table``.

    Returns:
        pathlib.Path: Path of ``q2_category_revenue.png``.
    """
    cat = cat.sort_values("revenue")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(cat.category, cat.revenue / 1000, color=c.BLUE, height=0.6)
    for r in cat.itertuples():
        ax.annotate(f"{r.share_pct:.1f}%", (r.revenue / 1000, r.category), xytext=(5, 0),
                    textcoords="offset points", va="center", color=c.TEXT_2, fontsize=9)
    ax.set_xlim(0, cat.revenue.max() / 1000 * 1.12)
    ax.set_xlabel("Revenue, Jul 1996–May 6, 1998 ($ thousands, net of discounts)")
    ax.grid(axis="y", visible=False)
    ax.set_title("Revenue by product category (label = share of total)")
    return c.save_fig(fig, "q2_category_revenue.png")


def chart_pareto(cust, top_n, top20_n):
    """Draw the customer Pareto curve with two marked points.

    Args:
        cust (pandas.DataFrame): Ranked table from ``customer_pareto``.
        top_n (int): Number of top customers to mark.
        top20_n (int): Number of customers in the top ``TOP_PCT``%.

    Returns:
        pathlib.Path: Path of ``q2_customer_pareto.png``.
    """
    fig, ax = plt.subplots(figsize=(7, 4.6))
    x = np.r_[0, cust.cum_customers_pct]
    y = np.r_[0, cust.cum_share_pct]
    ax.plot([0, 100], [0, 100], color=c.MUTED, lw=1.2, label="Equal share (every customer the same)")
    ax.plot(x, y, color=c.BLUE, lw=2, label="Actual: customers ranked by revenue")
    for n, text in [(top_n, f"Top {top_n} customers"), (top20_n, f"Top {TOP_PCT}% ({top20_n} customers)")]:
        px, py = cust.cum_customers_pct[n - 1], cust.cum_share_pct[n - 1]
        ax.scatter([px], [py], s=50, color=c.BLUE, edgecolor=c.SURFACE, linewidth=2, zorder=3)
        ax.annotate(f"{text}: {py:.0f}% of revenue", (px, py), xytext=(12, -14),
                    textcoords="offset points", color=c.TEXT, fontsize=9)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 102)
    ax.set_xlabel(f"Cumulative share of customers (%, n = {len(cust)} with orders)")
    ax.set_ylabel("Cumulative share of revenue (%)")
    ax.set_title("Customer concentration of revenue (Pareto curve)")
    ax.legend(loc="lower right")
    return c.save_fig(fig, "q2_customer_pareto.png")


def main():
    """Run the Q2 analysis and write its tables, figures and JSON.

    Args:
        None.

    Returns:
        None. Writes ``output/q2_*`` and ``docs/figures/q2_*``.

    Raises:
        AssertionError: If revenue totals or the customer count differ
            from the expected values.
    """
    c.setup_style()
    con = c.connect()
    cat, total = category_table(con)
    cust = customer_pareto(con)
    n_customers_all = con.execute("SELECT COUNT(*) FROM Customers").fetchone()[0]
    con.close()

    top_n = TOP_N
    top20_n = math.ceil(TOP_PCT / 100 * len(cust))
    top_share = float(cust.cum_share_pct[top_n - 1])
    top20_share = float(cust.cum_share_pct[top20_n - 1])

    # Verification (fail loudly).
    assert round(total, 2) == TOTAL_REVENUE_CHECK, total
    assert abs(cat.revenue.sum() - total) < 0.01
    assert abs(cust.cum_share_pct.iloc[-1] - 100) < 1e-9
    assert len(cust) == 89, len(cust)

    c.write_csv("q2_categories.csv", cat.round(2))
    c.write_csv("q2_customers_ranked.csv", cust.round(3))
    figs = [chart_categories(cat), chart_pareto(cust, top_n, top20_n)]

    results = {
        "window": "1996-07-04 to 1998-05-06",
        "total_revenue": round(total, 2),
        "categories": cat.set_index("category").round(6).to_dict(orient="index"),
        "top3_category_share_pct": round(float(cat.share_pct.head(3).sum()), 6),
        "customers_with_orders": len(cust),
        "customers_without_orders": n_customers_all - len(cust),
        "top_n": top_n, "top_n_share_pct": round(top_share, 6),
        "top_pct": TOP_PCT, "top20pct_n": top20_n, "top20pct_share_pct": round(top20_share, 6),
        "customers_for_50pct": n_to_reach(cust, 50),
        "customers_for_80pct": n_to_reach(cust, 80),
        "top_customer": {"name": cust.CompanyName[0], "country": cust.Country[0],
                         "share_pct": round(float(cust.share_pct[0]), 6)},
        "top10_customers": cust.head(top_n)[["rank", "CompanyName", "Country", "revenue",
                                             "orders", "share_pct", "first_order"]]
                               .round(6).to_dict(orient="records"),
        "bottom_half_n": len(cust) // 2,
        "bottom_half_share_pct": round(float(cust.share_pct.tail(len(cust) // 2).sum()), 6),
        "customers_first_order_after_p1": int((cust.first_order >= c.P1[1]).sum()),
        "figures": [str(f.relative_to(c.ROOT)) for f in figs],
    }
    c.write_json("q2_results.json", results)

    pd.set_option("display.width", 200)
    print(f"Total revenue {total:,.2f}")
    print("\nCategories:\n", cat.set_index("category").round(1).to_string())
    print(f"\nTop {top_n} customers: {top_share:.1f}% of revenue; "
          f"top 20% ({top20_n}): {top20_share:.1f}%; "
          f"customers for 50%: {results['customers_for_50pct']}, for 80%: {results['customers_for_80pct']}; "
          f"bottom half share: {results['bottom_half_share_pct']}%")
    print(f"Customers whose first order came after P1 (from Jun 1997): {results['customers_first_order_after_p1']}")
    print("\nTop 10 customers:\n", cust.head(top_n)[["rank", "CompanyName", "Country", "revenue",
          "orders", "share_pct", "first_order"]].round(1).to_string(index=False))


if __name__ == "__main__":
    main()
