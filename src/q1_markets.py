"""Q1: compare customer markets' revenue share across two halves.

P1 is Jul 1996–May 1997 and P2 is Jun 1997–Apr 1998.
"""

import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import common as c
from common import plt

QUIRK_ORDERS = [10248, 10249, 10260, 10808]


def load_orders(con):
    """Load one row per order with revenue, country, region and period.

    Args:
        con (sqlite3.Connection): Open Northwind database.

    Returns:
        pandas.DataFrame: Columns OrderID, OrderDate, CustomerID,
        Country, ShipCountry, revenue, period ("P1", "P2" or None)
        and Region.

    Raises:
        SystemExit: If a customer country is missing from
            ``REGION_MAP``.
    """
    sql = f"""
        SELECT o.OrderID, o.OrderDate, o.CustomerID, cu.Country, o.ShipCountry,
               SUM({c.REVENUE_SQL}) AS revenue
        FROM Orders o
        JOIN Customers cu ON cu.CustomerID = o.CustomerID
        JOIN "Orders Details" d ON d.OrderID = o.OrderID
        GROUP BY o.OrderID
    """
    df = pd.read_sql(sql, con)
    df["period"] = None
    df.loc[(df.OrderDate >= c.P1[0]) & (df.OrderDate < c.P1[1]), "period"] = "P1"
    df.loc[(df.OrderDate >= c.P2[0]) & (df.OrderDate < c.P2[1]), "period"] = "P2"
    unmapped = set(df.Country) - set(c.REGION_MAP)
    if unmapped:
        raise SystemExit(f"FAIL: countries missing from REGION_MAP: {sorted(unmapped)}")
    df["Region"] = df.Country.map(c.REGION_MAP)
    return df


def market_table(df, key):
    """Summarise revenue, orders and customers per market and period.

    Orders outside P1 and P2 are ignored, except in
    ``customers_total``, which counts every customer with an order.

    Args:
        df (pandas.DataFrame): Order rows from ``load_orders``.
        key (str): Market column, ``"Region"`` or ``"Country"``.

    Returns:
        pandas.DataFrame: One row per market, sorted by P2 share, with
        revenue, orders and customers per period, shares (%), share
        change (pp), revenue growth (%), customers_total and trend.
    """
    d = df[df.period.notna()]
    g = d.groupby([key, "period"]).agg(
        revenue=("revenue", "sum"), orders=("OrderID", "size"),
        customers=("CustomerID", "nunique"),
    ).unstack("period", fill_value=0)
    g.columns = [f"{m}_{p}" for m, p in g.columns]
    totals = d.groupby("period").revenue.sum()
    g["share_P1"] = 100 * g.revenue_P1 / totals["P1"]
    g["share_P2"] = 100 * g.revenue_P2 / totals["P2"]
    g["share_change_pp"] = g.share_P2 - g.share_P1
    g["revenue_growth_pct"] = 100 * (g.revenue_P2 / g.revenue_P1 - 1)
    g["customers_total"] = df.groupby(key).CustomerID.nunique()
    g["trend"] = g.share_change_pp.map(lambda x: "gained share" if x > 0 else "lost share")
    return g.reset_index().sort_values("share_P2", ascending=False)


def quirk_effect(df):
    """Measure how much the 4 quirk orders move the region results.

    Reassigns orders in ``QUIRK_ORDERS`` to their ship-to country's
    region and compares region shares with the base case.

    Args:
        df (pandas.DataFrame): Order rows from ``load_orders``.

    Returns:
        dict: The quirk order IDs, their revenue, the largest absolute
        change in any region share (pp), and whether any region's
        trend label flips.
    """
    alt = df.copy()
    mask = alt.OrderID.isin(QUIRK_ORDERS)
    alt.loc[mask, "Region"] = alt.loc[mask, "ShipCountry"].map(c.REGION_MAP)
    base = market_table(df, "Region").set_index("Region")
    moved = market_table(alt, "Region").set_index("Region").reindex(base.index)
    diff = (moved[["share_P1", "share_P2", "share_change_pp"]]
            - base[["share_P1", "share_P2", "share_change_pp"]]).abs()
    return {
        "quirk_orders": QUIRK_ORDERS,
        "quirk_revenue": round(float(df.loc[mask, "revenue"].sum()), 2),
        "max_share_shift_pp": round(float(diff.values.max()), 2),
        "changes_any_trend_label": bool((moved.trend != base.trend).any()),
    }


def chart_regions(reg):
    """Draw the P1-versus-P2 region share dot plot.

    Args:
        reg (pandas.DataFrame): Region table from ``market_table``.

    Returns:
        pathlib.Path: Path of ``q1_region_share.png``.
    """
    reg = reg.sort_values("share_P2")
    fig, ax = plt.subplots(figsize=(8, 3.8))
    y = range(len(reg))
    for i, r in zip(y, reg.itertuples()):
        ax.plot([r.share_P1, r.share_P2], [i, i], color=c.MUTED, lw=2, zorder=1)
        ax.annotate(f"revenue {r.revenue_growth_pct:+.0f}%",
                    (max(r.share_P1, r.share_P2), i), xytext=(10, 0),
                    textcoords="offset points", va="center", color=c.TEXT_2, fontsize=9)
    ax.scatter(reg.share_P1, y, s=60, color=c.MUTED, zorder=2,
               edgecolor=c.SURFACE, linewidth=2)
    ax.scatter(reg.share_P2, y, s=60, color=c.BLUE, zorder=3,
               edgecolor=c.SURFACE, linewidth=2)
    ax.set_yticks(list(y), reg.Region)
    ax.set_xlim(0, reg[["share_P1", "share_P2"]].values.max() * 1.25)
    ax.set_xlabel("Share of company revenue (%)")
    ax.grid(axis="y", visible=False)
    ax.set_title("Revenue share by customer region, first vs second 11 months")
    ax.legend(handles=[
        Line2D([], [], marker="o", ls="", color=c.MUTED, ms=8, label=f"P1: {c.P1_LABEL}"),
        Line2D([], [], marker="o", ls="", color=c.BLUE, ms=8, label=f"P2: {c.P2_LABEL}"),
    ], loc="lower right")
    return c.save_fig(fig, "q1_region_share.png")


