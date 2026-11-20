"""Generate docs/index.html from the JSON files in output/.

Page prose lives in ``q1_section``, ``q2_section`` and ``q3_section``.
"""

import json
from datetime import date
from html import escape

from common import OUTPUT_DIR, ROOT

DOCS = ROOT / "docs"
REPO_URL = "https://github.com/sakura657/yanchuan-15561-hw3"
MINUS = "\u2212"
SMALL_MARKET_MAX = 2  # countries with this many customers or fewer are flagged as small


# ---------- formatting helpers ----------

def load(name):
    """Read one analysis results file.

    Args:
        name (str): JSON file name inside ``output/``.

    Returns:
        dict: Parsed contents.

    Raises:
        SystemExit: If the file does not exist yet.
    """
    path = OUTPUT_DIR / name
    if not path.exists():
        raise SystemExit(f"{path} not found. Run: python run_all.py")
    return json.loads(path.read_text())


def money(x):
    """Format a dollar amount in thousands or millions.

    Args:
        x (float): Amount in dollars.

    Returns:
        str: E.g. ``"$453k"``, or ``"$1.27M"`` from one million up.
    """
    return f"${x / 1e6:.2f}M" if abs(x) >= 1e6 else f"${x / 1e3:,.0f}k"


def pct(x, d=1):
    """Format a percentage with a typographic minus sign.

    Args:
        x (float): Value in percent.
        d (int): Decimal places.

    Returns:
        str: E.g. ``"21.2%"``.
    """
    return f"{x:.{d}f}%".replace("-", MINUS)


def signed_pct(x, d=0):
    """Format a percentage with an explicit sign.

    Args:
        x (float): Value in percent.
        d (int): Decimal places.

    Returns:
        str: E.g. ``"+64%"`` or ``"−31%"``.
    """
    return f"{x:+.{d}f}%".replace("-", MINUS)


def pp(x):
    """Format a signed change in percentage points to one decimal.

    Args:
        x (float): Change in percentage points.

    Returns:
        str: E.g. ``"+3.6 pp"`` or ``"−3.2 pp"``.
    """
    return f"{x:+.1f} pp".replace("-", MINUS)


def num(x):
    """Format a count or measure for display.

    Args:
        x (float): Value to format.

    Returns:
        str: Whole numbers with thousands separators, otherwise one
        decimal place.
    """
    return f"{x:,.0f}" if float(x).is_integer() else f"{x:,.1f}"


def long_date(iso):
    """Format an ISO date as a long US-style date.

    Args:
        iso (str): Date as ``YYYY-MM-DD``.

    Returns:
        str: E.g. ``"July 4, 1996"``.
    """
    d = date.fromisoformat(iso)
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def country(name):
    """Format a country name for running text.

    Args:
        name (str): Country name as in the data.

    Returns:
        str: HTML-escaped name, with "the" before USA and UK.
    """
    return ("the " if name in {"USA", "UK"} else "") + escape(name)


def join_names(names):
    """Join names into an English list with "and".

    Args:
        names (Iterable[str]): Names in display order.

    Returns:
        str: HTML-escaped list, e.g. ``"A, B and C"``; empty if none.
    """
    names = [escape(n) for n in names]
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def table(headers, rows, numeric_from=1, caption=None):
    """Build an HTML table inside a scrollable wrapper.

    Cell values are inserted as given, so callers must escape text.

    Args:
        headers (list[str]): Column headings.
        rows (list[list[str]]): Cell values; the first cell of each row
            becomes a row header.
        numeric_from (int): Index of the first right-aligned column.
        caption (str | None): Caption HTML, or None for no caption.

    Returns:
        str: HTML for the table.
    """
    cap = f"<caption>{caption}</caption>" if caption else ""
    head = "".join(
        f'<th scope="col"{" class=num" if i >= numeric_from else ""}>{h}</th>'
        for i, h in enumerate(headers))
    body = ""
    for row in rows:
        cells = "".join(
            (f'<th scope="row">{v}</th>' if i == 0 else
             f'<td{" class=num" if i >= numeric_from else ""}>{v}</td>')
            for i, v in enumerate(row))
        body += f"<tr>{cells}</tr>"
    return (f'<div class="table-wrap wide"><table>{cap}<thead><tr>{head}</tr></thead>'
            f"<tbody>{body}</tbody></table></div>")


