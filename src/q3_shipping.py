"""Q3: compare shippers on days to ship and late shipments."""

import numpy as np
import pandas as pd

import common as c
from common import plt

N_BOOT = 10_000
SLOW_DAYS = 14  # an order taking longer than this counts as a slow shipment
SEED = 561


def load_orders(con):
    """Load one row per order with shipper and timing fields.

    Args:
        con (sqlite3.Connection): Open Northwind database.

    Returns:
        pandas.DataFrame: Order rows with shipper, open, lead_days,
        days_to_ship, late, days_late and open_overdue. For open
        orders the timing fields are NaN and ``late`` is False.
    """
    sql = """
        SELECT o.OrderID, o.OrderDate, o.RequiredDate, o.ShippedDate, o.Freight,
               s.CompanyName AS shipper
        FROM Orders o JOIN Shippers s ON s.ShipperID = o.ShipVia
    """
    df = pd.read_sql(sql, con, parse_dates=["OrderDate", "RequiredDate", "ShippedDate"])
    df["open"] = df.ShippedDate.isna()
    df["lead_days"] = (df.RequiredDate - df.OrderDate).dt.days
    df["days_to_ship"] = (df.ShippedDate - df.OrderDate).dt.days
    df["late"] = df.ShippedDate > df.RequiredDate
    df["days_late"] = (df.ShippedDate - df.RequiredDate).dt.days.where(df.late)
    df["open_overdue"] = df.open & (df.RequiredDate < pd.Timestamp(c.DATA_END))
    return df


def wilson(k, n, z=1.96):
    """Compute the Wilson score interval for a proportion.

    Args:
        k (int): Number of successes.
        n (int): Number of trials; must be positive.
        z (float): Normal quantile; the default gives a 95% interval.

    Returns:
        tuple[float, float]: Lower and upper bounds, in percent.
    """
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return 100 * (centre - half), 100 * (centre + half)


def boot_median_ci(values, rng):
    """Bootstrap a 95% confidence interval for the median.

    Uses ``N_BOOT`` resamples with replacement.

    Args:
        values (array-like): Observations, e.g. days to ship.
        rng (numpy.random.Generator): Random generator; advanced by
            the call.

    Returns:
        tuple[float, float]: 2.5th and 97.5th percentiles of the
        bootstrap medians.
    """
    v = np.asarray(values)
    meds = np.median(rng.choice(v, size=(N_BOOT, len(v)), replace=True), axis=1)
    return tuple(np.percentile(meds, [2.5, 97.5]))


def shipper_table(df):
    """Compute timing and lateness metrics for each shipper.

    Bootstrap intervals use a generator seeded with ``SEED``, so the
    results are reproducible.

    Args:
        df (pandas.DataFrame): Order rows from ``load_orders``.

    Returns:
        pandas.DataFrame: One row per shipper, slowest median first,
        with counts, median/mean/p90 days, slow and late rates (%)
        with Wilson intervals, lead-time mix, the 28-day late rate and
        average freight.
    """
    rng = np.random.default_rng(SEED)
    rows = []
    for name, g in df.groupby("shipper"):
        s = g[~g.open]
        s28 = s[s.lead_days == 28]
        lo, hi = wilson(s.late.sum(), len(s))
        slow_lo, slow_hi = wilson((s.days_to_ship > SLOW_DAYS).sum(), len(s))
        mlo, mhi = boot_median_ci(s.days_to_ship, rng)
        rows.append({
            "shipper": name, "orders": len(g), "shipped": len(s), "open": int(g.open.sum()),
            "median_days": float(s.days_to_ship.median()),
            "median_ci_lo": mlo, "median_ci_hi": mhi,
            "mean_days": s.days_to_ship.mean(), "p90_days": s.days_to_ship.quantile(0.9),
            "slow_pct": 100 * (s.days_to_ship > SLOW_DAYS).mean(),
            "slow_ci_lo": slow_lo, "slow_ci_hi": slow_hi,
            "late": int(s.late.sum()), "late_pct": 100 * s.late.mean(),
            "late_ci_lo": lo, "late_ci_hi": hi,
            "avg_days_late": s.days_late.mean(),
            "lead14_orders": int((s.lead_days == 14).sum()),
            "lead28_orders": len(s28), "lead42_orders": int((s.lead_days == 42).sum()),
            "late_pct_28day": 100 * s28.late.mean(), "late_28day": int(s28.late.sum()),
            "avg_freight": s.Freight.mean(),
        })
    return pd.DataFrame(rows).sort_values("median_days", ascending=False)


def lead_time_table(df):
    """Summarise shipped orders by promised lead time.

    Args:
        df (pandas.DataFrame): Order rows from ``load_orders``.

    Returns:
        pandas.DataFrame: One row per lead time in days, with shipped,
        late, median_days and late_pct.
    """
    s = df[~df.open]
    g = s.groupby("lead_days").agg(shipped=("OrderID", "size"), late=("late", "sum"),
                                   median_days=("days_to_ship", "median"))
    g["late_pct"] = 100 * g.late / g.shipped
    return g.reset_index()


