from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
import random
import re

import pandas as pd
from faker import Faker


RANDOM_SEED = 42
CURRENCY = "SEK"

START_DATE = date(2025, 1, 1)
END_DATE = date(2026, 5, 31)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "legacy_exports"

fake = Faker("sv_SE")
Faker.seed(RANDOM_SEED)


@dataclass(frozen=True)
class Supplier:
    code: str
    name: str
    brand: str
    category: str
    monthly_trend: float
    base_market_share: float
    region_bias: dict[str, float]


SUPPLIERS = [
    Supplier("SUP-001", "Nordic Home AB", "NordForm", "Home", 0.016, 0.34, {"Stockholm": 1.35}),
    Supplier("SUP-002", "Scandi Kitchen Co", "ScandiCook", "Kitchen", 0.006, 0.27, {"Skåne": 1.30}),
    Supplier("SUP-003", "Urban Outdoor Ltd", "FjordTrail", "Outdoor", 0.012, 0.31, {"Västra Götaland": 1.30}),
    Supplier("SUP-004", "Pure Beauty Nordic", "PureGlow", "Beauty", -0.005, 0.22, {"Stockholm": 1.25}),
    Supplier("SUP-005", "Smart Living AB", "BrightNest", "Electronics", 0.022, 0.38, {"Stockholm": 1.20}),
]


PRODUCT_TEMPLATES: dict[str, list[tuple[str, int, int]]] = {
    "Home": [
        ("Linen Table Runner", 55, 129),
        ("Wool Throw Blanket", 260, 599),
        ("Cotton Cushion Cover", 45, 119),
        ("Minimalist Wall Clock", 170, 399),
        ("Glass Storage Jar Set", 95, 219),
        ("Ceramic Vase", 110, 279),
        ("Scented Candle Set", 60, 149),
        ("Decorative Basket", 85, 199),
    ],
    "Kitchen": [
        ("Chef Knife 20cm", 210, 499),
        ("Non-stick Frying Pan", 180, 429),
        ("Silicone Utensil Set", 65, 159),
        ("Stainless Saucepan", 150, 349),
        ("Baking Tray Set", 90, 229),
        ("Digital Kitchen Scale", 80, 199),
        ("Reusable Food Wraps", 35, 99),
        ("Coffee Grinder Manual", 140, 329),
    ],
    "Outdoor": [
        ("Trail Backpack 25L", 280, 699),
        ("Insulated Water Bottle", 65, 179),
        ("Lightweight Rain Jacket", 310, 899),
        ("Camping Lantern", 95, 249),
        ("Hiking Socks 3-pack", 45, 129),
        ("Foldable Camping Chair", 180, 449),
        ("Dry Bag 10L", 70, 189),
        ("Thermal Base Layer", 160, 399),
    ],
    "Beauty": [
        ("Hydrating Face Cream", 85, 249),
        ("Vitamin C Serum", 120, 349),
        ("Gentle Cleanser", 55, 159),
        ("Body Lotion", 50, 149),
        ("Hand Cream Trio", 45, 129),
        ("Night Repair Mask", 110, 299),
        ("Mineral Sunscreen", 95, 259),
        ("Lip Balm 4-pack", 30, 89),
    ],
    "Electronics": [
        ("Smart LED Bulb 2-pack", 90, 249),
        ("WiFi Smart Plug", 75, 199),
        ("Motion Sensor", 110, 299),
        ("Smart Home Hub", 320, 899),
        ("Desk Lamp Wireless Charger", 180, 499),
        ("Bluetooth Speaker Mini", 150, 399),
        ("Cable Organizer Kit", 35, 99),
        ("Smart Thermometer", 95, 249),
    ],
}


REGIONS_AND_CITIES: dict[str, list[str]] = {
    "Stockholm": ["Stockholm", "Solna", "Södertälje", "Nacka"],
    "Västra Götaland": ["Göteborg", "Borås", "Trollhättan", "Skövde"],
    "Skåne": ["Malmö", "Lund", "Helsingborg", "Ystad"],
    "Uppsala": ["Uppsala", "Enköping", "Bålsta"],
    "Norrbotten": ["Luleå", "Kiruna", "Piteå"],
    "Östergötland": ["Linköping", "Norrköping", "Motala"],
}

REGION_WEIGHTS = {
    "Stockholm": 1.45,
    "Västra Götaland": 1.25,
    "Skåne": 1.15,
    "Uppsala": 0.80,
    "Norrbotten": 0.65,
    "Östergötland": 0.75,
}

SALES_CHANNELS = ["Store", "Online"]
CUSTOMER_SEGMENTS = ["Standard", "Loyalty", "Business"]


