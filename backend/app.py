import os
import sqlite3
from pathlib import Path
from deep_translator import GoogleTranslator
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import pandas as pd
import requests

# =========================
# LOAD ENVIRONMENT VARIABLES
# =========================

BASE_DIR = Path(__file__).resolve().parent


def find_frontend_dir():
    """The front-end HTML lives in a sibling folder next to backend/, but its
    exact name varies (front end / frontend / front-end). Auto-detect it by
    looking for a folder that actually contains an 'html' subfolder, instead
    of hardcoding one spelling."""
    parent = BASE_DIR.parent
    candidates = [
        parent / "front end",
        parent / "frontend",
        parent / "front-end",
        parent,
    ]
    for c in candidates:
        if (c / "html").is_dir():
            return c
    return parent  # fallback: at least won't crash on import


ROOT_DIR = find_frontend_dir()
env_path = BASE_DIR.parent / ".env"
load_dotenv(dotenv_path=env_path)


# =========================
# FLASK APP
# =========================

app = Flask(__name__, static_folder=str(ROOT_DIR), template_folder=str(ROOT_DIR), static_url_path="")


# =========================
# DATABASE CONFIG
# =========================

DB_PATH = BASE_DIR / "database.db"
SCHEMA_PATH = BASE_DIR / "database.sql"
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def get_db():
    """Return a sqlite3 connection with dict-like row access."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables from database.sql (idempotent: uses CREATE TABLE IF NOT
    EXISTS so it's safe to run every time, even against an existing DB that
    only has some of the tables, e.g. an old 'patients' table but no
    'patient_profiles' yet), then patch in any columns added later to the
    schema (safe no-op if they're already there)."""
    conn = get_db()

    if SCHEMA_PATH.exists():
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()

    tables = {row["name"] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    print(f"Database ready at {DB_PATH} — tables: {sorted(tables)}")

    # Safety net: patch an older 'users' table that may be missing columns
    # our auth routes need (e.g. it only had 'password' instead of
    # 'password_hash', or no 'created_at').
    users_extra_columns = {
        "password_hash": "TEXT",
        "created_at": "DATETIME",  # no DEFAULT here: SQLite's ALTER TABLE
                                     # rejects non-constant defaults like
                                     # CURRENT_TIMESTAMP on an existing table
        "age": "INTEGER",
    }
    if "users" in tables:
        existing_user_cols = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
        for col, col_type in users_extra_columns.items():
            if col not in existing_user_cols:
                try:
                    conn.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
                    conn.commit()
                    print(f"Added missing column '{col}' to users")
                except sqlite3.OperationalError as e:
                    print(f"Could not add column '{col}' to users:", e)

    # Safety net: patch older DBs that were created before these columns existed.
    extra_columns = {
        "gender": "TEXT",
        "activity_level": "TEXT",
        "target_guideline": "TEXT",
        "hypo_unawareness": "INTEGER DEFAULT 0",
        "image_path": "TEXT",
    }
    existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(patient_profiles)")}
    for col, col_type in extra_columns.items():
        if col not in existing_cols:
            try:
                conn.execute(f"ALTER TABLE patient_profiles ADD COLUMN {col} {col_type}")
                conn.commit()
                print(f"Added missing column '{col}' to patient_profiles")
            except sqlite3.OperationalError as e:
                print(f"Could not add column '{col}':", e)

    conn.close()


def allowed_image(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def get_expected_daily_doses(medication_type):
    """Rough default doses/day per treatment type, used to compute Medication
    Adherence %. There's no per-patient dosing schedule captured yet (that
    would need its own setup field), so this is a reasonable approximation:
    oral meds ~2x/day, insulin ~3x/day, GLP-1 injections ~1x/day (weekly
    injections simplified to a daily reminder), diet/exercise-only patients
    have nothing to track."""
    mapping = {
        "oral": 2,
        "insulin": 3,
        "glp1": 1,
        "lifestyle": 0,
    }
    return mapping.get((medication_type or "").strip().lower(), 2)


init_db()


# =========================
# APIs CONFIG
# =========================

SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY")
SPOONACULAR_SEARCH_URL = "https://api.spoonacular.com/recipes/complexSearch"
CHATBOT_URL = "http://127.0.0.1:8000"

# =========================
# LOAD EGYPTIAN CSV DATASET
# (still used by /api/nutrition/analyze below — foods search now uses the DB)
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
    """Calculates calories and macros dynamically to avoid repetition in Dataset.
    `row` can be a pandas Series (CSV path) or a plain dict (DB path) —
    both support .get()."""
    cal = float(row.get("calories_per_100g", 0) or 0)
    fat = float(row.get("fats_per_100g", 0) or 0)
    protein = float(row.get("protein_per_100g", 0) or 0)
    carbs = float(row.get("carbs_per_100g", 0) or 0)

    ingredients = str(row.get("ingredients_en", "") or "").lower()
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
    ing_lower = str(ingredients_str or "").lower()
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
IMAGES_DIR = BASE_DIR.parent / "images"


@app.route("/images/<path:filename>")
def serve_images(filename):
    """Serve images from the project-root images/ folder (not the front-end
    static folder), so signin.html's /images/sign2.jpg resolves correctly."""
    return send_from_directory(str(IMAGES_DIR), filename)


@app.route("/")
def home():
    # Redirect (instead of serving index.html directly at "/") so the browser's
    # address bar ends up under /html/. That way every page's relative nav
    # links (href="about.html", href="chat.html", ...) resolve correctly
    # against /html/, matching where the files actually live on disk.
    return redirect("/html/index.html")


@app.route("/api/categories", methods=["GET"])
@app.route("/api/foods/categories", methods=["GET"])  # alias: healthy_food.html/healthy.js calls this exact path
def get_categories():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT DISTINCT category FROM foods WHERE category IS NOT NULL AND category != ''"
        ).fetchall()
        categories = sorted(r["category"] for r in rows)
        return jsonify({"categories": categories})
    finally:
        conn.close()


# =========================
# SEARCH FOODS (NOW FROM database.db, WITH SPOONACULAR FALLBACK)
# =========================

@app.route("/api/foods", methods=["GET"])
def search_foods():
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    if not query and not category:
        return jsonify({"error": "Please enter a food name or choose a category."}), 400

    # ==========================================
    # 1. SEARCH database.db (foods table)
    # ==========================================
    conn = get_db()
    try:
        sql = "SELECT * FROM foods WHERE 1=1"
        params = []

        if category:
            sql += " AND category = ?"
            params.append(category)

        if query:
            like = f"%{query}%"
            sql += """ AND (
                food_name_en LIKE ? OR food_name_ar LIKE ? OR ingredients_en LIKE ?
            )"""
            params.extend([like, like, like])

        sql += " LIMIT 8"
        rows = conn.execute(sql, params).fetchall()

        if rows:
            results = []
            for row in rows:
                row_dict = dict(row)
                food_title = row_dict.get("food_name_en") or query
                calories, carbs, protein, fat = calculate_dynamic_nutrition(row_dict, food_title)
                advice = generate_diabetes_advice(carbs=carbs, calories=calories, fat=fat)
                substitutions = get_smart_substitutions(row_dict.get("ingredients_en", ""), food_title)

                match_type = "direct"
                ingredients_lower = (row_dict.get("ingredients_en") or "").lower()
                if query and query.lower() not in food_title.lower() and query.lower() in ingredients_lower:
                    match_type = "ingredient"

                results.append({
                    "id": row_dict["id"],
                    "description": food_title,
                    "category": row_dict.get("category", "General"),
                    "image": row_dict.get("image_url", ""),
                    "calories": round(calories),
                    "carbs": round(carbs, 1),
                    "protein": round(protein, 1),
                    "fat": round(fat, 1),
                    "match_type": match_type,
                    "ingredient_note": f"Contains '{query}' in ingredients" if match_type == "ingredient" else "",
                    "advice": advice,
                    "substitutions": substitutions,
                })

            if results:
                return jsonify({"foods": results})
    finally:
        conn.close()

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
# AUTH: REGISTER / LOGIN
# =========================

@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()
    age_raw = data.get("age")

    if not email or not password:
        return jsonify({"status": "error", "message": "Email and password are required."}), 400
    if len(password) < 6:
        return jsonify({"status": "error", "message": "Password must be at least 6 characters."}), 400

    age = None
    if age_raw not in (None, ""):
        try:
            age = int(age_raw)
            if age < 1 or age > 120:
                return jsonify({"status": "error", "message": "Please enter a valid age."}), 400
        except (TypeError, ValueError):
            return jsonify({"status": "error", "message": "Age must be a number."}), 400

    conn = get_db()
    try:
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            return jsonify({"status": "error", "message": "This email is already registered."}), 409

        password_hash = generate_password_hash(password)

        # Build the INSERT dynamically from the table's *actual* columns so
        # this works even if the users table has legacy NOT NULL columns
        # we don't know about in advance (e.g. an old 'password' column).
        cols_info = {row["name"]: row for row in conn.execute("PRAGMA table_info(users)")}

        data = {"email": email}
        if "password_hash" in cols_info:
            data["password_hash"] = password_hash
        if "password" in cols_info:
            # Legacy column — never store plaintext, reuse the hash here too.
            data["password"] = password_hash
        if age is not None and "age" in cols_info:
            data["age"] = age

        for name, info in cols_info.items():
            if name in data or name == "id":
                continue
            not_null = info["notnull"]
            has_default = info["dflt_value"] is not None
            if not_null and not has_default:
                data[name] = ""  # best-effort fallback for any other required legacy column

        columns = list(data.keys())
        placeholders = ", ".join("?" for _ in columns)
        cur = conn.execute(
            f"INSERT INTO users ({', '.join(columns)}) VALUES ({placeholders})",
            [data[c] for c in columns],
        )
        conn.commit()
        user_id = cur.lastrowid
        return jsonify({"status": "success", "user_id": user_id})
    except Exception as e:
        print("Register Error:", e)
        return jsonify({"status": "error", "message": "Server error during registration."}), 500
    finally:
        conn.close()


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()

    if not email or not password:
        return jsonify({"status": "error", "message": "Email and password are required."}), 400

    conn = get_db()
    try:
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        stored_hash = user["password_hash"] if user and "password_hash" in user.keys() else None
        if not user or not stored_hash or not check_password_hash(stored_hash, password):
            return jsonify({"status": "error", "message": "Invalid email or password."}), 401

        return jsonify({"status": "success", "user_id": user["id"]})
    except Exception as e:
        print("Login Error:", e)
        return jsonify({"status": "error", "message": "Server error during login."}), 500
    finally:
        conn.close()


# =========================
# PATIENT PROFILE / SETTINGS
# =========================

def _row_to_patient_dict(row):
    """Normalize a patient_profiles row into the field names both
    dashboard.js and script.js expect (covers both naming styles)."""
    if row is None:
        return {}
    d = dict(row)
    return {
        "name": d.get("full_name"),
        "fullName": d.get("full_name"),
        "age": d.get("age"),
        "gender": d.get("gender"),
        "weight": d.get("weight"),
        "height": d.get("height"),
        "bmi": d.get("bmi"),
        "hba1c": d.get("hba1c"),
        "medication_type": d.get("medication_type"),
        "medicationType": d.get("medication_type"),
        "medications": d.get("medications"),
        "activity_level": d.get("activity_level"),
        "target_guideline": d.get("target_guideline"),
        "hypo_unawareness": d.get("hypo_unawareness"),
        "image_path": d.get("image_path"),
    }


@app.route("/api/patient/profile/<int:user_id>", methods=["GET"])
def get_patient_profile(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM patient_profiles WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not row:
            return jsonify({"status": "error", "message": "Profile not found.", "profile": {}}), 404
        return jsonify({"status": "success", "profile": _row_to_patient_dict(row)})
    except Exception as e:
        print("Get Profile Error:", e)
        return jsonify({"status": "error", "message": "Server error."}), 500
    finally:
        conn.close()


@app.route("/api/patient/settings/<int:user_id>", methods=["GET"])
def get_patient_settings(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM patient_profiles WHERE user_id = ?", (user_id,)
        ).fetchone()
        return jsonify({"status": "success", "patient": _row_to_patient_dict(row)})
    except Exception as e:
        print("Get Settings Error:", e)
        return jsonify({"status": "error", "message": "Server error."}), 500
    finally:
        conn.close()


@app.route("/api/patient/update", methods=["POST"])
def update_patient():
    # Comes from a multipart/form-data FormData() call (supports image upload)
    form = request.form
    user_id = form.get("user_id")

    if not user_id:
        return jsonify({"status": "error", "message": "Missing user_id."}), 400

    def to_float(val, default=0.0):
        try:
            return float(val)
        except (TypeError, ValueError):
            return default

    def to_int(val, default=0):
        try:
            return int(val)
        except (TypeError, ValueError):
            return default

    def to_optional_int(val):
        """Like to_int but returns None instead of 0 when the field is
        missing/blank, so we don't insert bogus '0 mg/dL' glucose readings
        for forms that don't send reading1/2/3 (e.g. settings.html)."""
        try:
            if val is None or str(val).strip() == "":
                return None
            return int(float(val))
        except (TypeError, ValueError):
            return None

    full_name = form.get("fullName", "").strip()
    age = to_int(form.get("age"))
    gender = form.get("gender", "")
    weight = to_float(form.get("weight"))
    height = to_float(form.get("height"))
    hba1c = to_float(form.get("hba1c"))
    medication_type = form.get("medicationType", "")
    medications = form.get("medications", "")
    activity_level = form.get("activityLevel", "")
    target_guideline = form.get("targetGuideline", "")
    hypo_unawareness = 1 if form.get("hypoUnawareness") in ("on", "true", "1") else 0

    bmi = round(weight / ((height / 100) ** 2), 1) if weight > 0 and height > 0 else 0

    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT * FROM patient_profiles WHERE user_id = ?", (user_id,)
        ).fetchone()

        # Handle optional profile image upload
        image_path = existing["image_path"] if existing else None
        file = request.files.get("profileImage")
        if file and file.filename and allowed_image(file.filename):
            filename = secure_filename(f"user_{user_id}_{file.filename}")
            file.save(str(UPLOAD_FOLDER / filename))
            image_path = f"/uploads/{filename}"

        if existing:
            conn.execute(
                """UPDATE patient_profiles SET
                    full_name = ?, age = ?, gender = ?, weight = ?, height = ?, bmi = ?,
                    hba1c = ?, medication_type = ?, medications = ?, activity_level = ?,
                    target_guideline = ?, hypo_unawareness = ?, image_path = ?
                   WHERE user_id = ?""",
                (full_name or existing["full_name"], age or existing["age"], gender, weight,
                 height, bmi, hba1c, medication_type, medications, activity_level,
                 target_guideline, hypo_unawareness, image_path, user_id),
            )
        else:
            conn.execute(
                """INSERT INTO patient_profiles
                    (user_id, full_name, age, gender, weight, height, bmi, hba1c,
                     medication_type, medications, activity_level, target_guideline,
                     hypo_unawareness, image_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, full_name, age, gender, weight, height, bmi, hba1c,
                 medication_type, medications, activity_level, target_guideline,
                 hypo_unawareness, image_path),
            )

        # Save the 3 baseline glucose readings from setup.html into
        # glucose_logs, if this request included them (settings.html updates
        # won't, since it has no reading1/2/3 fields — that's fine, they're
        # simply skipped).
        glucose_readings = [
            (to_optional_int(form.get("reading1")), "Fasting"),
            (to_optional_int(form.get("reading2")), "Post-Meal"),
            (to_optional_int(form.get("reading3")), "Bedtime"),
        ]
        for value, reading_type in glucose_readings:
            if value is not None:
                conn.execute(
                    "INSERT INTO glucose_logs (user_id, reading_value, reading_type) VALUES (?, ?, ?)",
                    (user_id, value, reading_type),
                )

        conn.commit()
        return jsonify({"status": "success", "message": "Profile updated."})
    except Exception as e:
        print("Update Patient Error:", e)
        return jsonify({"status": "error", "message": "Server error while updating profile."}), 500
    finally:
        conn.close()


@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(str(UPLOAD_FOLDER), filename)


@app.route("/api/patient/medication/log", methods=["POST"])
def log_medication_dose():
    """Called by the 'Log Dose Taken' button on the dashboard. Just records
    a timestamped row — one row per dose taken."""
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"status": "error", "message": "Missing user_id."}), 400

    conn = get_db()
    try:
        conn.execute("INSERT INTO medication_logs (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        print("Log Medication Dose Error:", e)
        return jsonify({"status": "error", "message": "Server error."}), 500
    finally:
        conn.close()


@app.route("/api/patient/medication/adherence/<int:user_id>", methods=["GET"])
def get_medication_adherence(user_id):
    """Real adherence % for *today*: doses actually logged vs. expected doses
    for this patient's treatment type, replacing the hardcoded
    initMedRingChart(80) dashboard.js used to call with."""
    conn = get_db()
    try:
        profile = conn.execute(
            "SELECT medication_type FROM patient_profiles WHERE user_id = ?", (user_id,)
        ).fetchone()
        medication_type = profile["medication_type"] if profile else ""
        expected = get_expected_daily_doses(medication_type)

        taken_today = conn.execute(
            "SELECT COUNT(*) AS c FROM medication_logs "
            "WHERE user_id = ? AND date(taken_at, 'localtime') = date('now', 'localtime')",
            (user_id,),
        ).fetchone()["c"]

        if expected == 0:
            # Diet & Exercise Only — nothing to track, the ring isn't applicable.
            return jsonify({
                "status": "success", "applicable": False,
                "expected": 0, "taken": taken_today, "adherence_pct": 0,
            })

        adherence_pct = round(min(taken_today, expected) / expected * 100)
        return jsonify({
            "status": "success", "applicable": True,
            "expected": expected, "taken": taken_today, "adherence_pct": adherence_pct,
        })
    except Exception as e:
        print("Medication Adherence Error:", e)
        return jsonify({"status": "error", "message": "Server error."}), 500
    finally:
        conn.close()


@app.route("/api/patient/glucose-stats/<int:user_id>", methods=["GET"])
def get_glucose_stats(user_id):
    """Real Time-In-Range percentages computed from this patient's actual
    glucose_logs rows (last 50 readings), replacing the hardcoded
    initTIRChart(75, 20, 5) numbers dashboard.js used to call with."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT reading_value FROM glucose_logs WHERE user_id = ? "
            "ORDER BY logged_at DESC LIMIT 50",
            (user_id,),
        ).fetchall()

        total = len(rows)
        if total == 0:
            return jsonify({
                "status": "success", "has_data": False, "count": 0,
                "in_range_pct": 0, "high_pct": 0, "low_pct": 0,
            })

        in_range = sum(1 for r in rows if 70 <= r["reading_value"] <= 180)
        high = sum(1 for r in rows if r["reading_value"] > 180)
        low = sum(1 for r in rows if r["reading_value"] < 70)

        return jsonify({
            "status": "success",
            "has_data": True,
            "count": total,
            "in_range_pct": round(in_range / total * 100),
            "high_pct": round(high / total * 100),
            "low_pct": round(low / total * 100),
        })
    except Exception as e:
        print("Glucose Stats Error:", e)
        return jsonify({"status": "error", "message": "Server error."}), 500
    finally:
        conn.close()


# =========================
# NUTRITION ANALYSIS (used by dashboard "Analyze Meal")
# Still uses the CSV directly — not part of this migration.
# =========================

@app.route("/api/nutrition/analyze", methods=["POST"])
def analyze_nutrition():
    data = request.get_json(silent=True) or {}
    meal_text = (data.get("meal") or "").strip()

    if not meal_text:
        return jsonify({"status": "error", "message": "Please describe your meal."}), 400

    meal_lower = meal_text.lower()

    # 1. Try to match against the Egyptian food dataset first.
    if not egyptian_df.empty:
        en_col = "food_name_en" if "food_name_en" in egyptian_df.columns else egyptian_df.columns[0]
        ar_col = "food_name_ar" if "food_name_ar" in egyptian_df.columns else egyptian_df.columns[0]

        mask = (
            egyptian_df[en_col].astype(str).str.lower().apply(lambda n: n in meal_lower or meal_lower in n.lower()) |
            egyptian_df[ar_col].astype(str).apply(lambda n: n in meal_text)
        )
        matches = egyptian_df[mask]
        if not matches.empty:
            row = matches.iloc[0]
            title = row.get(en_col, meal_text)
            calories, carbs, protein, fat = calculate_dynamic_nutrition(row, title)
            fiber = round(carbs * 0.1, 1)  # rough estimate, dataset has no fiber column
            return jsonify({
                "status": "success",
                "source": "dataset",
                "matched_food": str(title),
                "carbs": round(carbs, 1),
                "fiber": fiber,
                "calories": round(calories),
                "protein": round(protein, 1),
            })

    # 2. Fallback: rough keyword-based estimate so the UI always gets a sensible number.
    carb_heavy = ["rice", "bread", "pasta", "potato", "sugar", "koshari", "rice with milk", "feteer"]
    protein_heavy = ["chicken", "meat", "egg", "fish", "beans", "lentil"]

    carbs = 20 + sum(15 for w in carb_heavy if w in meal_lower)
    protein = 10 + sum(8 for w in protein_heavy if w in meal_lower)
    fiber = round(carbs * 0.12, 1)
    calories = round(carbs * 4 + protein * 4 + 100)

    return jsonify({
        "status": "success",
        "source": "estimate",
        "matched_food": None,
        "carbs": carbs,
        "fiber": fiber,
        "calories": calories,
        "protein": protein,
    })


# =========================
# CHATBOT PROXY
# =========================

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    session_id = str(data.get("session_id") or "anon")

    if not message:
        return jsonify({"status": "error", "message": "Message cannot be empty."}), 400

    try:
        response = requests.post(
            f"{CHATBOT_URL}/chat",
            json={"session_id": session_id, "message": message},
            timeout=15,
        )
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        print("Chatbot proxy error:", e)
        return jsonify({"status": "error", "message": "Chatbot service is unavailable."}), 502


# =========================
# RUN APP
# =========================

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)