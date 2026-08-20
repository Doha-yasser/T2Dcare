"""
One-time migration: loads egyptian food cleaned.csv into database.db's
`foods` table. Run this once from the backend/ folder:

    python migrate_foods_to_db.py

Safe to re-run: it clears the foods table first, so running it again just
re-imports fresh data from the CSV (e.g. after you update the CSV).
"""

import sqlite3
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database.db"
CSV_PATH = BASE_DIR / "egyptian food cleaned.csv"


def pick_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None


def extract_image_url(row):
    for img_col in ["image", "image_url", "img", "picture"]:
        if img_col in row and pd.notna(row[img_col]) and str(row[img_col]).strip():
            return str(row[img_col]).strip()
    return ""


def main():
    df = pd.read_csv(CSV_PATH)
    df.columns = df.columns.str.strip()

    en_col = pick_col(df, ["food_name_en"]) or df.columns[0]
    ar_col = pick_col(df, ["food_name_ar"])
    cat_col = pick_col(df, ["main_category_en", "main_category_ar", "category"])
    ing_col = pick_col(df, ["ingredients_en"])

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("DELETE FROM foods")  # safe to re-run

    inserted = 0
    for _, row in df.iterrows():
        food_name_en = str(row.get(en_col, "")).strip()
        if not food_name_en or food_name_en.lower() == "nan":
            continue

        food_name_ar = str(row.get(ar_col, "")).strip() if ar_col else ""
        category = str(row.get(cat_col, "General")).strip() if cat_col else "General"
        ingredients_en = str(row.get(ing_col, "")).strip() if ing_col else ""

        def to_float(val):
            try:
                return float(val) if pd.notna(val) else 0.0
            except (TypeError, ValueError):
                return 0.0

        calories = to_float(row.get("calories_per_100g"))
        carbs = to_float(row.get("carbs_per_100g"))
        protein = to_float(row.get("protein_per_100g"))
        fats = to_float(row.get("fats_per_100g"))
        image_url = extract_image_url(row)

        conn.execute(
            """INSERT INTO foods
                (food_name_en, food_name_ar, category, ingredients_en,
                 calories_per_100g, carbs_per_100g, protein_per_100g, fats_per_100g, image_url)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (food_name_en, food_name_ar, category, ingredients_en,
             calories, carbs, protein, fats, image_url),
        )
        inserted += 1

    conn.commit()
    conn.close()
    print(f"Migrated {inserted} foods into {DB_PATH}")


if __name__ == "__main__":
    main()