def slugify(value: str) -> str:
    value = value.lower()
    value = value.replace("å", "a").replace("ä", "a").replace("ö", "o")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def date_range(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def weighted_choice(rng: random.Random, values: list[str], weights: list[float]) -> str:
    return rng.choices(values, weights=weights, k=1)[0]


def month_number(current_date: date) -> int:
    return (current_date.year - START_DATE.year) * 12 + current_date.month - START_DATE.month


def iso_week_start(current_date: date) -> str:
    return (current_date - timedelta(days=current_date.weekday())).isoformat()


def category_seasonality(category: str, current_date: date) -> float:
    month = current_date.month

    if category == "Outdoor":
        return {
            1: 0.65, 2: 0.75, 3: 1.00, 4: 1.25, 5: 1.45, 6: 1.60,
            7: 1.55, 8: 1.35, 9: 1.10, 10: 0.90, 11: 0.80, 12: 0.75,
        }[month]

    if category in ["Kitchen", "Home"]:
        return {
            1: 0.95, 2: 0.90, 3: 0.95, 4: 1.00, 5: 1.05, 6: 1.00,
            7: 0.95, 8: 1.00, 9: 1.05, 10: 1.15, 11: 1.35, 12: 1.55,
        }[month]

    if category == "Beauty":
        return {
            1: 1.15, 2: 1.05, 3: 1.00, 4: 1.00, 5: 1.10, 6: 1.20,
            7: 1.25, 8: 1.05, 9: 0.95, 10: 1.00, 11: 1.35, 12: 1.50,
        }[month]

    # Electronics
    return {
        1: 0.90, 2: 0.85, 3: 0.90, 4: 0.95, 5: 1.00, 6: 1.00,
        7: 0.95, 8: 1.05, 9: 1.10, 10: 1.20, 11: 1.60, 12: 1.45,
    }[month]


def price_with_noise(rng: random.Random, price: int) -> int:
    return int(round(price * rng.choice([0.90, 0.95, 1.00, 1.00, 1.05])))


def pick_quantity(rng: random.Random, customer_segment: str, unit_price: int) -> int:
    if customer_segment == "Business":
        return rng.choice([2, 3, 4, 6, 8, 10])

    if unit_price >= 600:
        return rng.choice([1, 1, 1, 2])

    if unit_price >= 300:
        return rng.choice([1, 1, 2, 2, 3])

    return rng.choice([1, 1, 2, 2, 3, 4])


def pick_discount_percent(rng: random.Random, current_date: date, customer_segment: str) -> int:
    choices = [0, 0, 0, 5]

    if customer_segment == "Loyalty":
        choices += [5, 10]

    if customer_segment == "Business":
        choices += [5, 10, 15]

    if current_date.month in [11, 12]:
        choices += [10, 15, 20]

    return rng.choice(choices)


def generate_supplier_master() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "supplier_code": supplier.code,
                "supplier_name": supplier.name,
                "contact_email": f"sales@{slugify(supplier.name)}.example",
                "primary_brand": supplier.brand,
                "primary_category": supplier.category,
            }
            for supplier in SUPPLIERS
        ]
    )


def generate_product_master(rng: random.Random) -> pd.DataFrame:
    rows = []

    for supplier in SUPPLIERS:
        templates = PRODUCT_TEMPLATES[supplier.category]

        for index, (name, unit_cost, recommended_price) in enumerate(templates, start=1):
            rows.append(
                {
                    "sku": f"{supplier.code.replace('SUP-', '')}-{index:04d}",
                    "product_name": name,
                    "brand": supplier.brand,
                    "category": supplier.category,
                    "supplier_code": supplier.code,
                    "supplier_name": supplier.name,
                    "unit_cost": unit_cost,
                    "recommended_price": recommended_price,
                    "currency": CURRENCY,
                    # Looks like something an export might include, but not something the app should expose directly.
                    "internal_popularity_weight": round(rng.uniform(0.75, 1.35), 2),
                }
            )

    return pd.DataFrame(rows)


def generate_store_geography(rng: random.Random) -> pd.DataFrame:
    rows = []
    store_counter = 1

    for region, cities in REGIONS_AND_CITIES.items():
        for city in cities:
            stores_in_city = rng.randint(1, 3)

            for _ in range(stores_in_city):
                rows.append(
                    {
                        "store_id": f"STORE-{store_counter:04d}",
                        "store_name": f"{city} Store {store_counter:03d}",
                        "sales_channel": "Store",
                        "country": "Sweden",
                        "region": region,
                        "city": city,
                    }
                )
                store_counter += 1

    # Online is represented as virtual sales locations.
    for region in ["Stockholm", "Västra Götaland", "Skåne"]:
        rows.append(
            {
                "store_id": f"WEB-{store_counter:04d}",
                "store_name": f"Online {region}",
                "sales_channel": "Online",
                "country": "Sweden",
                "region": region,
                "city": "Online",
            }
        )
        store_counter += 1

    return pd.DataFrame(rows)


