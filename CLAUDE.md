# 15.561 HW3: AI-Assisted Business Data Analysis (Northwind)

## Goal
Analyze the Northwind database and present the findings on a public webpage for a manager.
I (the student) choose the business questions and own the conclusions. You help inspect
data, plan, write and debug code, make charts, and build the page.

## Deliverables
1. Webpage: `docs/index.html`, served by GitHub Pages from `main` /docs.
   At least 3 business questions. For EACH question show, in this order:
   1. The question
   2. Why it matters (the decision, opportunity, risk, or operation it informs)
   3. Analytical approach (tables, joins, metric definitions, time window)
   4. A purposeful visualization or table (labeled axes with units, readable title and legend)
   5. Main finding and its business implication
2. Code: this public repo, Python only, plus README.md explaining how to reproduce
   every number, figure, and table on the webpage.
3. Reflection report: written by the student alone. Never draft, outline, or edit it.

## Data
- Source: the course's public Google Sheet "Northwind Database", exported as xlsx from
  https://docs.google.com/spreadsheets/d/1mD4Hn4NZdJlXMC4EJcSp27vg-_jbxUYJ95vQvMbSpVM/export?format=xlsx
- Keep a snapshot in the repo at `data/northwind_source.xlsx` so results stay reproducible
  even if the sheet changes. `src/build_db.py` downloads it only if the snapshot is missing,
  loads every tab with pandas (needs `openpyxl`), and saves `data/northwind.db`.
- `build_db.py` must check and fail loudly if these don't hold: 830 orders, 2,155 order
  lines, 91 customers, 77 products, OrderDate 1996-07-04 to 1998-05-06.
- Tabs (exact names): Categories, Customers, Employees, Orders Details, Orders, Shippers,
  Product, Suppliers. No Regions/Territories tables exist.
- `Product` has a `Price` column (current list price) and no `UnitPrice`. Ignore its leftover
  exercise columns: Cheap, NewPrice, Cheap.1, IsCheap, Unnamed: 14, NewPrice.1.
- Known quirk: orders 10248, 10249, 10260, 10808 have a CustomerID whose country differs
  from ShipCountry. Keep the data as given, but mention it if it affects a result.

## Analysis rules
- Revenue = `[Orders Details].UnitPrice * Quantity * (1 - Discount)`.
  Never use `Product.Price` for revenue (it differs on 658 order lines).
- 1996 (Jul-Dec) and 1998 (Jan to May 6) are partial years. Never compare raw yearly
  totals; use monthly series or same-period comparisons, and say so on the page.
- 21 orders have no ShippedDate; handle them explicitly in any shipping analysis.
- State assumptions and caveats; flag small sample sizes.

## Code rules
- Python only. List dependencies in `requirements.txt` (including `openpyxl`).
- One command reproduces everything: `python run_all.py`.
- Every number on the webpage must be computed by the scripts and inserted by
  `src/build_site.py`. Never type numbers into the page by hand.
- When the code is final, document all Python files with the `/python-docstrings` skill.

## Working style
- Work in stages. At the end of each stage, stop and show me the results before moving on.
- When I ask for a plan, do not write code until I approve it.

## Git
- Commits are authored by me only. Never add `Co-Authored-By` or any Claude / Claude Code
  attribution to commit messages or PR descriptions.
- Ask me before every `git push`.
