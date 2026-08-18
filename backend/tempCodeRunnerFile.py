from flask import Flask, request, jsonify, send_from_directory
import requests
import os
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from deep_translator import GoogleTranslator


# =========================================================
# APP CONFIGURATION
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

app = Flask(
    __name__,
    static_folder="..",
    static_url_path=""
)


# =========================================================
# API CONFIGURATION
# =========================================================

SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY")
SPOONACULAR_SEARCH_URL = (
    "https://api.spoonacular.com/recipes/complexSearch"
)

EDAMAM_APP_ID = os.getenv("EDAMAM_APP_ID")
EDAMAM_APP_KEY = os.getenv("EDAMAM_APP_KEY")

EDAMAM_URL = (
    "https://api.edamam.com/api/nutrition-data"
)


# =========================================================
# DEBUG
# =========================================================

print("\n==============================")
print("T2D CARE SERVER")
print("==============================")

print("CSV directory:", BASE_DIR)
print("Edamam App ID exists:", bool(EDAMAM_APP_ID))
print("Edamam App Key exists:", bool(EDAMAM_APP_KEY))
print("Spoonacular Key exists:", bool(SPOONACULAR_API_KEY))

print("==============================\n")


# =========================================================
# LOAD EGYPTIAN FOOD DATASET
# =========================================================

csv_path = (
    BASE_DIR /
    "Copy of Egyptian_Food_Combined_with_Original.csv"
)

try:

    egyptian_df = pd.read_csv(
        csv_path,
        encoding="utf-8"
    )

    egyptian_df.columns = (
        egyptian_df.columns
        .astype(str)
        .str.strip()
    )

    print("CSV loaded successfully.")
    print("CSV columns:")
    print(egyptian_df.columns.tolist())
    print("CSV rows:", len(egyptian_df))

except Exception as e:

    print("CSV Load Error:", e)

    egyptian_df = pd.DataFrame()


# =========================================================
# FALLBACK FOOD IMAGES
# =========================================================

FOOD_IMAGES_DATABASE = [

    "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?q=80&w=600",

    "https://images.unsplash.com/photo-1541544741938-0af808871cc0?q=80&w=600",

    "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?q=80&w=600",

    "https://images.unsplash.com/photo-1546833999-b9f581a1996d?q=80&w=600",

    "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?q=80&w=600"
]


# =========================================================
# INGREDIENTS TO IGNORE
# =========================================================

EXCLUDED_INGREDIENTS = {

    "salt",
    "black pepper",
    "pepper",
    "spices",
    "water",

    "ملح",
    "فلفل اسود",
    "فلفل",
    "بهارات",
    "مياه",
    "ماء"
}


# =========================================================
# ESTIMATED INGREDIENT WEIGHTS
# =========================================================

INGREDIENT_WEIGHTS = {

    # Protein
    "liver": 150,
    "كبدة": 150,

    "chicken": 150,
    "دجاج": 150,

    "meat": 150,
    "لحمة": 150,
    "لحم": 150,

    "beef": 150,
    "لحم بقري": 150,

    "shrimp": 120,
    "جمبري": 120,

    "fish": 150,
    "سمك": 150,

    "egg": 55,
    "بيض": 55,


    # Carbohydrates
    "rice": 150,
    "أرز": 150,

    "pasta": 150,
    "مكرونة": 150,

    "bread": 60,
    "عيش": 60,
    "خبز": 60,

    "potato": 150,
    "بطاطس": 150,


    # Legumes / Vegetables
    "lentils": 100,
    "عدس": 100,

    "peas": 80,
    "بسلة": 80,

    "beans": 100,
    "فول": 100,

    "fava beans": 100,

    "onion": 40,
    "بصل": 40,

    "tomato": 60,
    "طماطم": 60,

    "garlic": 5,
    "ثوم": 5,


    # Oils / Fats
    "oil": 10,
    "زيت": 10,

    "ghee": 10,
    "سمنة": 10,

    "ghee baladi": 10,

    "butter": 10,
    "زبدة": 10,


    # Vegetables
    "okra": 100,
    "بامية": 100,

    "molokhia": 100,
    "ملوخية": 100,

    "zucchini": 100,
    "كوسة": 100,

    "sauce": 30,
    "صلصة": 30
}