def figure(src, alt, caption):
    """Build an HTML figure for one chart image.

    Args:
        src (str): Image path relative to ``docs/``.
        alt (str): Alt text; escaped here.
        caption (str): Caption HTML, inserted unescaped.

    Returns:
        str: HTML for the figure.
    """
    return (f'<figure><img src="{src}" alt="{escape(alt)}">'
            f"<figcaption>{caption}</figcaption></figure>")


def section(qid, question, why, approach, visual, finding, implication, caveats):
    """Assemble one question's section in the required order.

    Args:
        qid (str): Section id, e.g. ``"q1"``; also shown upper-cased.
        question (str): The business question.
        why (str): "Why it matters" HTML.
        approach (str): "Approach" HTML.
        visual (str): Figures and tables HTML.
        finding (str): "Main finding" HTML.
        implication (str): "Business implication" HTML.
        caveats (list[str]): Caveat HTML, one list item each.

    Returns:
        str: HTML for the section.
    """
    caveat_items = "".join(f"<li>{c}</li>" for c in caveats)
    return f"""
<section id="{qid}" aria-labelledby="{qid}-title">
  <p class="qnum">{qid.upper()}</p>
  <h2 id="{qid}-title">{question}</h2>
  <h3>Why it matters</h3>
  {why}
  <h3>Approach</h3>
  {approach}
  {visual}
  <div class="answer">
    <h3>Main finding</h3>
    {finding}
    <h3>Business implication</h3>
    {implication}
  </div>
  <details class="caveats"><summary>Caveats and sample sizes</summary><ul>{caveat_items}</ul></details>
</section>"""


# ---------- Q1 ----------

def q1_facts(q1):
    """Pick out the Q1 markets that the page text refers to.

    Args:
        q1 (dict): Contents of ``q1_results.json``.

    Returns:
        dict: Region and country tables, the top and bottom region and
        country by share change, the largest region by P2 share, and
        the countries that gained share, lost revenue, or have at most
        ``SMALL_MARKET_MAX`` customers.
    """
    regions = q1["regions"]
    countries = q1["countries_drilldown"]
    by_change = sorted(regions, key=lambda r: regions[r]["share_change_pp"])
    c_by_change = sorted(countries, key=lambda c: countries[c]["share_change_pp"])
    return {
        "regions": regions, "countries": countries,
        "reg_gainer": by_change[-1], "reg_loser": by_change[0],
        "largest": max(regions, key=lambda r: regions[r]["share_P2"]),
        "cty_gainer": c_by_change[-1], "cty_loser": c_by_change[0],
        "cty_gained": [c for c in reversed(c_by_change) if countries[c]["share_change_pp"] > 0],
        "cty_declined_rev": [c for c in c_by_change if countries[c]["revenue_growth_pct"] < 0],
        "cty_small": [c for c in c_by_change if countries[c]["customers_total"] <= SMALL_MARKET_MAX],
    }


