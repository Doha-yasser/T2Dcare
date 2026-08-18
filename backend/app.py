import os
from pathlib import Path
from deep_translator import GoogleTranslator
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
import pandas as pd
import requests

# =========================
# LOAD ENVIRONMENT VARIABLES
# =========================

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)


# =========================
# FLASK APP
# =========================

app = Flask(__name__, static_folder=str(ROOT_DIR), template_folder=str(ROOT_DIR), static_url_path="")


# =========================
# APIs CONFIG
# =========================

SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY")
SPOONACULAR_SEARCH_URL = "https://api.spoonacular.com/recipes/complexSearch"


# =========================
# LOAD EGYPTIAN CSV DATASET
# =========================

csv_path = BASE_DIR / "egyptian food cleaned.csv"

try:
    egyptian_df = pd.read_csv(csv_path)
    egyptian_df.columns = egyptian_df.columns.str.strip()
except Exception as e:
    print("CSV Load Error:", e)
    egyptian_df = pd.DataFrame()


# =========================
# DYNAMIC INGREDIENT ENGINE
# =========================

INGREDIENT_NUTRIENTS = {
    "egg": {"calories": 75, "carbs": 0.5, "protein": 6.3, "fat": 5.0},
    "yellow lentil": {"calories": -10, "carbs": -2.8, "protein": 1.5, "fat": -1.2},
    "butter": {"calories": 100, "carbs": 0.0, "protein": 0.1, "fat": 11.0},
    "ghee": {"calories": 112, "carbs": 0.0, "protein": 0.0, "fat": 12.7},
    "cheese": {"calories": 80, "carbs": 0.8, "protein": 5.0, "fat": 6.5},
    "nuts": {"calories": 90, "carbs": 3.0, "protein": 3.0, "fat": 8.0},
    "cream": {"calories": 85, "carbs": 0.8, "protein": 0.6, "fat": 9.0},
    "sugar": {"calories": 40, "carbs": 10.0, "protein": 0.0, "fat": 0.0},
}

def calculate_dynamic_nutrition(row, food_title):
    """Calculates calories and macros dynamically to avoid repetition in Dataset."""
    cal = float(row.get("calories_per_100g", 0) if pd.notna(row.get("calories_per_100g")) else 0)
    fat = float(row.get("fats_per_100g", 0) if pd.notna(row.get("fats_per_100g")) else 0)
    protein = float(row.get("protein_per_100g", 0) if pd.notna(row.get("protein_per_100g")) else 0)
    carbs = float(row.get("carbs_per_100g", 0) if pd.notna(row.get("carbs_per_100g")) else 0)

    ingredients = str(row.get("ingredients_en", "")).lower()
    title_lower = str(food_title).lower()

    for item, values in INGREDIENT_NUTRIENTS.items():
        if item in ingredients or item in title_lower:
            if item in ["egg", "yellow lentil"] and "koshari" in title_lower:
                cal += values["calories"]
                carbs += values["carbs"]
                protein += values["protein"]
                fat += values["fat"]

    return max(0.0, cal), max(0.0, carbs), max(0.0, protein), max(0.0, fat)


# =========================
# T2D SMART SUBSTITUTIONS
# =========================