DEFAULT_INGREDIENT_WEIGHT = 80


# =========================================================
# GET INGREDIENT WEIGHT
# =========================================================

def get_ingredient_weight(ingredient_name):

    name_lower = (
        str(ingredient_name)
        .strip()
        .lower()
    )

    for key, weight in INGREDIENT_WEIGHTS.items():

        if key in name_lower:
            return weight

    return DEFAULT_INGREDIENT_WEIGHT


# =========================================================
# DIABETES ADVICE
# =========================================================

def generate_diabetes_advice_from_nutrition(
    food_title,
    net_carbs,
    calories=0,
    fat=0,
    fiber=0
):

    title_lower = str(food_title).lower()

    # Drinks
    if (
        "juice" in title_lower
        or "smoothie" in title_lower
        or "drink" in title_lower
        or "عصير" in title_lower
    ):

        return {

            "status": "warning",

            "badge": "⚠️ High Glycemic Impact",

            "tip":
                "العصائر قد ترفع مستوى السكر بسرعة، "
                "ويُفضل تناول الفاكهة كاملة بدلًا من العصير."
        }


    # High carbohydrate
    if (
        net_carbs > 25
        or "rice" in title_lower
        or "potato" in title_lower
        or "pasta" in title_lower
        or "أرز" in title_lower
        or "بطاطس" in title_lower
        or "مكرونة" in title_lower
    ):

        return {

            "status": "warning",

            "badge": "⚠️ High Glycemic Impact",

            "tip":
                f"تحتوي الحصة على حوالي "
                f"{net_carbs}g صافي كربوهيدرات. "
                "يُنصح بالاعتدال في حجم الحصة "
                "وموازنة الوجبة مع الخضروات والبروتين."
        }


    # Moderate carbohydrate
    elif 12 < net_carbs <= 25:

        return {

            "status": "info",

            "badge": "ℹ️ Moderate Impact",

            "tip":
                f"تحتوي الحصة على حوالي "
                f"{net_carbs}g صافي كربوهيدرات. "
                "يفضل الانتباه إلى حجم الحصة "
                "وتوازن باقي الوجبة."
        }


    # Low carbohydrate
    else:

        if calories > 500 or fat > 30:

            return {

                "status": "info",

                "badge": "ℹ️ Low Carb / Higher Calories",

                "tip":
                    "منخفضة نسبيًا في الكربوهيدرات "
                    "لكنها قد تكون مرتفعة في السعرات أو الدهون، "
                    "لذلك يُفضل الاعتدال في حجم الحصة."
            }

        else:

            return {

                "status": "success",

                "badge": "✅ Diabetes Friendly",

                "tip":
                    "خيار منخفض نسبيًا في الكربوهيدرات. "
                    "يفضل تناوله ضمن وجبة متوازنة "
                    "مع مراعاة حجم الحصة."
            }


# =========================================================
# EDAMAM ANALYSIS
# =========================================================