def chart_countries(cty):
    """Draw the country share-change bar chart.

    Args:
        cty (pandas.DataFrame): Country rows from ``market_table``
            that pass the drill-down threshold.

    Returns:
        pathlib.Path: Path of ``q1_country_share_change.png``.
    """
    cty = cty.sort_values("share_change_pp")
    fig, ax = plt.subplots(figsize=(8, 4.6))
    colors = [c.BLUE if v > 0 else c.RED for v in cty.share_change_pp]
    labels = [f"{r.Country} ({r.customers_total} cust.)" for r in cty.itertuples()]
    ax.barh(labels, cty.share_change_pp, color=colors, height=0.6)
    ax.axvline(0, color=c.TEXT_2, lw=0.8)
    ax.set_xlabel("Change in share of company revenue, P1 → P2 (percentage points)")
    ax.grid(axis="y", visible=False)
    ax.set_title(f"Country share change (countries with ≥{c.Q1_MIN_ORDERS_PER_HALF} orders in each half)")
    ax.legend(handles=[Patch(color=c.BLUE, label="Gained share"),
                       Patch(color=c.RED, label="Lost share")], loc="lower right")
    return c.save_fig(fig, "q1_country_share_change.png")


def main():
    """Run the Q1 analysis and write its tables, figures and JSON.

    Args:
        None.

    Returns:
        None. Writes ``output/q1_*`` and ``docs/figures/q1_*``.

    Raises:
        AssertionError: If revenue or order totals fail to reconcile.
    """
    c.setup_style()
    con = c.connect()
    df = load_orders(con)
    con.close()

    n_p1, n_p2 = (df.period == "P1").sum(), (df.period == "P2").sum()
    n_excluded = int(df.period.isna().sum())
    rev_p1 = df.loc[df.period == "P1", "revenue"].sum()
    rev_p2 = df.loc[df.period == "P2", "revenue"].sum()

    reg = market_table(df, "Region")
    cty_all = market_table(df, "Country")
    k = c.Q1_MIN_ORDERS_PER_HALF
    cty = cty_all[(cty_all.orders_P1 >= k) & (cty_all.orders_P2 >= k)]

    # Verification (fail loudly).
    assert abs(reg.revenue_P1.sum() - rev_p1) < 0.01 and abs(reg.revenue_P2.sum() - rev_p2) < 0.01
    assert n_p1 + n_p2 + n_excluded == 830 and n_excluded == 14, (n_p1, n_p2, n_excluded)
    assert abs(reg.share_P1.sum() - 100) < 1e-6 and abs(reg.share_P2.sum() - 100) < 1e-6

    c.write_csv("q1_regions.csv", reg.round(2))
    c.write_csv("q1_countries_all.csv", cty_all.round(2))
    c.write_csv("q1_countries_drilldown.csv", cty.round(2))
    figs = [chart_regions(reg), chart_countries(cty)]

    cols = ["revenue_P1", "revenue_P2", "orders_P1", "orders_P2", "customers_P1",
            "customers_P2", "customers_total", "share_P1", "share_P2", "share_change_pp",
            "revenue_growth_pct", "trend"]
    rnd = lambda t, key: t.set_index(key)[cols].round(6).to_dict(orient="index")
    results = {
        "p1": {"label": c.P1_LABEL, "orders": int(n_p1), "revenue": round(rev_p1, 2)},
        "p2": {"label": c.P2_LABEL, "orders": int(n_p2), "revenue": round(rev_p2, 2)},
        "company_revenue_growth_pct": round(100 * (rev_p2 / rev_p1 - 1), 1),
        "excluded_orders_may_1998": n_excluded,
        "region_map": c.REGION_MAP,
        "regions": rnd(reg, "Region"),
        "country_min_orders_per_half": k,
        "countries_drilldown": rnd(cty, "Country"),
        "countries_all": rnd(cty_all, "Country"),
        "quirk_effect": quirk_effect(df),
        "figures": [str(f.relative_to(c.ROOT)) for f in figs],
    }
    c.write_json("q1_results.json", results)

    pd.set_option("display.width", 200)
    show = ["revenue_P1", "revenue_P2", "orders_P1", "orders_P2", "customers_total",
            "share_P1", "share_P2", "share_change_pp", "revenue_growth_pct"]
    print(f"Company revenue P1 {rev_p1:,.0f} -> P2 {rev_p2:,.0f} "
          f"({results['company_revenue_growth_pct']:+.1f}%); orders {n_p1} -> {n_p2}; "
          f"excluded May 1998 orders: {n_excluded}")
    print("\nRegions:\n", reg.set_index("Region")[show].round(1).to_string())
    print("\nCountry drill-down:\n", cty.set_index("Country")[show].round(1).to_string())
    print("\nQuirk orders effect:", results["quirk_effect"])


if __name__ == "__main__":
    main()