def get_smart_substitutions(ingredients_str, food_title):
    """Healthy substitutions suggestions for diabetics."""
    substitutions = []
    ing_lower = str(ingredients_str).lower()
    title_lower = str(food_title).lower()

    if any(w in ing_lower or w in title_lower for w in ["sugar", "honey", "syrup", "milk"]):
        if "rice with milk" in title_lower or "feteer" in title_lower:
            substitutions.append({
                "ingredient": "Added Sugar / Honey",
                "replacement": "Stevia / Erythritol",
                "cal_saved": 40,
                "carbs_saved": 10.0,
                "reason": "Prevents blood sugar spikes and eliminates added carbs."
            })

    if any(w in ing_lower or w in title_lower for w in ["fried", "ghee", "oil", "butter"]):
        substitutions.append({
            "ingredient": "Deep Frying / Butter",
            "replacement": "Air Frying + Spray Olive Oil",
            "cal_saved": 80,
            "carbs_saved": 0.0,
            "reason": "Reduces saturated fats and improves insulin sensitivity."
        })

    if any(w in ing_lower for w in ["pasta", "rice", "flour"]):
        substitutions.append({
            "ingredient": "White Carbs (Rice/Pasta/Flour)",
            "replacement": "Brown Rice / Whole Wheat / Oats",
            "cal_saved": 20,
            "carbs_saved": 4.0,
            "reason": "Rich in fiber which slows down glucose absorption."
        })

    return substitutions


# =========================
# DIABETES ADVICE
# =========================

def generate_diabetes_advice(carbs, calories=0, fat=0, fiber=0):
    """Generate diabetes-friendly advice based on carbohydrates, calories and fat."""
    if carbs > 45:
        return {
            "status": "warning",
            "badge": "⚠️ High Glycemic Impact",
            "tip": "Very high in carbohydrates and sugars! Causes a rapid spike in blood sugar. Reduce portion size.",
        }
    elif carbs <= 30 and (calories > 600 or fat > 35):
        return {
            "status": "info",
            "badge": "ℹ️ Low Carb / High Calorie",
            "tip": "Low in carbohydrates, but rich in calories and fats! Consume a moderate portion.",
        }
    elif carbs <= 30:
        return {
            "status": "success",
            "badge": "✅ Diabetes Friendly",
            "tip": "Excellent and healthy choice! Low carbohydrate content with a balanced effect on blood sugar levels.",
        }
    else:
        return {
            "status": "info",
            "badge": "ℹ️ Moderate Impact",
            "tip": "Moderate carbohydrates. Ensure meal balance and control added starch intake.",
        }


# =========================
# UTILS: EXTRACT IMAGE URL
# =========================

def extract_image_url(row):
    """Extracts image URL from CSV if exists, otherwise returns empty string."""
    for img_col in ["image", "image_url", "img", "picture"]:
        if img_col in row and pd.notna(row[img_col]) and str(row[img_col]).strip():
            return str(row[img_col]).strip()
    return ""


# =========================
# HOME & CATEGORIES
# =========================

@app.route("/")
def home():
    return send_from_directory(str(ROOT_DIR), "index.html")

@app.route("/api/categories", methods=["GET"])
def get_categories():
    if not egyptian_df.empty:
        cat_col = None
        for col in ["main_category_en", "main_category_ar", "category"]:
            if col in egyptian_df.columns:
                cat_col = col
                break
        
        if cat_col:
            categories = egyptian_df[cat_col].dropna().astype(str).str.strip().unique().tolist()
            categories = [c for c in categories if c and c.lower() != 'nan']
            return jsonify({"categories": sorted(categories)})
            
    return jsonify({"categories": []})


# =========================
# SEARCH FOODS (HYBRID SYSTEM)
# =========================