def analyze_with_edamam_api(
    ingredients_text,
    food_title
):

    if not EDAMAM_APP_ID or not EDAMAM_APP_KEY:

        print(
            "Edamam credentials are missing."
        )

        return None


    if not ingredients_text:

        print(
            "No ingredients found for:",
            food_title
        )

        return None


    if str(ingredients_text).lower() == "nan":

        return None


    # -----------------------------------------------------
    # Split ingredients
    # -----------------------------------------------------

    raw_list = [

        ingredient.strip()

        for ingredient
        in str(ingredients_text).split(",")

        if ingredient.strip()
    ]


    # -----------------------------------------------------
    # Remove insignificant ingredients
    # -----------------------------------------------------

    filtered_list = []

    for item in raw_list:

        if (
            item.strip().lower()
            not in EXCLUDED_INGREDIENTS
        ):

            filtered_list.append(item)


    if not filtered_list:

        filtered_list = raw_list


    # -----------------------------------------------------
    # Take main ingredients
    # -----------------------------------------------------

    ingredient_parts = []

    for item in filtered_list[:5]:

        weight = get_ingredient_weight(item)

        ingredient_parts.append(
            f"{weight}g {item}"
        )


    if not ingredient_parts:

        return None


    formatted_ingr = " and ".join(
        ingredient_parts
    )


    print("\n------------------------------")
    print("EDAMAM REQUEST")
    print("Food:", food_title)
    print("Ingredients:", formatted_ingr)


    # -----------------------------------------------------
    # Request parameters
    # -----------------------------------------------------

    params = {

        "app_id": EDAMAM_APP_ID,

        "app_key": EDAMAM_APP_KEY,

        "nutrition-type": "logging",

        "ingr": formatted_ingr
    }


    try:

        response = requests.get(
            EDAMAM_URL,
            params=params,
            timeout=10
        )


        print(
            "Edamam status:",
            response.status_code
        )


        print(
            "Edamam response:",
            response.text[:1000]
        )


        if response.status_code != 200:

            print(
                "Edamam API failed."
            )

            return None


        data = response.json()


        nutrients = data.get(
            "totalNutrients",
            {}
        )


        # -------------------------------------------------
        # Extract nutrients
        # -------------------------------------------------

        total_carbs = (

            nutrients
            .get("CHOCDF", {})
            .get("quantity", 0)
        )


        calories = data.get(
            "calories",
            0
        )


        protein = (

            nutrients
            .get("PROCNT", {})
            .get("quantity", 0)
        )


        fat = (

            nutrients
            .get("FAT", {})
            .get("quantity", 0)
        )


        fiber = (

            nutrients
            .get("FIBTG", {})
            .get("quantity", 0)
        )


        net_carbs = max(
            0,
            total_carbs - fiber
        )


        if calories <= 0:

            print(
                "Edamam returned no calories."
            )

            return None


        advice = (
            generate_diabetes_advice_from_nutrition(
                food_title,
                round(net_carbs, 1),
                calories,
                fat,
                fiber
            )
        )


        result = {

            "calories": round(calories),

            "carbs": round(
                total_carbs,
                1
            ),

            "protein": round(
                protein,
                1
            ),

            "fat": round(
                fat,
                1
            ),

            "advice": advice,

            "is_estimated": True
        }


        print(
            "Edamam nutrition:",
            result
        )

        print("------------------------------\n")


        return result


    except Exception as error:

        print(
            "Edamam API Exception:",
            repr(error)
        )

        return None


# =========================================================
# FALLBACK ESTIMATION
# =========================================================