def q1_section(q1, f, ds):
    """Build the Q1 markets section.

    Args:
        q1 (dict): Contents of ``q1_results.json``.
        f (dict): Facts from ``q1_facts``.
        ds (dict): Contents of ``data_summary.json``.

    Returns:
        str: HTML for the section.
    """
    R, C = f["regions"], f["countries"]
    p1, p2 = q1["p1"], q1["p2"]
    g, l = R[f["reg_gainer"]], R[f["reg_loser"]]
    cg, cl = C[f["cty_gainer"]], C[f["cty_loser"]]
    k = q1["country_min_orders_per_half"]
    loser_desc = (f"is still the largest region at {pct(l['share_P2'])} of revenue but"
                  if f["reg_loser"] == f["largest"] else f"({pct(l['share_P2'])} of revenue)")

    why = ("<p>Sales time and marketing money are limited. Knowing which customer markets are "
           "taking a bigger slice of the business, and which are slipping, tells the sales team "
           "where extra effort is most likely to pay off and which markets need a closer look "
           "before they shrink further.</p>")

    approach = f"""<p>Revenue is <code>UnitPrice × Quantity × (1 − Discount)</code> from each order
line, joined to the order and then to the customer. A market is the customer's country
(<code>Customers.Country</code>), grouped into five regions.</p>
<p>The data covers only part of {ds['first_order'][:4]} and part of {ds['last_order'][:4]}, so
calendar years can't be compared. Instead I split the data into two equal halves:
<strong>P1 = {p1['label']}</strong> ({num(p1['orders'])} orders) and
<strong>P2 = {p2['label']}</strong> ({num(p2['orders'])} orders). The last
{q1['excluded_orders_may_1998']} orders, placed after P2 ended and up to
{long_date(ds['last_order'])}, are left out.</p>
<p>Because the whole company grew {pct(q1['company_revenue_growth_pct'], 0)} between the
halves, almost every market grew in dollars. So the headline measure is each market's
<strong>change in share of company revenue</strong> (in percentage points, pp). Dollar growth is
shown alongside. Countries are shown individually only if they had at least {k} orders in each
half.</p>"""

    reg_rows = [
        [escape(r), num(v["customers_total"]), num(v["orders_P1"]), num(v["orders_P2"]),
         money(v["revenue_P1"]), money(v["revenue_P2"]), signed_pct(v["revenue_growth_pct"]),
         pct(v["share_P1"]), pct(v["share_P2"]), pp(v["share_change_pp"])]
        for r, v in sorted(R.items(), key=lambda kv: -kv[1]["share_P2"])]
    cty_rows = [
        [escape(c), num(v["customers_total"]), num(v["orders_P1"]), num(v["orders_P2"]),
         signed_pct(v["revenue_growth_pct"]), pp(v["share_change_pp"])]
        for c, v in sorted(C.items(), key=lambda kv: -kv[1]["share_change_pp"])]
    region_list = "; ".join(
        f"{escape(r)}: {join_names(sorted(c for c, rr in q1['region_map'].items() if rr == r))}"
        for r in sorted(R))

    visual = (
        figure("figures/q1_region_share.png",
               "Dot plot of each region's share of company revenue in P1 and P2.",
               f"Grey dot = P1 share, blue dot = P2 share. Labels give each region's revenue growth.")
        + table(["Region", "Customers", "Orders P1", "Orders P2", "Revenue P1", "Revenue P2",
                 "Growth", "Share P1", "Share P2", "Share change"], reg_rows)
        + figure("figures/q1_country_share_change.png",
                 "Bar chart of change in revenue share by country.",
                 f"Countries with at least {k} orders in each half. "
                 "The number in brackets is how many customers the country has.")
        + f"<details><summary>Country table</summary>"
        + table(["Country", "Customers", "Orders P1", "Orders P2", "Revenue growth",
                 "Share change"], cty_rows) + "</details>")

    finding = f"""<p>Revenue grew {pct(q1['company_revenue_growth_pct'], 0)} from P1 to P2
({money(p1['revenue'])} to {money(p2['revenue'])}). Measured by share,
<strong>{escape(f['reg_gainer'])} gained the most</strong>: {pct(g['share_P1'])} to
{pct(g['share_P2'])} ({pp(g['share_change_pp'])}), with revenue up
{pct(g['revenue_growth_pct'], 0)}. {escape(f['reg_loser'])} {loser_desc} lost
{pp(-l['share_change_pp']).replace('+', '')}.</p>
<p>By country, {country(f['cty_gainer'])} gained the most share ({pp(cg['share_change_pp'])}) and
{escape(f['cty_loser'])} lost the most ({pp(cl['share_change_pp'])}, with revenue up only
{pct(cl['revenue_growth_pct'], 0)}). Only {join_names(f['cty_declined_rev'])} had lower
revenue in P2 than in P1.</p>"""

    implication = f"""<p>{escape(f['reg_gainer'])}, and {country(f['cty_gainer'])} in particular, is
where demand is rising fastest, so it is the strongest case for extra sales capacity. The
markets gaining share are {join_names(f['cty_gained'])}. {escape(f['cty_loser'])} and the
countries where revenue fell ({join_names(f['cty_declined_rev'])}) need a customer-by-customer
review to find out who is buying less, and why, before deciding whether to rebuild or cut
effort there.</p>"""

    qe = q1["quirk_effect"]
    caveats = [
        f"P1 and P2 are equal-length halves, not calendar years. Each holds one of every calendar "
        f"month except that P1 includes a May and P2 a June.",
        f"Region groupings are my own judgment. {region_list}.",
        f"{join_names(f['cty_small'])} have at most {SMALL_MARKET_MAX} customers each, so their changes reflect "
        f"individual accounts more than whole markets.",
        f"{len(qe['quirk_orders'])} orders ({', '.join(map(str, qe['quirk_orders']))}) ship to a "
        f"country different from the customer's own. Counting them by ship-to country instead "
        f"moves any region's share by at most {qe['max_share_shift_pp']} pp and changes no "
        f"region from gaining to losing.",
        "Share of revenue depends on a few large orders in small markets, so a single big order "
        "can swing a country's result.",
    ]
    return section("q1", "Which customer markets are growing or declining, and where should "
                   "sales efforts be focused?", why, approach, visual, finding, implication,
                   caveats)