def chart_box(df, order):
    """Draw the days-to-ship box plot by shipper.

    Args:
        df (pandas.DataFrame): Order rows from ``load_orders``.
        order (list[str]): Shipper names, drawn bottom to top.

    Returns:
        pathlib.Path: Path of ``q3_days_to_ship_box.png``.
    """
    s = df[~df.open]
    data = [s.loc[s.shipper == name, "days_to_ship"].values for name in order]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    bp = ax.boxplot(data, vert=False, widths=0.5, patch_artist=True, whis=(5, 95),
                    medianprops={"color": c.TEXT, "lw": 2},
                    boxprops={"facecolor": "#cde2fb", "edgecolor": c.BLUE},
                    whiskerprops={"color": c.BLUE}, capprops={"color": c.BLUE},
                    flierprops={"marker": "o", "markersize": 4, "markerfacecolor": c.BLUE,
                                "markeredgecolor": c.SURFACE, "alpha": 0.8})
    ax.set_yticks(range(1, len(order) + 1),
                  [f"{n}\n(n = {len(d)})" for n, d in zip(order, data)])
    pct28 = 100 * (s.lead_days == 28).mean()
    ax.axvline(28, color=c.RED, lw=1.2)
    ax.annotate(f"28 days: standard promised\nlead time ({pct28:.0f}% of orders)", (28, len(order) + 0.45),
                xytext=(4, 0), textcoords="offset points", color=c.TEXT_2, fontsize=8, va="top")
    ax.set_xlabel("Days from order to shipment (calendar days)")
    ax.set_xlim(0, s.days_to_ship.max() + 2)
    ax.grid(axis="y", visible=False)
    ax.set_title("Days to ship by shipper (shipped orders only)")
    ax.text(0, -0.28, "Box = middle 50% of orders, line = median, whiskers = 5th–95th percentile, "
            "dots = slowest/fastest 5%.", transform=ax.transAxes, color=c.TEXT_2, fontsize=8)
    return c.save_fig(fig, "q3_days_to_ship_box.png")


def main():
    """Run the Q3 analysis and write its tables, figure and JSON.

    Args:
        None.

    Returns:
        None. Writes ``output/q3_*`` and ``docs/figures/q3_*``.

    Raises:
        AssertionError: If order, late or per-shipper counts differ
            from the expected values.
    """
    c.setup_style()
    con = c.connect()
    df = load_orders(con)
    con.close()

    shipped = df[~df.open]
    tab = shipper_table(df)
    lead = lead_time_table(df)

    # Verification (fail loudly).
    assert len(shipped) + df.open.sum() == 830 and df.open.sum() == 21
    assert int(shipped.late.sum()) == 37, shipped.late.sum()
    assert (shipped.days_to_ship >= 0).all()
    expected = {"United Package": (326, 315, 16, 11), "Federal Shipping": (255, 249, 9, 6),
                "Speedy Express": (249, 245, 12, 4)}
    for r in tab.itertuples():
        assert (r.orders, r.shipped, r.late, r.open) == expected[r.shipper], r

    order = list(tab.shipper[::-1])  # slowest median at top of the chart
    figs = [chart_box(df, order)]
    c.write_csv("q3_shippers.csv", tab.round(2))
    c.write_csv("q3_lead_time.csv", lead.round(2))

    ci_overlap = tab.late_ci_lo.max() < tab.late_ci_hi.min()
    results = {
        "shipped_orders": len(shipped), "open_orders": int(df.open.sum()),
        "open_order_dates": [str(df.loc[df.open, "OrderDate"].min().date()),
                             str(df.loc[df.open, "OrderDate"].max().date())],
        "open_overdue_at_data_end": int(df.open_overdue.sum()),
        "overall": {
            "median_days": float(shipped.days_to_ship.median()),
            "mean_days": round(float(shipped.days_to_ship.mean()), 1),
            "p90_days": float(shipped.days_to_ship.quantile(0.9)),
            "late": int(shipped.late.sum()),
            "late_pct": round(100 * float(shipped.late.mean()), 6),
            "avg_days_late": round(float(shipped.days_late.mean()), 1),
        },
        "shippers": tab.set_index("shipper").round(6).to_dict(orient="index"),
        "lead_time": lead.round(6).to_dict(orient="records"),
        "late_rate_cis_all_overlap": bool(ci_overlap),
        "slow_threshold_days": SLOW_DAYS,
        "bootstrap": {"n": N_BOOT, "seed": SEED},
        "figures": [str(f.relative_to(c.ROOT)) for f in figs],
    }
    c.write_json("q3_results.json", results)

    pd.set_option("display.width", 220)
    print("Overall:", results["overall"], "| open:", results["open_orders"],
          "| open overdue at data end:", results["open_overdue_at_data_end"])
    print("\nShippers:\n", tab.set_index("shipper").round(1).T.to_string())
    print("\nBy promised lead time:\n", lead.round(1).to_string(index=False))
    print("\nAll three late-rate 95% CIs overlap:", ci_overlap)


if __name__ == "__main__":
    main()