def create_fallback_nutrition(
    ingredients_text,
    food_title
):

    """
    Fallback بسيط جدًا في حالة فشل Edamam.
    الهدف منه عدم إظهار نتيجة فارغة للمستخدم.
    """

    if not ingredients_text:

        return None


    ingredients = [

        item.strip().lower()

        for item
        in str(ingredients_text).split(",")

        if item.strip()
    ]


    calories = 0
    carbs = 0
    protein = 0
    fat = 0


    # -----------------------------------------------------
    # Approximate nutritional values per selected portion
    # -----------------------------------------------------

    nutrition_values = {

        "rice":
            (195, 42, 4, 0.5),

        "أرز":
            (195, 42, 4, 0.5),


        "pasta":
            (220, 43, 8, 1.5),

        "مكرونة":
            (220, 43, 8, 1.5),


        "potato":
            (115, 26, 3, 0.1),

        "بطاطس":
            (115, 26, 3, 0.1),


        "oil":
            (90, 0, 0, 10),

        "زيت":
            (90, 0, 0, 10),


        "ghee":
            (90, 0, 0, 10),

        "سمنة":
            (90, 0, 0, 10),


        "onion":
            (16, 4, 0.4, 0.1),

        "بصل":
            (16, 4, 0.4, 0.1),


        "tomato":
            (11, 2.5, 0.5, 0.1),

        "طماطم":
            (11, 2.5, 0.5, 0.1),


        "okra":
            (33, 7, 2, 0.2),

        "بامية":
            (33, 7, 2, 0.2),


        "liver":
            (200, 7, 30, 7),

        "كبدة":
            (200, 7, 30, 7),


        "chicken":
            (250, 0, 46, 5),

        "دجاج":
            (250, 0, 46, 5),


        "beef":
            (300, 0, 38, 16),

        "لحم":
            (300, 0, 38, 16),

        "لحمة":
            (300, 0, 38, 16),


        "fish":
            (180, 0, 38, 4),

        "سمك":
            (180, 0, 38, 4),


        "shrimp":
            (120, 1, 24, 2),

        "جمبري":
            (120, 1, 24, 2),


        "beans":
            (110, 20, 7, 0.5),

        "فول":
            (110, 20, 7, 0.5),


        "fava beans":
            (110, 20, 7, 0.5),


        "lentils":
            (115, 20, 9, 0.5),

        "عدس":
            (115, 20, 9, 0.5)
    }


    # -----------------------------------------------------
    # Calculate
    # -----------------------------------------------------

    for ingredient in ingredients:

        matched = False

        for key, values in nutrition_values.items():

            if key in ingredient:

                cals, carb, prot, fat_value = values

                calories += cals
                carbs += carb
                protein += prot
                fat += fat_value

                matched = True

                break


        if not matched:

            # Unknown ingredient
            # ignore rather than inventing huge values
            continue


    if calories <= 0:

        return None


    net_carbs = max(
        0,
        carbs
    )


    advice = (
        generate_diabetes_advice_from_nutrition(
            food_title,
            round(net_carbs, 1),
            calories,
            fat,
            0
        )
    )


    return {

        "calories": round(calories),

        "carbs": round(
            carbs,
            1
        ),

        "protein": round(
            protein,
            1
        ),

        "fat": round(
            fat,
            1
        ),

        "advice": advice,

        "is_estimated": True
    }


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def home():

    return send_from_directory(
        "..",
        "index.html"
    )


# =========================================================
# FOOD SEARCH API
# =========================================================