# ---------- Q2 ----------

def q2_section(q2, q1):
    """Build the Q2 categories and concentration section.

    Args:
        q2 (dict): Contents of ``q2_results.json``.
        q1 (dict): Contents of ``q1_results.json``, for the P1 and P2
            labels.

    Returns:
        str: HTML for the section.
    """
    cats = q2["categories"]
    order = sorted(cats, key=lambda c: -cats[c]["revenue"])
    top3 = order[:3]
    by_shift = sorted(cats, key=lambda c: cats[c]["share_change_pp"])
    c_loss, c_gain = by_shift[0], by_shift[-1]
    top10 = q2["top10_customers"]
    big3 = top10[:3]
    big3_shares = [c["share_pct"] for c in big3]
    n_cust = q2["customers_with_orders"]

    why = ("<p>Knowing which categories bring in the money guides stock, purchasing and "
           "promotion decisions. Knowing how much revenue depends on a handful of customers "
           "measures risk: if a few accounts make up most of the business, losing one of them "
           "hurts, and those accounts deserve extra attention.</p>")

    approach = f"""<p>Order lines are joined to products and then to categories; revenue is
<code>UnitPrice × Quantity × (1 − Discount)</code>. The window is the whole dataset,
{long_date(q2['window'][:10])} to {long_date(q2['window'][-10:])}. No years are compared here, so
the partial years don't distort the totals. As a stability check, category shares are also
compared between the two halves used in Q1 (P1 = {q1['p1']['label']}, P2 =
{q1['p2']['label']}).</p>
<p>For concentration, the {n_cust} customers with at least one order are ranked by total
revenue. The Pareto curve shows what share of revenue the top X% of customers bring in. The
summary numbers are the share held by the top {q2['top_n']} customers and by the top
{q2['top_pct']}% ({q2['top20pct_n']} customers).</p>"""

    cat_rows = [[escape(c), num(cats[c]["products"]), money(cats[c]["revenue"]),
                 pct(cats[c]["share_pct"]), pct(cats[c]["share_P1_pct"]),
                 pct(cats[c]["share_P2_pct"]), pp(cats[c]["share_change_pp"])] for c in order]
    cust_rows = [[num(c["rank"]), escape(c["CompanyName"]), escape(c["Country"]),
                  money(c["revenue"]), num(c["orders"]), pct(c["share_pct"])] for c in top10]

    visual = (
        figure("figures/q2_category_revenue.png", "Bar chart of revenue by product category.",
               "Revenue over the whole period, net of discounts. Labels give each category's "
               "share of the total.")
        + table(["Category", "Products", "Revenue", "Share", "Share P1", "Share P2",
                 "Share change"], cat_rows)
        + figure("figures/q2_customer_pareto.png",
                 "Pareto curve of cumulative revenue share against cumulative share of customers.",
                 "The further the blue curve sits above the grey line, the more revenue depends "
                 "on a few customers.")
        + "<details><summary>Top customers table</summary>"
        + table(["Rank", "Customer", "Country", "Revenue", "Orders", "Share"], cust_rows,
                numeric_from=3) + "</details>")

    finding = f"""<p>{join_names(top3)} together bring in {pct(q2['top3_category_share_pct'])}
of revenue, and {escape(order[0])} alone {pct(cats[order[0]]['share_pct'])}. The mix is
shifting: between the halves {escape(c_loss)} lost {pp(-cats[c_loss]['share_change_pp']).replace('+', '')}
of share and {escape(c_gain)} gained {pp(cats[c_gain]['share_change_pp'])}.</p>
<p>Customer revenue is heavily concentrated. The top {q2['top_n']} of {n_cust} customers bring in
<strong>{pct(q2['top_n_share_pct'])}</strong> of revenue and the top {q2['top_pct']}% bring in
{pct(q2['top20pct_share_pct'])}. Just {q2['customers_for_50pct']} customers make up half of all
revenue, while the smallest {q2['bottom_half_n']} together make up
{pct(q2['bottom_half_share_pct'])}. The three largest, {join_names(c['CompanyName'] for c in big3)},
each account for {pct(min(big3_shares))} to {pct(max(big3_shares))}.</p>"""

    implication = f"""<p>Losing any one of the three largest customers would remove roughly
{pct(min(big3_shares), 0)} to {pct(max(big3_shares), 0)} of revenue, so these accounts
justify a named account manager and early warning when their order frequency drops. On the
product side, stock and promotion priority belongs with {join_names(top3)}, while the falling
share of {escape(c_loss)} is worth checking for pricing or competition problems.</p>"""

    caveats = [
        f"Totals cover the whole period, so customers who started buying later look smaller. "
        f"{q2['customers_first_order_after_p1']} customers placed their first order after P1.",
        f"{q2['customers_without_orders']} customers in the database never ordered and are "
        f"excluded from the {n_cust}.",
        "Revenue is net of discounts and excludes freight.",
    ]
    return section("q2", "Which product categories drive the most revenue, and how concentrated "
                   "are sales?", why, approach, visual, finding, implication, caveats)


