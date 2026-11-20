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
- Source: https://github.com/jpwhite3/northwind-SQLite3 pinned at commit 4f56e7f.
- Build the database the way that repo's `make build` does: run its `src/create.sql`,
  then `src/update.sql`. Do this in Python with the built-in `sqlite3` module
  (`src/build_db.py`), writing to `data/northwind.db`.
- Expected result: 830 orders, 2,155 order lines, OrderDate 2016-07-04 to 2018-05-06.
- Do NOT use that repo's prebuilt `dist/northwind.db`: it adds ~15k randomly generated orders.

## Analysis rules
- Revenue = `[Order Details].UnitPrice * Quantity * (1 - Discount)`.
  Never use `Products.UnitPrice` for revenue (it differs on 658 order lines).
- 2016 (Jul-Dec) and 2018 (Jan to May 6) are partial years. Never compare raw yearly
  totals; use monthly series or same-period comparisons, and say so on the page.
- 21 orders have no ShippedDate; handle them explicitly in any shipping analysis.
- State assumptions and caveats; flag small sample sizes.

## Code rules
- Python only. List dependencies in `requirements.txt`.
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