@app.route(
    "/api/foods",
    methods=["GET"]
)
def search_foods():

    query = request.args.get(
        "q",
        ""
    ).strip()


    if not query:

        return jsonify({

            "error":
                "Please enter a food name."

        }), 400


    print("\n================================")
    print("FOOD SEARCH:", query)
    print("================================")


    # =====================================================
    # 1. SEARCH LOCAL CSV
    # =====================================================

    if not egyptian_df.empty:

        ar_col = "food_name_ar"

        en_col = "food_name_en"


        # Safety check
        if (
            ar_col not in egyptian_df.columns
            or
            en_col not in egyptian_df.columns
        ):

            print(
                "Required CSV columns are missing."
            )

        else:

            matches = egyptian_df[

                egyptian_df[ar_col]
                .astype(str)
                .str.contains(
                    query,
                    case=False,
                    na=False
                )

                |

                egyptian_df[en_col]
                .astype(str)
                .str.contains(
                    query,
                    case=False,
                    na=False
                )
            ]


            print(
                "CSV matches:",
                len(matches)
            )


            if not matches.empty:

                results = []


                # Take first matching food
                for idx, (_, row) in enumerate(
                    matches.head(1).iterrows()
                ):

                    food_title = str(
                        row.get(
                            en_col,
                            query
                        )
                    )


                    ingredients = row.get(
                        "ingredients_en",
                        ""
                    )


                    image_url = row.get(
                        "image_url",
                        ""
                    )


                    # -------------------------------------------------
                    # Try Edamam
                    # -------------------------------------------------

                    nutrition = (
                        analyze_with_edamam_api(
                            ingredients,
                            food_title
                        )
                    )


                    # -------------------------------------------------
                    # Fallback if Edamam fails
                    # -------------------------------------------------

                    if nutrition is None:

                        print(
                            "Using fallback nutrition "
                            "for:",
                            food_title
                        )


                        nutrition = (
                            create_fallback_nutrition(
                                ingredients,
                                food_title
                            )
                        )


                    # -------------------------------------------------
                    # Add result
                    # -------------------------------------------------

                    if nutrition is not None:

                        results.append({

                            "description":
                                food_title,

                            "image":
                                image_url
                                if image_url
                                else FOOD_IMAGES_DATABASE[
                                    idx %
                                    len(
                                        FOOD_IMAGES_DATABASE
                                    )
                                ],

                            "calories":
                                nutrition[
                                    "calories"
                                ],

                            "carbs":
                                nutrition[
                                    "carbs"
                                ],

                            "protein":
                                nutrition[
                                    "protein"
                                ],

                            "fat":
                                nutrition[
                                    "fat"
                                ],

                            "advice":
                                nutrition[
                                    "advice"
                                ],

                            "is_estimated":
                                nutrition.get(
                                    "is_estimated",
                                    True
                                )
                        })


                if results:

                    print(
                        "Returning CSV result."
                    )

                    return jsonify({

                        "foods":
                            results
                    })


    # =====================================================
    # 2. SPOONACULAR FALLBACK
    # =====================================================

    if SPOONACULAR_API_KEY:

        print(
            "Searching Spoonacular..."
        )


        try:

            # -------------------------------------------------
            # Translate Arabic → English
            # -------------------------------------------------

            try:

                translated_query = (
                    GoogleTranslator(
                        source="auto",
                        target="en"
                    ).translate(query)
                )

            except Exception:

                translated_query = query


            print(
                "Spoonacular query:",
                translated_query
            )


            params = {

                "apiKey":
                    SPOONACULAR_API_KEY,

                "query":
                    translated_query,

                "number":
                    6,

                "addRecipeNutrition":
                    "true",

                "addRecipeInformation":
                    "true"
            }


            response = requests.get(

                SPOONACULAR_SEARCH_URL,

                params=params,

                timeout=10
            )


            print(
                "Spoonacular status:",
                response.status_code
            )


            if response.status_code == 200:

                data = response.json().get(
                    "results",
                    []
                )


                formatted_foods = []


                for item in data:

                    title = item.get(
                        "title",
                        ""
                    )


                    servings = item.get(
                        "servings",
                        1
                    )


                    if not servings or servings <= 0:

                        servings = 1


                    nutrients_list = (

                        item
                        .get(
                            "nutrition",
                            {}
                        )
                        .get(
                            "nutrients",
                            []
                        )
                    )


                    nutrients = {

                        n["name"]:
                            n["amount"]

                        for n in nutrients_list

                        if "name" in n
                        and "amount" in n
                    }


                    calories = round(

                        nutrients.get(
                            "Calories",
                            0
                        )
                        / servings
                    )


                    carbs = round(

                        nutrients.get(
                            "Carbohydrates",
                            0
                        )
                        / servings,

                        1
                    )


                    protein = round(

                        nutrients.get(
                            "Protein",
                            0
                        )
                        / servings,

                        1
                    )


                    fat = round(

                        nutrients.get(
                            "Fat",
                            0
                        )
                        / servings,

                        1
                    )


                    fiber = round(

                        nutrients.get(
                            "Fiber",
                            0
                        )
                        / servings,

                        1
                    )


                    net_carbs = max(

                        0,

                        carbs - fiber
                    )


                    advice = (

                        generate_diabetes_advice_from_nutrition(

                            title,

                            net_carbs,

                            calories,

                            fat,

                            fiber
                        )
                    )


                    formatted_foods.append({

                        "description":
                            title,

                        "image":
                            item.get(
                                "image"
                            ),

                        "calories":
                            calories,

                        "carbs":
                            carbs,

                        "protein":
                            protein,

                        "fat":
                            fat,

                        "advice":
                            advice,

                        "is_estimated":
                            False
                    })


                return jsonify({

                    "foods":
                        formatted_foods
                })


        except Exception as e:

            print(
                "Spoonacular Error:",
                repr(e)
            )


    # =====================================================
    # NO RESULTS
    # =====================================================

    print(
        "No food results found."
    )


    return jsonify({

        "foods": []

    })


# =========================================================
# RUN SERVER
# =========================================================

if __name__ == "__main__":

    app.run(

        host="127.0.0.1",

        port=5000,

        debug=True
    )