# ---------- Q3 ----------

def q3_section(q3):
    """Build the Q3 shipping section.

    Args:
        q3 (dict): Contents of ``q3_results.json``.

    Returns:
        str: HTML for the section.
    """
    S = q3["shippers"]
    o = q3["overall"]
    slow_days = q3["slow_threshold_days"]
    best = min(S, key=lambda s: S[s]["p90_days"])
    worst = max(S, key=lambda s: S[s]["p90_days"])
    b, w = S[best], S[worst]
    medians = [S[s]["median_days"] for s in S]
    lead = {r["lead_days"]: r for r in q3["lead_time"]}
    leads = sorted(lead)
    standard = max(lead, key=lambda d: lead[d]["shipped"])
    shortest = leads[0]
    slow_overlap = b["slow_ci_hi"] >= w["slow_ci_lo"]

    why = ("<p>Late or slow shipments cost repeat business and lead to rush freight and "
           "complaints. Knowing whether delays come from a particular carrier or from how "
           "delivery dates are promised tells operations which lever to pull.</p>")

    approach = f"""<p>Each order is joined to its shipper (<code>Orders.ShipVia → Shippers</code>).
Two measures are used:</p>
<ul>
<li><strong>Days to ship</strong> = <code>ShippedDate − OrderDate</code> in calendar days
(headline). I report the median, the 90th percentile, and the share of orders taking more than
{slow_days} days.</li>
<li><strong>Late rate</strong> = share of orders shipped after their <code>RequiredDate</code>.</li>
</ul>
<p>All {num(q3['shipped_orders'])} shipped orders are used. The {q3['open_orders']} orders with
no ship date (placed {long_date(q3['open_order_dates'][0])} to
{long_date(q3['open_order_dates'][1])}) are excluded from timing and listed separately as
<em>open</em>. 95% ranges come from a Wilson interval for shares and from a bootstrap for the
median.</p>"""

    ship_rows = [[escape(s), num(v["shipped"]), num(v["open"]), num(v["median_days"]),
                  num(v["p90_days"]),
                  f"{pct(v['slow_pct'])} <span class=ci>({num(v['slow_ci_lo'])}–{num(v['slow_ci_hi'])})</span>",
                  f"{pct(v['late_pct'])} <span class=ci>({num(v['late_ci_lo'])}–{num(v['late_ci_hi'])})</span>",
                  num(v["late"])]
                 for s, v in sorted(S.items(), key=lambda kv: kv[1]["p90_days"])]
    lead_rows = [[f"{d} days", num(lead[d]["shipped"]), num(lead[d]["late"]),
                  pct(lead[d]["late_pct"])] for d in leads]

    visual = (
        figure("figures/q3_days_to_ship_box.png", "Box plot of days to ship for each shipper.",
               "Shipped orders only. The red line marks the most common promised lead time.")
        + table(["Shipper", "Shipped", "Open", "Median days", "90th pct days",
                 f"Over {slow_days} days (95% range)", "Late (95% range)", "Late orders"],
                ship_rows)
        + table(["Promised lead time", "Shipped", "Late", "Late rate"], lead_rows,
                caption="Late rate by promised lead time (RequiredDate − OrderDate)"))

    finding = f"""<p>Half of all orders ship within {num(o['median_days'])} days and 90% within
{num(o['p90_days'])} days. Overall, {pct(o['late_pct'])} ({o['late']} of
{num(q3['shipped_orders'])}) shipped after the required date. The shippers are alike on typical
speed (medians {num(min(medians))} to {num(max(medians))} days) but differ in their slow tail:
<strong>{escape(best)} ships 90% of orders within {num(b['p90_days'])} days, against
{num(w['p90_days'])} days for {escape(worst)}</strong>. Only {pct(b['slow_pct'])} of its orders take
more than {slow_days} days, against {pct(w['slow_pct'])}.</p>
<p>Late rates ({'; '.join(f"{escape(s)} {pct(S[s]['late_pct'])}" for s in S)})
{'fall within each other’s 95% ranges, so the data cannot separate the shippers on lateness'
 if q3['late_rate_cis_all_overlap'] else 'differ beyond their 95% ranges'}. The promised lead
time matters more: {pct(lead[shortest]['late_pct'])} of {shortest}-day orders shipped late,
against {pct(lead[standard]['late_pct'])} of {standard}-day orders.</p>"""

    tail_strength = ("The gap in slow shipments is borderline (the 95% ranges just overlap), so "
                     "treat it as a lead worth testing, not proof."
                     if slow_overlap else
                     "The gap in slow shipments is clear of the 95% ranges.")
    implication = f"""<p>The problem is the slow tail and tight promises, not average speed.
Routing time-sensitive orders to {escape(best)} and asking {escape(worst)} about its slowest
shipments could cut the long waits. Promising a {shortest}-day lead time should be checked
against what the warehouse can actually ship in time. {tail_strength} A trial that routes
urgent orders to {escape(best)} and tracks the results would settle it.</p>"""

    caveats = [
        f"Late counts per shipper are small ({min(S[s]['late'] for s in S)} to "
        f"{max(S[s]['late'] for s in S)}), which is why the late-rate ranges are wide.",
        "ShippedDate is when the order left the warehouse, not when the customer received it.",
        f"None of the {q3['open_orders']} open orders was past its required date when the data "
        f"ends ({q3['open_overdue_at_data_end']} overdue), but some may still turn late.",
        "Days are calendar days; weekends and holidays are not removed.",
    ]
    return section("q3", "Where are the largest shipping delays, and which operational areas "
                   "need improvement?", why, approach, visual, finding, implication, caveats)


