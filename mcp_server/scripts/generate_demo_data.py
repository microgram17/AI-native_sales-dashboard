"""Generate demo data for the supplier BI dashboard.

Produces normalized CSV files for database import and denormalized Excel
reports as legacy-style reporting artifacts.

Usage:
    uv run python -m scripts.generate_demo_data
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import random

import pandas as pd


RANDOM_SEED = 42
START_DATE = date(2024, 1, 1)
END_DATE = date(2026, 6, 30)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSV_DIR = PROJECT_ROOT / "data" / "demo" / "csv"
EXCEL_DIR = PROJECT_ROOT / "data" / "demo" / "excel"


# ── Suppliers ──────────────────────────────────────────────────────────────────

SUPPLIER_ROWS = [
    {"supplier_id": "NORDVALE",            "supplier_name": "Nordvale Apparel AB",      "active": True},
    {"supplier_id": "URBAN_THREADS",       "supplier_name": "Urban Threads Studio AB",  "active": True},
    {"supplier_id": "ELM_RIDGE",           "supplier_name": "Elm & Ridge Tailoring AB", "active": True},
    {"supplier_id": "AURA_ACTIVE",         "supplier_name": "Aura Activewear AB",       "active": True},
    {"supplier_id": "SOLBERG_ACCESSORIES", "supplier_name": "Solberg Accessories AB",   "active": True},
    {"supplier_id": "KIDS_CO",             "supplier_name": "Kids & Co. Nordic AB",     "active": True},
]


# ── Stores ─────────────────────────────────────────────────────────────────────

STORE_ROWS = [
    {"store_id": "ONLINE-SE", "store_name": "Online Store",     "store_type": "online",   "city": "Online",    "opened_date": date(2018, 3, 1),  "active": True},
    {"store_id": "STO-001",   "store_name": "Stockholm City",   "store_type": "physical", "city": "Stockholm", "opened_date": date(2019, 9, 15), "active": True},
    {"store_id": "STO-002",   "store_name": "Stockholm Mall",   "store_type": "physical", "city": "Stockholm", "opened_date": date(2020, 4, 1),  "active": True},
    {"store_id": "STO-003",   "store_name": "Stockholm Outlet", "store_type": "physical", "city": "Stockholm", "opened_date": date(2021, 6, 1),  "active": True},
    {"store_id": "UPP-001",   "store_name": "Uppsala City",     "store_type": "physical", "city": "Uppsala",   "opened_date": date(2019, 3, 10), "active": True},
    {"store_id": "UPP-002",   "store_name": "Uppsala Mall",     "store_type": "physical", "city": "Uppsala",   "opened_date": date(2020, 11, 1), "active": True},
    {"store_id": "UPP-003",   "store_name": "Uppsala Outlet",   "store_type": "physical", "city": "Uppsala",   "opened_date": date(2022, 3, 1),  "active": True},
    {"store_id": "GOT-001",   "store_name": "Göteborg City",    "store_type": "physical", "city": "Göteborg",  "opened_date": date(2019, 6, 1),  "active": True},
    {"store_id": "GOT-002",   "store_name": "Göteborg Mall",    "store_type": "physical", "city": "Göteborg",  "opened_date": date(2020, 8, 15), "active": True},
    {"store_id": "GOT-003",   "store_name": "Göteborg Outlet",  "store_type": "physical", "city": "Göteborg",  "opened_date": date(2021, 9, 1),  "active": True},
]

OUTLET_STORE_IDS = {"STO-003", "UPP-003", "GOT-003"}
MALL_STORE_IDS   = {"STO-002", "UPP-002", "GOT-002"}
ONLINE_STORE_ID  = "ONLINE-SE"

# Base demand weights for each store (before any day-type adjustments)
STORE_BASE_WEIGHTS: dict[str, int] = {
    "ONLINE-SE": 20,
    "STO-001": 12, "STO-002": 10, "STO-003": 8,
    "UPP-001":  7, "UPP-002":  5, "UPP-003": 4,
    "GOT-001": 10, "GOT-002":  9, "GOT-003": 7,
}


# ── Product domain ─────────────────────────────────────────────────────────────
#
# category -> (abbrev_code, (price_low_sek, price_high_sek), (margin_low, margin_high),
#              subcategories, name_templates)
#
CATEGORY_DATA: dict[str, tuple[str, tuple[int, int], tuple[float, float], list[str], list[str]]] = {
    "T-Shirts": (
        "TSH", (99, 299), (0.45, 0.62),
        ["Basic Tee", "Premium Tee", "Organic Cotton", "Relaxed Fit"],
        [
            "Classic Cotton Tee", "Relaxed Fit T-Shirt", "Essential Crew Neck",
            "Premium Cotton Tee", "Organic Soft Tee", "Slim Fit T-Shirt",
            "Weekend Tee", "Everyday Essential Tee", "Washed Cotton Tee",
        ],
    ),
    "Shirts": (
        "SHT", (249, 599), (0.50, 0.65),
        ["Casual Shirt", "Formal Shirt", "Linen Shirt", "Oxford Shirt"],
        [
            "Oxford Button-Down", "Linen Casual Shirt", "Classic Formal Shirt",
            "Smart Casual Shirt", "Slim Fit Shirt", "Relaxed Linen Shirt",
            "Weekend Shirt", "Summer Shirt", "Poplin Shirt",
        ],
    ),
    "Hoodies": (
        "HOD", (399, 899), (0.48, 0.62),
        ["Pullover Hoodie", "Zip Hoodie", "Oversized Hoodie", "Cropped Hoodie"],
        [
            "Classic Pullover Hoodie", "Full-Zip Hoodie", "Oversized Fleece Hoodie",
            "Minimal Logo Hoodie", "Essential Zip Hoodie", "Soft Terry Hoodie",
            "Weekend Pullover", "Lightweight Zip-Up", "French Terry Hoodie",
        ],
    ),
    "Knitwear": (
        "KNT", (399, 999), (0.50, 0.65),
        ["Crew Neck", "V-Neck", "Cardigan", "Turtleneck"],
        [
            "Merino Crew Neck Sweater", "Fine Knit V-Neck", "Classic Cardigan",
            "Ribbed Turtleneck", "Oversized Knit Sweater", "Cable Knit Jumper",
            "Lightweight Knit Top", "Relaxed Cardigan", "Wool-Blend Jumper",
        ],
    ),
    "Jackets": (
        "JKT", (799, 2499), (0.35, 0.55),
        ["Denim Jacket", "Puffer Jacket", "Blazer", "Windbreaker", "Leather Jacket"],
        [
            "Classic Denim Jacket", "Lightweight Puffer", "Tailored Blazer",
            "Windbreaker Jacket", "Quilted Jacket", "Oversized Blazer",
            "Waterproof Shell", "Padded Winter Jacket", "Structured Blazer",
        ],
    ),
    "Trousers": (
        "TRS", (399, 999), (0.50, 0.63),
        ["Slim Fit", "Wide Leg", "Chinos", "Tapered"],
        [
            "Slim Fit Trousers", "Wide-Leg Pants", "Classic Chinos",
            "Tapered Smart Trousers", "Relaxed Chinos", "Straight Leg Trousers",
            "Smart Casual Pants", "Linen Trousers", "Pleated Trousers",
        ],
    ),
    "Jeans": (
        "JNS", (499, 1299), (0.48, 0.62),
        ["Slim Fit", "Straight Fit", "Relaxed Fit", "Skinny"],
        [
            "Slim Fit Dark Jeans", "Classic Straight Jeans", "Relaxed Fit Jeans",
            "Skinny Jeans", "Tapered Jeans", "Cropped Wide Leg Jeans",
            "High-Waist Jeans", "Vintage Wash Jeans", "Slim Tapered Jeans",
        ],
    ),
    "Dresses": (
        "DRS", (349, 999), (0.52, 0.65),
        ["Mini Dress", "Midi Dress", "Maxi Dress", "Shirt Dress"],
        [
            "Floral Midi Dress", "Classic Shirt Dress", "Linen Maxi Dress",
            "Mini Wrap Dress", "Casual Day Dress", "Slip Dress",
            "Knit Midi Dress", "Summer Maxi Dress", "Smocked Mini Dress",
        ],
    ),
    "Activewear": (
        "ACT", (199, 899), (0.50, 0.65),
        ["Sports Top", "Leggings", "Shorts", "Sports Bra"],
        [
            "High-Waist Leggings", "Training Shorts", "Sports Bra",
            "Compression Tights", "Active Tank Top", "Training Hoodie",
            "Running Tee", "Yoga Pants", "Athletic Zip-Up",
        ],
    ),
    "Shoes": (
        "SHO", (599, 1799), (0.35, 0.52),
        ["Sneakers", "Boots", "Loafers", "Sandals"],
        [
            "Classic White Sneakers", "Chelsea Boots", "Suede Loafers",
            "Running Sneakers", "Ankle Boots", "Canvas Slip-Ons",
            "Platform Sneakers", "Leather Derby", "Chunky Sole Sneakers",
        ],
    ),
    "Bags": (
        "BAG", (299, 1299), (0.55, 0.70),
        ["Tote Bag", "Crossbody Bag", "Backpack", "Clutch"],
        [
            "Canvas Tote Bag", "Leather Crossbody", "Minimal Backpack",
            "Weekend Holdall", "Structured Tote", "Bucket Bag",
            "Zip-Around Pouch", "Work Backpack",
        ],
    ),
    "Belts": (
        "BLT", (149, 499), (0.55, 0.70),
        ["Leather Belt", "Canvas Belt", "Woven Belt"],
        [
            "Classic Leather Belt", "Reversible Belt", "Canvas Woven Belt",
            "Slim Leather Belt", "Braided Leather Belt", "Wide Leather Belt",
        ],
    ),
    "Sunglasses": (
        "SGL", (199, 899), (0.58, 0.72),
        ["Classic", "Sport", "Oversized", "Aviator"],
        [
            "Classic Aviator", "Oversized Square", "Tortoise Round Frame",
            "Sport Wrap", "Retro Round", "Modern Rectangle",
        ],
    ),
    "Scarves & Hats": (
        "SCH", (99, 499), (0.55, 0.70),
        ["Scarf", "Beanie", "Cap", "Bucket Hat"],
        [
            "Merino Wool Scarf", "Classic Beanie", "Cotton Baseball Cap",
            "Bucket Hat", "Chunky Knit Scarf", "Ribbed Beanie",
            "Dad Cap", "Reversible Scarf",
        ],
    ),
    "Socks": (
        "SOK", (49, 149), (0.50, 0.65),
        ["Ankle Socks", "Crew Socks", "Thermal Socks", "No-Show Socks"],
        [
            "Ankle Socks 3-Pack", "Crew Socks 2-Pack", "Thermal Wool Socks",
            "No-Show Socks 5-Pack", "Sport Ankle Socks", "Cosy Crew Socks",
            "Bamboo Blend Socks",
        ],
    ),
    "Kidswear": (
        "KDS", (99, 599), (0.40, 0.60),
        ["Baby", "Toddler", "Kids"],
        [
            "Kids Cotton T-Shirt", "Toddler Hoodie", "Baby Bodysuit Set",
            "Kids Jogger Set", "Children's Raincoat", "Kids Denim Jeans",
            "Baby Knitwear Set", "Kids Puffer Jacket", "Toddler Zip-Up",
        ],
    ),
    "Accessories": (
        "ACC", (99, 799), (0.58, 0.72),
        ["Wallet", "Keychain", "Phone Case", "Hair Accessories"],
        [
            "Slim Leather Wallet", "Card Holder", "Keyring",
            "Phone Wallet Case", "Hair Clip Set", "Travel Wallet",
            "Mini Pouch", "Tote Charm",
        ],
    ),
}

# Supplier -> [(category, n_products_target), ...]
# Count targets produce ~120–180 total products across all suppliers.
SUPPLIER_CATEGORIES: dict[str, list[tuple[str, int]]] = {
    "NORDVALE": [
        ("T-Shirts", 8), ("Hoodies", 7), ("Knitwear", 7),
        ("Shirts", 4), ("Socks", 4),
    ],
    "URBAN_THREADS": [
        ("T-Shirts", 7), ("Hoodies", 7), ("Jackets", 7),
        ("Jeans", 5), ("Accessories", 4),
    ],
    "ELM_RIDGE": [
        ("Shirts", 8), ("Trousers", 7), ("Jackets", 7),
        ("Knitwear", 5), ("Belts", 5),
    ],
    "AURA_ACTIVE": [
        ("Activewear", 10), ("T-Shirts", 7), ("Socks", 5),
        ("Jackets", 5),
    ],
    "SOLBERG_ACCESSORIES": [
        ("Bags", 7), ("Belts", 5), ("Sunglasses", 6),
        ("Scarves & Hats", 7), ("Socks", 3),
    ],
    "KIDS_CO": [
        ("Kidswear", 10), ("T-Shirts", 6), ("Hoodies", 6),
        ("Jackets", 4), ("Socks", 4),
    ],
}

SUPPLIER_PREFIXES: dict[str, str] = {
    "NORDVALE":            "NORD",
    "URBAN_THREADS":       "URBN",
    "ELM_RIDGE":           "ELMR",
    "AURA_ACTIVE":         "AURA",
    "SOLBERG_ACCESSORIES": "SOLB",
    "KIDS_CO":             "KIDS",
}


# ── Seasonality ────────────────────────────────────────────────────────────────

# Per-category monthly demand multipliers (month number 1–12 -> float)
CATEGORY_SEASONALITY: dict[str, dict[int, float]] = {
    "T-Shirts":       {1: 0.70, 2: 0.75, 3: 1.00, 4: 1.25, 5: 1.45, 6: 1.55,
                       7: 1.50, 8: 1.40, 9: 1.05, 10: 0.85, 11: 0.80, 12: 0.75},
    "Shirts":         {1: 0.80, 2: 0.85, 3: 1.05, 4: 1.10, 5: 1.15, 6: 1.05,
                       7: 0.95, 8: 1.00, 9: 1.10, 10: 1.05, 11: 1.05, 12: 1.00},
    "Hoodies":        {1: 1.15, 2: 1.10, 3: 1.00, 4: 0.90, 5: 0.80, 6: 0.70,
                       7: 0.70, 8: 0.85, 9: 1.10, 10: 1.25, 11: 1.30, 12: 1.25},
    "Knitwear":       {1: 1.20, 2: 1.15, 3: 1.00, 4: 0.80, 5: 0.60, 6: 0.50,
                       7: 0.50, 8: 0.65, 9: 1.00, 10: 1.30, 11: 1.45, 12: 1.40},
    "Jackets":        {1: 1.20, 2: 1.15, 3: 1.10, 4: 0.95, 5: 0.70, 6: 0.55,
                       7: 0.50, 8: 0.65, 9: 1.05, 10: 1.35, 11: 1.50, 12: 1.40},
    "Trousers":       {1: 0.90, 2: 0.90, 3: 1.00, 4: 1.05, 5: 1.05, 6: 1.00,
                       7: 0.95, 8: 1.00, 9: 1.05, 10: 1.05, 11: 1.05, 12: 1.00},
    "Jeans":          {1: 0.90, 2: 0.95, 3: 1.00, 4: 1.05, 5: 1.05, 6: 0.95,
                       7: 0.90, 8: 1.00, 9: 1.10, 10: 1.10, 11: 1.10, 12: 1.00},
    "Dresses":        {1: 0.70, 2: 0.80, 3: 1.05, 4: 1.25, 5: 1.40, 6: 1.45,
                       7: 1.40, 8: 1.25, 9: 0.95, 10: 0.80, 11: 0.85, 12: 1.10},
    "Activewear":     {1: 1.45, 2: 1.30, 3: 1.25, 4: 1.20, 5: 1.15, 6: 1.00,
                       7: 0.90, 8: 0.95, 9: 1.05, 10: 1.00, 11: 0.95, 12: 0.85},
    "Shoes":          {1: 0.90, 2: 0.90, 3: 1.05, 4: 1.15, 5: 1.10, 6: 1.00,
                       7: 0.95, 8: 1.00, 9: 1.15, 10: 1.15, 11: 1.05, 12: 1.00},
    "Bags":           {1: 0.90, 2: 0.90, 3: 1.00, 4: 1.05, 5: 1.05, 6: 1.00,
                       7: 1.00, 8: 1.00, 9: 1.00, 10: 1.00, 11: 1.10, 12: 1.15},
    "Belts":          {1: 0.90, 2: 0.90, 3: 1.00, 4: 1.05, 5: 1.00, 6: 1.00,
                       7: 1.00, 8: 1.00, 9: 1.00, 10: 1.00, 11: 1.10, 12: 1.15},
    "Sunglasses":     {1: 0.50, 2: 0.60, 3: 0.85, 4: 1.15, 5: 1.50, 6: 1.70,
                       7: 1.65, 8: 1.50, 9: 1.00, 10: 0.70, 11: 0.55, 12: 0.50},
    "Scarves & Hats": {1: 1.50, 2: 1.40, 3: 1.10, 4: 0.80, 5: 0.55, 6: 0.45,
                       7: 0.45, 8: 0.55, 9: 0.90, 10: 1.25, 11: 1.50, 12: 1.60},
    "Socks":          {1: 1.10, 2: 1.05, 3: 1.00, 4: 0.95, 5: 0.90, 6: 0.85,
                       7: 0.85, 8: 0.90, 9: 1.00, 10: 1.10, 11: 1.15, 12: 1.20},
    "Kidswear":       {1: 0.90, 2: 0.85, 3: 0.90, 4: 0.95, 5: 1.00, 6: 0.95,
                       7: 0.90, 8: 1.35, 9: 1.10, 10: 1.00, 11: 1.25, 12: 1.30},
    "Accessories":    {1: 0.85, 2: 0.85, 3: 0.95, 4: 1.00, 5: 1.00, 6: 0.95,
                       7: 0.95, 8: 1.00, 9: 1.00, 10: 1.05, 11: 1.30, 12: 1.40},
}

# Item and quantity distributions
ITEM_COUNTS        = [1, 2, 3, 4, 5, 6]
ITEM_COUNT_WEIGHTS = [45, 30, 15, 7, 2, 1]

QUANTITY_CHOICES = [1, 2, 3]
QUANTITY_WEIGHTS = [85, 12, 3]

PRICE_NOISE         = [0.95, 0.97, 1.00, 1.00, 1.00, 1.03, 1.05]
PRICE_NOISE_WEIGHTS = [5,    8,   30,   30,   30,    8,    5]


# ── Helpers ────────────────────────────────────────────────────────────────────

def date_range(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def last_friday_of_november(year: int) -> date:
    d = date(year, 11, 30)
    while d.weekday() != 4:  # 4 = Friday
        d -= timedelta(days=1)
    return d


def is_black_friday_period(current_date: date) -> bool:
    if current_date.month != 11:
        return False
    bf = last_friday_of_november(current_date.year)
    return abs((current_date - bf).days) <= 2


def autosize_columns(writer: pd.ExcelWriter, sheet_name: str, df: pd.DataFrame) -> None:
    worksheet = writer.sheets[sheet_name]
    for col_index, col_name in enumerate(df.columns, start=1):
        sample  = df[col_name].head(500).astype(str).tolist()
        max_len = max(len(str(col_name)), *(len(v) for v in sample))
        width   = min(max(max_len + 2, 10), 42)
        col_letter = worksheet.cell(row=1, column=col_index).column_letter
        worksheet.column_dimensions[col_letter].width = width
    worksheet.freeze_panes = "A2"


def write_excel(path: Path, sheets: dict[str, pd.DataFrame]) -> None:
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            autosize_columns(writer, sheet_name, df)


# ── Generators ─────────────────────────────────────────────────────────────────

def generate_suppliers() -> pd.DataFrame:
    return pd.DataFrame(SUPPLIER_ROWS)


def generate_stores() -> pd.DataFrame:
    return pd.DataFrame(STORE_ROWS)


def generate_products(rng: random.Random) -> pd.DataFrame:
    rows: list[dict] = []

    launch_start  = date(2023, 1, 1)
    launch_end    = date(2026, 6, 30)
    launch_range  = (launch_end - launch_start).days

    for supplier_id, category_list in SUPPLIER_CATEGORIES.items():
        prefix     = SUPPLIER_PREFIXES[supplier_id]
        global_seq = 1

        for category, n_target in category_list:
            cat_code, price_range, margin_range, subcategories, name_templates = CATEGORY_DATA[category]
            price_low, price_high   = price_range
            margin_low, margin_high = margin_range

            n = max(1, n_target + rng.randint(-1, 1))

            names_shuffled = name_templates.copy()
            rng.shuffle(names_shuffled)

            for i in range(n):
                product_id   = f"{prefix}-{cat_code}-{global_seq:03d}"
                global_seq  += 1

                product_name = names_shuffled[i % len(names_shuffled)]
                subcategory  = rng.choice(subcategories)

                base_price = round(rng.uniform(price_low, price_high), 2)
                margin     = rng.uniform(margin_low, margin_high)
                base_cost  = round(base_price * (1.0 - margin), 2)
                base_cost  = min(base_cost, base_price)  # floating-point safety

                days_offset = rng.randint(0, launch_range)
                launch_date = launch_start + timedelta(days=days_offset)

                # Older products are occasionally inactive (10% chance)
                active = True
                if launch_date < date(2024, 6, 1) and rng.random() < 0.10:
                    active = False

                rows.append(
                    {
                        "product_id":          product_id,
                        "supplier_id":         supplier_id,
                        "product_name":        product_name,
                        "category":            category,
                        "subcategory":         subcategory,
                        "base_price_sek":      base_price,
                        "base_cost_sek":       base_cost,
                        "launch_date":         launch_date.isoformat(),
                        "active":              active,
                        # Internal weight — not written to CSV or database
                        "_popularity_weight":  round(rng.uniform(0.6, 1.5), 3),
                    }
                )

    return pd.DataFrame(rows)


def discount_probability(current_date: date, store_id: str) -> float:
    """Probability that a line item receives a discount on this date and store."""
    month = current_date.month

    if is_black_friday_period(current_date):
        base = 0.60
    elif month == 11:
        base = 0.45
    elif month == 1:
        base = 0.40
    elif month == 7:
        base = 0.35
    elif month == 12:
        base = 0.25
    else:
        base = 0.10

    if store_id in OUTLET_STORE_IDS:
        base = min(1.0, base + 0.20)

    return base


def generate_orders_and_items(
    rng: random.Random,
    products_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    # Only active products are sold
    products_list = products_df[products_df["active"]].to_dict("records")

    store_ids    = [row["store_id"] for row in STORE_ROWS]
    base_weights = [STORE_BASE_WEIGHTS[sid] for sid in store_ids]

    order_rows: list[dict] = []
    item_rows:  list[dict] = []
    order_counter = 1
    item_counter  = 1

    for current_date in date_range(START_DATE, END_DATE):
        month      = current_date.month
        is_weekend = current_date.weekday() >= 5
        is_payday  = current_date.day in range(24, 29)

        # --- Daily demand multiplier ---
        day_mult = 1.25 if is_weekend else 1.0
        if is_payday:
            day_mult *= 1.15

        month_factor = {
            1:  1.10,   # January sale
            7:  1.10,   # Summer sale
            11: 1.25,   # Pre-Black Friday build-up
            12: 1.35,   # December holiday
        }.get(month, 1.0)

        if is_black_friday_period(current_date):
            month_factor = max(month_factor, 1.80)

        total_daily = int(round(80 * day_mult * month_factor))

        # --- Product weights for today (precomputed once per day) ---
        seasonality_today = {cat: CATEGORY_SEASONALITY[cat][month] for cat in CATEGORY_SEASONALITY}
        product_weights = [
            p["_popularity_weight"] * seasonality_today.get(p["category"], 1.0)
            for p in products_list
        ]

        # --- Per-store weights (mall stores get weekend boost) ---
        day_store_weights = []
        for sid in store_ids:
            w = STORE_BASE_WEIGHTS[sid]
            if is_weekend and sid in MALL_STORE_IDS:
                w = int(w * 1.30)
            day_store_weights.append(w)
        day_weight_total = sum(day_store_weights)

        # --- Generate orders per store ---
        for i, store_id in enumerate(store_ids):
            store_fraction = day_store_weights[i] / day_weight_total
            expected_for_store = total_daily * store_fraction
            noise = rng.gauss(0, max(1.0, expected_for_store * 0.15))
            n_orders = max(0, int(round(expected_for_store + noise)))

            is_online = store_id == ONLINE_STORE_ID
            is_outlet = store_id in OUTLET_STORE_IDS

            for _ in range(n_orders):
                order_id = f"ORD-{order_counter:07d}"
                order_counter += 1

                order_status = "cancelled" if rng.random() < 0.025 else "completed"

                if is_online:
                    payment_method = rng.choices(
                        ["card", "swish", "klarna", "gift_card"],
                        weights=[40, 15, 35, 10],
                    )[0]
                else:
                    payment_method = rng.choices(
                        ["card", "swish", "klarna", "gift_card"],
                        weights=[50, 30, 12, 8],
                    )[0]

                order_rows.append(
                    {
                        "order_id":       order_id,
                        "order_date":     current_date.isoformat(),
                        "store_id":       store_id,
                        "order_status":   order_status,
                        "payment_method": payment_method,
                    }
                )

                # Cancelled orders have no items
                if order_status == "cancelled":
                    continue

                n_items = rng.choices(ITEM_COUNTS, weights=ITEM_COUNT_WEIGHTS)[0]
                chosen  = rng.choices(products_list, weights=product_weights, k=n_items)

                for product in chosen:
                    quantity = rng.choices(QUANTITY_CHOICES, weights=QUANTITY_WEIGHTS)[0]

                    noise_factor = rng.choices(PRICE_NOISE, weights=PRICE_NOISE_WEIGHTS)[0]
                    unit_price   = round(product["base_price_sek"] * noise_factor, 2)

                    # Outlet stores sell at a slightly lower price
                    if is_outlet:
                        unit_price = round(unit_price * rng.uniform(0.82, 0.92), 2)

                    unit_cost = float(product["base_cost_sek"])

                    # Guarantee price >= cost (outlet discount may undercut)
                    if unit_price < unit_cost:
                        unit_price = unit_cost

                    # Discount
                    disc_prob = discount_probability(current_date, store_id)
                    if rng.random() < disc_prob:
                        max_disc = round(quantity * unit_price, 2)
                        raw_disc = round(quantity * unit_price * rng.uniform(0.05, 0.30), 2)
                        discount = min(raw_disc, max_disc)
                    else:
                        discount = 0.00

                    item_rows.append(
                        {
                            "order_item_id":       f"LINE-{item_counter:08d}",
                            "order_id":            order_id,
                            "product_id":          product["product_id"],
                            "quantity":            quantity,
                            "unit_price_sek":      round(unit_price, 2),
                            "unit_cost_sek":       round(unit_cost, 2),
                            "discount_amount_sek": round(discount, 2),
                        }
                    )
                    item_counter += 1

    return pd.DataFrame(order_rows), pd.DataFrame(item_rows)


# ── Excel report builders ──────────────────────────────────────────────────────

def build_supplier_master(df_suppliers: pd.DataFrame) -> pd.DataFrame:
    return df_suppliers[["supplier_id", "supplier_name", "active"]].copy()


def build_store_master(df_stores: pd.DataFrame) -> pd.DataFrame:
    df = df_stores.copy()
    df["sales_channel"] = df["store_type"]
    return df[["store_id", "store_name", "store_type", "city", "sales_channel", "opened_date", "active"]]


def build_product_master(df_products: pd.DataFrame, df_suppliers: pd.DataFrame) -> pd.DataFrame:
    merged = df_products.merge(
        df_suppliers[["supplier_id", "supplier_name"]],
        on="supplier_id",
        how="left",
    )
    return merged[[
        "product_id", "product_name", "supplier_id", "supplier_name",
        "category", "subcategory", "base_price_sek", "base_cost_sek",
        "launch_date", "active",
    ]]


def build_weekly_supplier_sales(
    df_orders: pd.DataFrame,
    df_items: pd.DataFrame,
    df_products: pd.DataFrame,
    df_suppliers: pd.DataFrame,
    df_stores: pd.DataFrame,
) -> pd.DataFrame:
    completed_orders = df_orders[df_orders["order_status"] == "completed"][
        ["order_id", "order_date", "store_id"]
    ]

    df = (
        df_items
        .merge(completed_orders, on="order_id", how="inner")
        .merge(
            df_products[["product_id", "supplier_id", "product_name", "category", "subcategory"]],
            on="product_id",
            how="left",
        )
        .merge(df_suppliers[["supplier_id", "supplier_name"]], on="supplier_id", how="left")
        .merge(
            df_stores[["store_id", "store_name", "store_type", "city"]],
            on="store_id",
            how="left",
        )
    )

    df["order_date"]          = pd.to_datetime(df["order_date"])
    df["report_week_start"]   = (
        df["order_date"] - pd.to_timedelta(df["order_date"].dt.weekday, unit="D")
    ).dt.date
    df["report_week_end"]     = df["report_week_start"].apply(lambda d: d + timedelta(days=6))
    df["gross_sales_sek"]     = (df["quantity"] * df["unit_price_sek"]).round(2)
    df["net_sales_sek"]       = (df["gross_sales_sek"] - df["discount_amount_sek"]).round(2)
    df["estimated_margin_sek"] = (
        df["net_sales_sek"] - df["quantity"] * df["unit_cost_sek"]
    ).round(2)
    df["sales_channel"] = df["store_type"]

    grouped = (
        df.groupby(
            [
                "report_week_start", "report_week_end",
                "supplier_id", "supplier_name",
                "store_id", "store_name", "store_type", "city", "sales_channel",
                "product_id", "product_name", "category", "subcategory",
            ],
            as_index=False,
        )
        .agg(
            units_sold=("quantity", "sum"),
            gross_sales_sek=("gross_sales_sek", "sum"),
            discount_amount_sek=("discount_amount_sek", "sum"),
            net_sales_sek=("net_sales_sek", "sum"),
            estimated_margin_sek=("estimated_margin_sek", "sum"),
            number_of_orders=("order_id", "nunique"),
        )
        .sort_values(["report_week_start", "supplier_id", "store_id", "product_id"])
        .reset_index(drop=True)
    )

    for col in ["gross_sales_sek", "discount_amount_sek", "net_sales_sek", "estimated_margin_sek"]:
        grouped[col] = grouped[col].round(2)

    return grouped[
        [
            "report_week_start", "report_week_end",
            "supplier_id", "supplier_name",
            "store_id", "store_name", "store_type", "city", "sales_channel",
            "product_id", "product_name", "category", "subcategory",
            "units_sold", "gross_sales_sek", "discount_amount_sek",
            "net_sales_sek", "estimated_margin_sek", "number_of_orders",
        ]
    ]


def build_monthly_supplier_sales(
    df_orders: pd.DataFrame,
    df_items: pd.DataFrame,
    df_products: pd.DataFrame,
    df_suppliers: pd.DataFrame,
) -> pd.DataFrame:
    completed_orders = df_orders[df_orders["order_status"] == "completed"][
        ["order_id", "order_date"]
    ]

    df = (
        df_items
        .merge(completed_orders, on="order_id", how="inner")
        .merge(
            df_products[["product_id", "supplier_id", "product_name", "category", "subcategory"]],
            on="product_id",
            how="left",
        )
        .merge(df_suppliers[["supplier_id", "supplier_name"]], on="supplier_id", how="left")
    )

    df["order_date"]          = pd.to_datetime(df["order_date"])
    df["report_month"]        = df["order_date"].dt.to_period("M").astype(str)
    df["gross_sales_sek"]     = (df["quantity"] * df["unit_price_sek"]).round(2)
    df["net_sales_sek"]       = (df["gross_sales_sek"] - df["discount_amount_sek"]).round(2)
    df["estimated_margin_sek"] = (
        df["net_sales_sek"] - df["quantity"] * df["unit_cost_sek"]
    ).round(2)

    grouped = (
        df.groupby(
            [
                "report_month",
                "supplier_id", "supplier_name",
                "product_id", "product_name", "category", "subcategory",
            ],
            as_index=False,
        )
        .agg(
            units_sold=("quantity", "sum"),
            gross_sales_sek=("gross_sales_sek", "sum"),
            discount_amount_sek=("discount_amount_sek", "sum"),
            net_sales_sek=("net_sales_sek", "sum"),
            estimated_margin_sek=("estimated_margin_sek", "sum"),
            number_of_orders=("order_id", "nunique"),
            avg_unit_price_sek=("unit_price_sek", "mean"),
        )
        .sort_values(["report_month", "supplier_id", "product_id"])
        .reset_index(drop=True)
    )

    for col in ["gross_sales_sek", "discount_amount_sek", "net_sales_sek",
                "estimated_margin_sek", "avg_unit_price_sek"]:
        grouped[col] = grouped[col].round(2)

    # Rank products within each supplier+month by net_sales_sek descending (rank 1 = highest)
    grouped["sales_rank_for_supplier"] = (
        grouped
        .groupby(["report_month", "supplier_id"])["net_sales_sek"]
        .rank(ascending=False, method="min")
        .astype(int)
    )

    return grouped[
        [
            "report_month",
            "supplier_id", "supplier_name",
            "product_id", "product_name", "category", "subcategory",
            "units_sold", "gross_sales_sek", "discount_amount_sek",
            "net_sales_sek", "estimated_margin_sek", "number_of_orders",
            "avg_unit_price_sek", "sales_rank_for_supplier",
        ]
    ]


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    rng = random.Random(RANDOM_SEED)

    # Clean output directories
    for output_dir in [CSV_DIR, EXCEL_DIR]:
        output_dir.mkdir(parents=True, exist_ok=True)
        for f in output_dir.iterdir():
            if f.is_file():
                f.unlink()

    print("Generating master data …")
    df_suppliers = generate_suppliers()
    df_stores    = generate_stores()
    df_products  = generate_products(rng)

    print("Generating orders and order items …")
    df_orders, df_items = generate_orders_and_items(rng, df_products)

    # Drop internal weight column before writing
    products_csv = df_products.drop(columns=["_popularity_weight"])

    # ── Write CSVs ─────────────────────────────────────────────────────────────
    print("Writing CSVs …")
    df_suppliers.to_csv(CSV_DIR / "suppliers.csv", index=False)
    df_stores.to_csv(CSV_DIR / "stores.csv", index=False)
    products_csv.to_csv(CSV_DIR / "products.csv", index=False)
    df_orders.to_csv(CSV_DIR / "orders.csv", index=False)
    df_items.to_csv(CSV_DIR / "order_items.csv", index=False)

    # ── Build and write Excel reports ──────────────────────────────────────────
    print("Building Excel reports …")
    xl_supplier_master = build_supplier_master(df_suppliers)
    xl_store_master    = build_store_master(df_stores)
    xl_product_master  = build_product_master(df_products, df_suppliers)
    xl_weekly          = build_weekly_supplier_sales(
        df_orders, df_items, df_products, df_suppliers, df_stores
    )
    xl_monthly = build_monthly_supplier_sales(
        df_orders, df_items, df_products, df_suppliers
    )

    print("Writing Excel files …")
    write_excel(EXCEL_DIR / "supplier_master.xlsx",        {"Suppliers":              xl_supplier_master})
    write_excel(EXCEL_DIR / "store_master.xlsx",           {"Stores":                 xl_store_master})
    write_excel(EXCEL_DIR / "product_master.xlsx",         {"Products":               xl_product_master})
    write_excel(EXCEL_DIR / "weekly_supplier_sales.xlsx",  {"Weekly_Supplier_Sales":  xl_weekly})
    write_excel(EXCEL_DIR / "monthly_supplier_sales.xlsx", {"Monthly_Supplier_Sales": xl_monthly})

    # ── Validation output ──────────────────────────────────────────────────────
    n_completed = int((df_orders["order_status"] == "completed").sum())
    n_cancelled = int((df_orders["order_status"] == "cancelled").sum())

    print()
    print("Generated demo data:")
    print(f"  suppliers:           {len(df_suppliers)}")
    print(f"  stores:              {len(df_stores)}")
    print(f"  products:            {len(products_csv)}")
    print(f"  orders:              {len(df_orders)}")
    print(f"  order_items:         {len(df_items)}")
    print(f"  completed orders:    {n_completed}")
    print(f"  cancelled orders:    {n_cancelled}")
    print(f"  weekly report rows:  {len(xl_weekly)}")
    print(f"  monthly report rows: {len(xl_monthly)}")
    print()
    print(f"  CSV output:   {CSV_DIR.relative_to(PROJECT_ROOT)}")
    print(f"  Excel output: {EXCEL_DIR.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