@app.route("/api/foods", methods=["GET"])
def search_foods():
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    if not query and not category:
        return jsonify({"error": "Please enter a food name or choose a category."}), 400

    # ==========================================
    # 1. SEARCH EGYPTIAN CSV
    # ==========================================
    if not egyptian_df.empty:
        df_clean = egyptian_df.copy()

        # Dynamic Category Column Check
        cat_col = None
        for col in ["main_category_en", "main_category_ar", "category"]:
            if col in df_clean.columns:
                cat_col = col
                break

        # Filter by category if selected
        if category and cat_col:
            df_clean = df_clean[df_clean[cat_col].astype(str).str.strip().str.casefold() == category.casefold()]

        if not query:
            matches = df_clean.head(10).copy()
            matches["match_type"] = "direct"
        else:
            ar_col = "food_name_ar" if "food_name_ar" in df_clean.columns else df_clean.columns[0]
            en_col = "food_name_en" if "food_name_en" in df_clean.columns else df_clean.columns[0]

            name_mask = (
                df_clean[ar_col].astype(str).str.contains(query, case=False, na=False) |
                df_clean[en_col].astype(str).str.contains(query, case=False, na=False)
            )
            exact_matches = df_clean[name_mask].copy()
            if not exact_matches.empty:
                exact_matches["match_type"] = "direct"

            ing_mask = pd.Series(False, index=df_clean.index)
            if "ingredients_en" in df_clean.columns:
                ing_mask = df_clean["ingredients_en"].astype(str).str.contains(query, case=False, na=False) & (~name_mask)

            ing_matches = df_clean[ing_mask].copy()
            if not ing_matches.empty:
                ing_matches["match_type"] = "ingredient"

            matches = pd.concat([exact_matches, ing_matches])

        if not matches.empty:
            results = []
            for idx, (_, row) in enumerate(matches.head(8).iterrows()):
                food_title = row.get("food_name_en" if "food_name_en" in row else row.index[0], query)
                image_url = extract_image_url(row)
                match_type = row.get("match_type", "direct")

                calories, carbs, protein, fat = calculate_dynamic_nutrition(row, food_title)
                advice = generate_diabetes_advice(carbs=carbs, calories=calories, fat=fat)
                substitutions = get_smart_substitutions(row.get("ingredients_en", ""), food_title)

                category_val = str(row.get(cat_col, "General")) if cat_col else "General"

                results.append({
                    "id": int(row.get("food_id", idx)),
                    "description": food_title,
                    "category": category_val,
                    "image": image_url,
                    "calories": round(calories),
                    "carbs": round(carbs, 1),
                    "protein": round(protein, 1),
                    "fat": round(fat, 1),
                    "match_type": match_type,
                    "ingredient_note": f"Contains '{query}' in ingredients" if match_type == "ingredient" else "",
                    "advice": advice,
                    "substitutions": substitutions
                })

            if results:
                return jsonify({"foods": results})

    # ==========================================
    # 2. FALLBACK TO SPOONACULAR API
    # ==========================================
    if SPOONACULAR_API_KEY and query:
        try:
            try:
                translated_query = GoogleTranslator(source="auto", target="en").translate(query)
            except Exception:
                translated_query = query

            params = {
                "apiKey": SPOONACULAR_API_KEY,
                "query": translated_query,
                "number": 6,
                "addRecipeNutrition": "true",
            }

            res = requests.get(SPOONACULAR_SEARCH_URL, params=params, timeout=8)

            if res.status_code == 200:
                data = res.json().get("results", [])
                formatted_foods = []

                for item in data:
                    nutrients_list = item.get("nutrition", {}).get("nutrients", [])
                    nutrients = {n["name"]: n["amount"] for n in nutrients_list}

                    carbs = nutrients.get("Carbohydrates", 0)
                    calories = nutrients.get("Calories", 0)
                    fat = nutrients.get("Fat", 0)
                    fiber = nutrients.get("Fiber", 0)
                    protein = nutrients.get("Protein", 0)

                    formatted_foods.append({
                        "id": item.get("id"),
                        "description": item.get("title"),
                        "image": item.get("image", ""),
                        "calories": round(calories),
                        "carbs": round(carbs, 1),
                        "protein": round(protein, 1),
                        "fat": round(fat, 1),
                        "match_type": "direct",
                        "ingredient_note": "",
                        "advice": generate_diabetes_advice(carbs, calories, fat, fiber),
                        "substitutions": []
                    })

                return jsonify({"foods": formatted_foods})

            else:
                print("Spoonacular status:", res.status_code)

        except Exception as e:
            print("Spoonacular Error:", e)

    return jsonify({"foods": []})


# =========================
# RUN APP
# =========================

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)