# ---------- page ----------

CSS = """
:root{--bg:#fcfcfb;--ink:#1f2a33;--ink-2:#55606a;--rule:#dde2e6;--accent:#2a78d6;
--panel:#eef4fb;--code:#f1f2f0;color-scheme:light}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);
font:1.0625rem/1.6 "Atkinson Hyperlegible",system-ui,sans-serif}
main{max-width:46rem;margin:0 auto;padding:3rem 1rem 4rem}
header{margin-bottom:3rem}
h1{font-size:clamp(1.9rem,4.5vw,2.6rem);line-height:1.15;letter-spacing:-.015em;margin:0 0 .75rem}
.dek{font-size:1.2rem;color:var(--ink-2);margin:0 0 2rem}
.summary{border-top:3px solid var(--ink);padding-top:1rem}
.summary h2{font-size:1rem;margin:0 0 .5rem}
.summary ol{margin:0;padding-left:1.25rem}
.summary li{margin:.5rem 0}
.summary a{color:var(--ink);font-weight:700}
section{border-top:1px solid var(--rule);padding-top:2.25rem;margin-top:3rem}
.qnum{margin:0;color:var(--accent);font-weight:700}
h2{font-size:1.6rem;line-height:1.25;margin:.25rem 0 1.25rem;letter-spacing:-.01em}
h3{font-size:1.05rem;margin:1.75rem 0 .35rem}
p{margin:0 0 .9rem}
ul{padding-left:1.25rem}
code{background:var(--code);padding:.05em .3em;border-radius:3px;font-size:.88em}
.wide,figure{width:min(58rem,calc(100vw - 2rem));position:relative;left:50%;transform:translateX(-50%)}
figure{margin:2rem 0 1rem;padding:0}
figure img{display:block;width:100%;height:auto}
figcaption{font-size:.9rem;color:var(--ink-2);padding:.5rem 0 0;max-width:46rem;margin:0 auto}
.table-wrap{overflow-x:auto;margin:1rem 0 1.5rem}
table{border-collapse:collapse;width:100%;font-size:.9rem;font-variant-numeric:tabular-nums}
caption{text-align:left;font-weight:700;padding-bottom:.4rem}
th,td{padding:.4rem .6rem;border-bottom:1px solid var(--rule);text-align:left;white-space:nowrap}
thead th{color:var(--ink-2);font-weight:700;border-bottom:1.5px solid var(--ink-2)}
.num{text-align:right}
.ci{color:var(--ink-2);font-size:.85em}
.answer{background:var(--panel);border-radius:6px;padding:.25rem 1.25rem .5rem;margin-top:2rem}
.answer h3:first-child{margin-top:1rem}
details{margin:1rem 0}
summary{cursor:pointer;color:var(--accent);font-weight:700}
summary:focus-visible,a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.caveats li{margin:.35rem 0}
footer{border-top:1px solid var(--rule);margin-top:3.5rem;padding-top:1.5rem;font-size:.95rem;color:var(--ink-2)}
footer h2{font-size:1.1rem;color:var(--ink)}
a{color:var(--accent)}
"""


