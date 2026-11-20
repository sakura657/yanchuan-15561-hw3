"""Shared paths, definitions and chart style for the analysis."""

import json
import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "northwind.db"
OUTPUT_DIR = ROOT / "output"
FIG_DIR = ROOT / "docs" / "figures"

# Revenue per order line. Never use Product.Price (CLAUDE.md analysis rules).
REVENUE_SQL = "d.UnitPrice * d.Quantity * (1 - d.Discount)"

# Two 11-month halves (inclusive start, exclusive end). May 1–6, 1998 is excluded.
P1 = ("1996-07-01", "1997-06-01")
P2 = ("1997-06-01", "1998-05-01")
P1_LABEL = "Jul 1996–May 1997"
P2_LABEL = "Jun 1997–Apr 1998"
DATA_END = "1998-05-06"

# Customer country -> world region. A judgment call, stated on the page.
REGION_MAP = {
    "USA": "North America", "Canada": "North America",
    "Mexico": "Latin America", "Brazil": "Latin America",
    "Venezuela": "Latin America", "Argentina": "Latin America",
    "Germany": "Western Europe", "France": "Western Europe", "UK": "Western Europe",
    "Ireland": "Western Europe", "Belgium": "Western Europe",
    "Switzerland": "Western Europe", "Austria": "Western Europe",
    "Poland": "Western Europe",
    "Spain": "Southern Europe", "Portugal": "Southern Europe", "Italy": "Southern Europe",
    "Sweden": "Nordic", "Denmark": "Nordic", "Norway": "Nordic", "Finland": "Nordic",
}

# Q1 country drill-down: minimum orders a country needs in EACH half.
Q1_MIN_ORDERS_PER_HALF = 10

# Chart palette (dataviz reference palette, light mode).
SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e4e3df"
BLUE = "#2a78d6"
RED = "#e34948"
MUTED = "#a9a8a2"


def connect():
    """Open the Northwind database read-only.

    Args:
        None.

    Returns:
        sqlite3.Connection: Read-only connection to ``DB_PATH``.

    Raises:
        SystemExit: If the database has not been built yet.
    """
    if not DB_PATH.exists():
        raise SystemExit(f"{DB_PATH} not found. Run: python src/build_db.py")
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)


def write_json(name, data):
    """Save a results dictionary as JSON in the output folder.

    Args:
        name (str): File name inside ``output/``.
        data (dict): JSON-serialisable results.

    Returns:
        pathlib.Path: Path of the written file.
    """
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / name
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return path


def write_csv(name, df):
    """Save a table as CSV in the output folder, without the index.

    Args:
        name (str): File name inside ``output/``.
        df (pandas.DataFrame): Table to save.

    Returns:
        None.
    """
    OUTPUT_DIR.mkdir(exist_ok=True)
    df.to_csv(OUTPUT_DIR / name, index=False)


def setup_style():
    """Apply the shared matplotlib style used by every chart.

    Args:
        None.

    Returns:
        None. Updates ``matplotlib.pyplot.rcParams`` globally.
    """
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.size": 10, "font.family": "sans-serif",
        "text.color": TEXT, "axes.labelcolor": TEXT_2,
        "xtick.color": TEXT_2, "ytick.color": TEXT_2,
        "axes.edgecolor": GRID, "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
        "axes.axisbelow": True,
        "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "legend.frameon": False,
    })


def save_fig(fig, name):
    """Save a figure as a PNG in ``docs/figures`` and close it.

    Args:
        fig (matplotlib.figure.Figure): Figure to save.
        name (str): File name inside ``docs/figures/``.

    Returns:
        pathlib.Path: Path of the written PNG.
    """
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    path = FIG_DIR / name
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path