def generate_raw_sales_export(
    rng: random.Random,
    product_master: pd.DataFrame,
    store_geography: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    order_counter = 1
    line_counter = 1

    products_by_supplier = {
        supplier.code: product_master[product_master["supplier_code"] == supplier.code].to_dict("records")
        for supplier in SUPPLIERS
    }

    stores_by_region = {
        region: store_geography[store_geography["region"] == region].to_dict("records")
        for region in REGIONS_AND_CITIES.keys()
    }

    all_stores = store_geography.to_dict("records")
    regions = list(REGIONS_AND_CITIES.keys())

    for current_date in date_range(START_DATE, END_DATE):
        is_weekend = current_date.weekday() >= 5

        day_factor = 0.78 if is_weekend else 1.0
        payday_factor = 1.15 if current_date.day in [24, 25, 26, 27, 28] else 1.0
        holiday_factor = 1.25 if current_date.month in [11, 12] else 1.0

        for supplier in SUPPLIERS:
            supplier_products = products_by_supplier[supplier.code]

            trend_factor = max(0.50, 1 + supplier.monthly_trend * month_number(current_date))
            expected_orders = 3.8 * day_factor * payday_factor * holiday_factor * trend_factor
            order_count = max(1, int(expected_orders + rng.random() * 2.5))

            region_weights = [
                REGION_WEIGHTS[region] * supplier.region_bias.get(region, 1.0)
                for region in regions
            ]

            for _ in range(order_count):
                preferred_region = weighted_choice(rng, regions, region_weights)
                store = rng.choice(stores_by_region.get(preferred_region) or all_stores)

                order_id = f"ORD-{order_counter:07d}"
                lines_in_order = rng.choice([1, 1, 1, 2, 2, 3])

                customer_segment = rng.choices(
                    CUSTOMER_SEGMENTS,
                    weights=[0.55, 0.35, 0.10],
                    k=1,
                )[0]

                anonymized_customer_id = f"ANON-{rng.randint(1, 5000):05d}"

                for _ in range(lines_in_order):
                    product_weights = [
                        product["internal_popularity_weight"]
                        * category_seasonality(product["category"], current_date)
                        for product in supplier_products
                    ]

                    product = rng.choices(supplier_products, weights=product_weights, k=1)[0]

                    unit_price = price_with_noise(rng, int(product["recommended_price"]))
                    quantity = pick_quantity(rng, customer_segment, unit_price)
                    discount_percent = pick_discount_percent(rng, current_date, customer_segment)

                    gross_sales = quantity * unit_price
                    net_sales = round(gross_sales * (1 - discount_percent / 100), 2)
                    unit_cost = int(product["unit_cost"])
                    estimated_margin = round(net_sales - quantity * unit_cost, 2)

                    rows.append(
                        {
                            # This is intentionally flat/duplicated, like a raw Excel export.
                            "order_id": order_id,
                            "order_line_id": f"LINE-{line_counter:08d}",
                            "order_date": current_date.isoformat(),
                            "week_start": iso_week_start(current_date),
                            "month": current_date.strftime("%Y-%m"),
                            "store_id": store["store_id"],
                            "store_name": store["store_name"],
                            "sales_channel": store["sales_channel"],
                            "country": store["country"],
                            "region": store["region"],
                            "city": store["city"],
                            "customer_segment": customer_segment,
                            "anonymized_customer_id": anonymized_customer_id,
                            "supplier_code": product["supplier_code"],
                            "supplier_name": product["supplier_name"],
                            "brand": product["brand"],
                            "sku": product["sku"],
                            "product_name": product["product_name"],
                            "category": product["category"],
                            "quantity": quantity,
                            "unit_price": unit_price,
                            "discount_percent": discount_percent,
                            "gross_sales": gross_sales,
                            "net_sales": net_sales,
                            "estimated_margin": estimated_margin,
                            "currency": CURRENCY,
                        }
                    )

                    line_counter += 1

                order_counter += 1

    return pd.DataFrame(rows)


def add_market_benchmark_columns(report: pd.DataFrame, supplier_lookup: dict[str, Supplier]) -> pd.DataFrame:
    rows = []

    for row in report.to_dict("records"):
        supplier = supplier_lookup[row["supplier_code"]]

        # Static legacy reports have market comparison, but only aggregated.
        # They do not reveal competitor raw rows or competitor product details.
        market_share = supplier.base_market_share + random.uniform(-0.045, 0.045)
        market_share = max(0.12, min(0.60, market_share))

        supplier_revenue = float(row["supplier_revenue"])
        supplier_units = int(row["supplier_units"])
        supplier_orders = int(row["supplier_orders"])

        row["comparable_market_revenue"] = round(supplier_revenue / market_share, 2)
        row["comparable_market_units"] = int(round(supplier_units / market_share))
        row["comparable_market_orders"] = int(round(supplier_orders / market_share))
        row["estimated_market_share_pct"] = round(market_share * 100, 2)

        rows.append(row)

    return pd.DataFrame(rows)


def generate_static_reports(raw_sales: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    supplier_lookup = {supplier.code: supplier for supplier in SUPPLIERS}

    weekly = (
        raw_sales
        .groupby(["supplier_code", "supplier_name", "week_start"], as_index=False)
        .agg(
            supplier_revenue=("net_sales", "sum"),
            supplier_units=("quantity", "sum"),
            supplier_orders=("order_id", "nunique"),
        )
        .sort_values(["supplier_code", "week_start"])
    )

    monthly = (
        raw_sales
        .groupby(["supplier_code", "supplier_name", "month"], as_index=False)
        .agg(
            supplier_revenue=("net_sales", "sum"),
            supplier_units=("quantity", "sum"),
            supplier_orders=("order_id", "nunique"),
        )
        .sort_values(["supplier_code", "month"])
    )

    weekly = add_market_benchmark_columns(weekly, supplier_lookup)
    monthly = add_market_benchmark_columns(monthly, supplier_lookup)

    weekly["supplier_revenue"] = weekly["supplier_revenue"].round(2)
    monthly["supplier_revenue"] = monthly["supplier_revenue"].round(2)

    return weekly, monthly


def autosize_columns(writer: pd.ExcelWriter, sheet_name: str, dataframe: pd.DataFrame) -> None:
    worksheet = writer.sheets[sheet_name]

    for column_index, column_name in enumerate(dataframe.columns, start=1):
        sample_values = dataframe[column_name].head(500).astype(str).tolist()
        max_length = max([len(str(column_name)), *(len(value) for value in sample_values)])
        adjusted_width = min(max(max_length + 2, 10), 36)

        column_letter = worksheet.cell(row=1, column=column_index).column_letter
        worksheet.column_dimensions[column_letter].width = adjusted_width

    worksheet.freeze_panes = "A2"


def write_excel(path: Path, sheets: dict[str, pd.DataFrame]) -> None:
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, dataframe in sheets.items():
            dataframe.to_excel(writer, sheet_name=sheet_name, index=False)
            autosize_columns(writer, sheet_name, dataframe)


def main() -> None:
    rng = random.Random(RANDOM_SEED)
    random.seed(RANDOM_SEED)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for existing_file in OUTPUT_DIR.glob("*.xlsx"):
        existing_file.unlink()

    supplier_master = generate_supplier_master()
    product_master = generate_product_master(rng)
    store_geography = generate_store_geography(rng)
    raw_sales = generate_raw_sales_export(rng, product_master, store_geography)
    weekly_report, monthly_report = generate_static_reports(raw_sales)

    readme = pd.DataFrame(
        [
            {
                "file": "raw_retail_sales_export.xlsx",
                "description": "Flat raw sales export from retailer sales systems. Intentionally denormalized.",
            },
            {
                "file": "product_master_export.xlsx",
                "description": "Product catalog / master data export.",
            },
            {
                "file": "store_geography_export.xlsx",
                "description": "Store, sales channel, and geography export.",
            },
            {
                "file": "legacy_supplier_reports.xlsx",
                "description": "Static weekly/monthly supplier reports with aggregated market benchmark columns.",
            },
            {
                "file": "important_note",
                "description": (
                    "These files represent the legacy data/reporting situation. "
                    "They are not intended to mirror the normalized database schema."
                ),
            },
        ]
    )

    write_excel(OUTPUT_DIR / "raw_retail_sales_export.xlsx", {"Sales_Export": raw_sales})
    write_excel(OUTPUT_DIR / "product_master_export.xlsx", {"Products": product_master})
    write_excel(OUTPUT_DIR / "supplier_master_export.xlsx", {"Suppliers": supplier_master})
    write_excel(OUTPUT_DIR / "store_geography_export.xlsx", {"Stores": store_geography})
    write_excel(
        OUTPUT_DIR / "legacy_supplier_reports.xlsx",
        {
            "README": readme,
            "Weekly_Reports": weekly_report,
            "Monthly_Reports": monthly_report,
        },
    )

    print("Generated legacy-style retail dataset:")
    print(f"- suppliers: {len(supplier_master)}")
    print(f"- products: {len(product_master)}")
    print(f"- stores/online locations: {len(store_geography)}")
    print(f"- raw sales rows: {len(raw_sales)}")
    print(f"- weekly report rows: {len(weekly_report)}")
    print(f"- monthly report rows: {len(monthly_report)}")
    print()
    print(f"Output folder: {OUTPUT_DIR.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()