def build():
    """Generate the full webpage from the analysis outputs.

    Args:
        None.

    Returns:
        None. Writes ``docs/index.html``.

    Raises:
        SystemExit: If an output JSON file is missing.
    """
    ds = load("data_summary.json")
    q1, q2, q3 = load("q1_results.json"), load("q2_results.json"), load("q3_results.json")
    f1 = q1_facts(q1)

    S = q3["shippers"]
    best = min(S, key=lambda s: S[s]["p90_days"])
    big3 = q2["top10_customers"][:3]
    lead = {r["lead_days"]: r for r in q3["lead_time"]}
    shortest = min(lead)
    summary = f"""
<div class="summary">
<h2>Summary</h2>
<ol>
<li><a href="#q1">Markets.</a> Revenue grew {pct(q1['company_revenue_growth_pct'], 0)} between
the two halves of the data. {escape(f1['reg_gainer'])} gained the most share of revenue
({pp(f1['regions'][f1['reg_gainer']]['share_change_pp'])}), led by {country(f1['cty_gainer'])};
{escape(f1['reg_loser'])} lost the most ({pp(f1['regions'][f1['reg_loser']]['share_change_pp'])}).</li>
<li><a href="#q2">Categories and concentration.</a> {pct(q2['top3_category_share_pct'])} of revenue
comes from three categories, and {pct(q2['top_n_share_pct'])} from just {q2['top_n']} customers.
The top three customers alone bring in {pct(sum(c['share_pct'] for c in big3))}.</li>
<li><a href="#q3">Shipping.</a> The shippers are alike on typical speed but not on slow orders:
{escape(best)} ships 90% of orders within {num(S[best]['p90_days'])} days. Orders promised in
{shortest} days are late far more often ({pct(lead[shortest]['late_pct'])}) than the rest.</li>
</ol>
</div>"""

    footer = f"""
<footer>
<h2>Data and method</h2>
<p>Source: the course's Northwind Google Sheet, saved in the repository as a snapshot. It holds
{num(ds['orders'])} orders, {num(ds['order_lines'])} order lines, {ds['customers']} customers in
{ds['customer_countries']} countries, {ds['products']} products in {ds['categories']} categories
and {ds['shippers']} shippers. Orders run from {long_date(ds['first_order'])} to
{long_date(ds['last_order'])}, so the first and last years are partial; no raw yearly totals are
compared anywhere on this page.</p>
<p>Revenue always uses the price on the order line, not the product's current list price. The
two differ on {num(ds['lines_price_differs_from_list'])} order lines because prices rose during
the period. {ds['unshipped_orders']} orders had not shipped when the data ends, and
{ds['orders_customer_country_differs_from_ship_country']} orders ship to a different country from
the customer's own; each is handled where it matters above.</p>
<p>Every number, chart and table on this page is produced by the Python code in
<a href="{REPO_URL}">the project repository</a>. Run <code>python run_all.py</code> to rebuild
it from the data snapshot.</p>
</footer>"""

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Northwind Sales Review</title>
<meta name="description" content="Where Northwind's markets are growing, how concentrated its revenue is, and where shipping slows down.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<main>
<header>
<h1>Northwind sales review: markets, concentration and shipping</h1>
<p class="dek">Three questions for planning next year's sales and operations, answered from
{num(ds['orders'])} orders placed between {long_date(ds['first_order'])} and
{long_date(ds['last_order'])}.</p>
{summary}
</header>
{q1_section(q1, f1, ds)}
{q2_section(q2, q1)}
{q3_section(q3)}
{footer}
</main>
</body>
</html>
"""
    DOCS.mkdir(exist_ok=True)
    out = DOCS / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"OK: wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
