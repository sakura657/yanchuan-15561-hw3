# Northwind sales review (15.561 HW3)

An analysis of the Northwind sample database for a sales manager. It answers three questions:

1. **Markets.** Which customer markets are growing or declining, and where should sales effort go?
2. **Categories and concentration.** Which product categories drive revenue, and how much does revenue depend on a few customers?
3. **Shipping.** Where are the largest shipping delays, and which areas of operations need improvement?

The results are published as a webpage at `docs/index.html`, served by GitHub Pages from the
`main` branch, `/docs` folder. Every number, chart and table on the page is produced by the
Python scripts in this repository. None is typed in by hand.

## Data

The source is the course's public Google Sheet, "Northwind Database". A snapshot is kept at
`data/northwind_source.xlsx`, so the results don't change if the sheet does. `src/build_db.py`
downloads the sheet only when that snapshot is missing.

## Setup

Tested with **Python 3.10.18** on macOS. Package versions are pinned in `requirements.txt`.

```bash
git clone https://github.com/sakura657/yanchuan-15561-hw3.git
cd yanchuan-15561-hw3
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Reproduce everything

```bash
python run_all.py
```

This runs five scripts in order and stops at the first failure:

| Step | Script | Writes |
|---|---|---|
| 1 | `src/build_db.py` | `data/northwind.db`, `output/data_summary.json` |
| 2 | `src/q1_markets.py` | `output/q1_*.csv`, `output/q1_results.json`, `docs/figures/q1_*.png` |
| 3 | `src/q2_concentration.py` | `output/q2_*.csv`, `output/q2_results.json`, `docs/figures/q2_*.png` |
| 4 | `src/q3_shipping.py` | `output/q3_*.csv`, `output/q3_results.json`, `docs/figures/q3_*.png` |
| 5 | `src/build_site.py` | `docs/index.html` |

Each step checks its own results and fails loudly if a check doesn't hold:

- `build_db.py` requires 830 orders, 2,155 order lines, 91 customers, 77 products and order
  dates from 1996-07-04 to 1998-05-06.
- Each analysis script confirms that its totals add up, for example that region revenue sums
  to company revenue.

To view the page locally:

```bash
python -m http.server 8561 --directory docs
```

Then open http://localhost:8561.

Shared definitions live in `src/common.py`: the revenue formula, the two comparison periods,
the country-to-region mapping, the Q1 country threshold and the chart colours.

## Definitions used throughout

- **Revenue** = `[Orders Details].UnitPrice × Quantity × (1 − Discount)`. It is never computed
  from `Product.Price`, the current list price, which differs on 658 order lines.
- **Comparison periods:** 1996 and 1998 are partial years, so yearly totals are never compared.
  Growth uses two 11-month halves instead:
  - P1 = Jul 1996 – May 1997
  - P2 = Jun 1997 – Apr 1998
  - The 14 orders from May 1–6, 1998 fall outside both halves.
- **Unshipped orders:** the 21 orders with no `ShippedDate` are left out of the shipping timing
  measures and reported separately as open.
- **Bootstrap:** confidence intervals use 10,000 resamples with a fixed seed (561), so they
  reproduce exactly.

## Where each number, figure and table on the webpage comes from

The `src/build_site.py` column is the function that puts the item on the page. Some page values
are derived there from the JSON rather than read directly. Examples are the region that gained
the most share, the minimum and maximum across shippers, and the combined share of the top
three customers.

| Webpage item | Produced by | Read from | `src/build_site.py` |
|---|---|---|---|
| Header: order count and date range | `src/build_db.py` | `output/data_summary.json` | `build` |
| Summary list (3 items) | `src/q1_markets.py`, `src/q2_concentration.py`, `src/q3_shipping.py` | `output/q1_results.json`, `output/q2_results.json`, `output/q3_results.json` | `build` |
| **Q1** Approach: P1/P2 order counts, the 14 excluded orders, company growth, country threshold | `src/q1_markets.py` (threshold set in `src/common.py`) | `q1_results.json` → `p1`, `p2`, `excluded_orders_may_1998`, `company_revenue_growth_pct`, `country_min_orders_per_half` | `q1_section` |
| **Q1** Figure: revenue share by region | `src/q1_markets.py` → `chart_regions` | `docs/figures/q1_region_share.png` | `q1_section` |
| **Q1** Region table | `src/q1_markets.py` → `market_table` | `q1_results.json` → `regions` (also `output/q1_regions.csv`) | `q1_section` |
| **Q1** Figure: country share change | `src/q1_markets.py` → `chart_countries` | `docs/figures/q1_country_share_change.png` | `q1_section` |
| **Q1** Country table | `src/q1_markets.py` → `market_table` | `q1_results.json` → `countries_drilldown` (also `output/q1_countries_drilldown.csv`) | `q1_section` |
| **Q1** All-countries table (all 21, incl. those below the threshold) | `src/q1_markets.py` → `market_table` | `q1_results.json` → `countries_all` (also `output/q1_countries_all.csv`) | `q1_section` |
| **Q1** Finding and implication: shares, share changes, growth rates, the countries that gained or lost the most share, every country whose revenue fell | `src/q1_markets.py` | `q1_results.json` → `regions`, `countries_drilldown`, `countries_all`, `p1`, `p2` | `q1_facts`, `q1_section` |
| **Q1** Caveat: effect of the 4 ship-to-country orders | `src/q1_markets.py` → `quirk_effect` | `q1_results.json` → `quirk_effect` | `q1_section` |
| **Q1** Caveat: region groupings | `src/common.py` → `REGION_MAP` | `q1_results.json` → `region_map` | `q1_section` |
| **Q2** Approach: window, customer count, top-N and top-% definitions | `src/q2_concentration.py` | `q2_results.json` → `window`, `customers_with_orders`, `top_n`, `top_pct`, `top20pct_n` | `q2_section` |
| **Q2** Figure: revenue by category | `src/q2_concentration.py` → `chart_categories` | `docs/figures/q2_category_revenue.png` | `q2_section` |
| **Q2** Category table, incl. P1/P2 shares | `src/q2_concentration.py` → `category_table` | `q2_results.json` → `categories` (also `output/q2_categories.csv`) | `q2_section` |
| **Q2** Figure: customer Pareto curve | `src/q2_concentration.py` → `chart_pareto` | `docs/figures/q2_customer_pareto.png` | `q2_section` |
| **Q2** Top customers table | `src/q2_concentration.py` → `customer_pareto` | `q2_results.json` → `top10_customers` (full ranking in `output/q2_customers_ranked.csv`) | `q2_section` |
| **Q2** Finding and implication: top-3 category share, share shifts, top-10 and top-20% share, customers for 50%, bottom-half share, largest customers | `src/q2_concentration.py` | `q2_results.json` → `top3_category_share_pct`, `categories`, `top_n_share_pct`, `top20pct_share_pct`, `customers_for_50pct`, `bottom_half_n`, `bottom_half_share_pct`, `top10_customers` | `q2_section` |
| **Q2** Caveats: late starters, customers with no orders | `src/q2_concentration.py` | `q2_results.json` → `customers_first_order_after_p1`, `customers_without_orders` | `q2_section` |
| **Q3** Approach: shipped and open counts, open-order dates, slow-shipment threshold | `src/q3_shipping.py` | `q3_results.json` → `shipped_orders`, `open_orders`, `open_order_dates`, `slow_threshold_days` | `q3_section` |
| **Q3** Figure: days to ship by shipper | `src/q3_shipping.py` → `chart_box` | `docs/figures/q3_days_to_ship_box.png` | `q3_section` |
| **Q3** Shipper table, incl. 95% ranges | `src/q3_shipping.py` → `shipper_table`, `wilson`, `boot_median_ci` | `q3_results.json` → `shippers` (also `output/q3_shippers.csv`) | `q3_section` |
| **Q3** Late rate by promised lead time table | `src/q3_shipping.py` → `lead_time_table` | `q3_results.json` → `lead_time` (also `output/q3_lead_time.csv`) | `q3_section` |
| **Q3** Finding and implication: overall median, 90th percentile and late rate, shipper comparison, lead-time effect, overlap of confidence ranges | `src/q3_shipping.py` | `q3_results.json` → `overall`, `shippers`, `lead_time`, `late_rate_cis_all_overlap` | `q3_section` |
| **Q3** Caveats: late counts, overdue open orders | `src/q3_shipping.py` | `q3_results.json` → `shippers`, `open_overdue_at_data_end` | `q3_section` |
| Data and method: dataset counts, price-mismatch lines, unshipped orders, ship-country mismatches | `src/build_db.py` → `write_summary` | `output/data_summary.json` | `build` |

## Repository layout

```
data/northwind_source.xlsx   source snapshot (data/northwind.db is generated, not committed)
src/build_db.py              load the workbook, validate, write SQLite + data summary
src/common.py                shared definitions, paths and chart style
src/q1_markets.py            Q1 analysis
src/q2_concentration.py      Q2 analysis
src/q3_shipping.py           Q3 analysis
src/build_site.py            writes docs/index.html from output/*.json
run_all.py                   runs all of the above in order
output/                      generated tables (CSV) and results (JSON)
docs/                        the webpage and its figures (GitHub Pages)
```
