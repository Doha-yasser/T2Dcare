import os
import sqlite3
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder="../", template_folder="../")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

# إعداد مجلد حفظ الصور المرفوعة
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. جدول المستخدمين
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # 2. جدول المرضى
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            name TEXT,
            age INTEGER,
            gender TEXT,
            weight REAL,
            height REAL,
            hba1c REAL,
            medication_type TEXT,
            medications TEXT,
            hypo_unawareness INTEGER DEFAULT 0,
            activity_level TEXT,
            target_guideline TEXT,
            image_path TEXT,
            reading_fasting REAL,
            reading_postmeal REAL,
            reading_bedtime REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """
    )

    # إضافة الأعمدة الجديدة في حال كانت قاعدة البيانات قديمة
    new_columns = [
        ("gender", "TEXT"),
        ("hypo_unawareness", "INTEGER DEFAULT 0"),
        ("activity_level", "TEXT"),
        ("target_guideline", "TEXT"),
        ("image_path", "TEXT"),
    ]

    for col_name, col_type in new_columns:
        try:
            cursor.execute(f"ALTER TABLE patients ADD COLUMN {col_name} {col_type};")
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()


init_db()


# --- Routes لتقديم الصفحات والملفات الثابتة ---
@app.route("/")
def home():
    return send_from_directory("../", "signin.html")


@app.route("/uploads/<path:filename>")
def serve_uploads(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory("../", path)


# --- API Endpoints ---

# --- 1. APIs الأطعمة والنظام الغذائي (محدثة بمجموعات الـ Dataset) ---
@app.route("/api/foods", methods=["GET"])
def get_foods():
    try:
        search_query = request.args.get("search", "").strip().lower()
        category = request.args.get("category", "").strip().lower()

        # بيانات الأطعمة المتوافقة مع أقسام الـ Dataset
        sample_foods = [
            {
                "id": 1,
                "name": "Complete Green Salad Plate",
                "category": "Salads",
                "calories": 85,
                "carbs": 8,
                "sugar": 3,
                "protein": 2,
                "fat": 5,
                "image": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=600&q=80",
                "ingredients": ["Cucumber", "Tomatoes", "Lettuce", "Olive Oil", "Lemon"]
            },
            {
                "id": 2,
                "name": "Avocado Lemon Smoothie with Chia Seeds",
                "category": "Beverages",
                "calories": 160,
                "carbs": 6,
                "sugar": 1,
                "protein": 2,
                "fat": 14,
                "image": "https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=600&q=80",
                "ingredients": ["Avocado", "Water", "Lemon Juice", "Chia Seeds"]
            },
            {
                "id": 3,
                "name": "Grilled Chicken Breast with Brown Rice",
                "category": "Main Dishes",
                "calories": 280,
                "carbs": 22,
                "sugar": 1,
                "protein": 32,
                "fat": 6,
                "image": "https://images.unsplash.com/photo-1532550907401-a500c9a57435?auto=format&fit=crop&w=600&q=80",
                "ingredients": ["Chicken Breast", "Brown Rice", "Olive Oil", "Cucumber"]
            },
            {
                "id": 4,
                "name": "Greek Yogurt with Natural Honey & Cinnamon",
                "category": "Desserts",
                "calories": 150,
                "carbs": 12,
                "sugar": 8,
                "protein": 15,
                "fat": 4,
                "image": "https://images.unsplash.com/photo-1488477181946-6428a0291777?auto=format&fit=crop&w=600&q=80",
                "ingredients": ["Greek Yogurt", "Natural Honey", "Cinnamon", "Nuts"]
            },
            {"id": 5, "name": "Apple", "category": "Fruits", "calories": 52, "carbs": 14, "sugar": 10, "protein": 0.3, "fat": 0.2, "ingredients": ["Apple"]},
            {"id": 6, "name": "Oats Meal", "category": "Grains", "calories": 389, "carbs": 66, "sugar": 1, "protein": 16.9, "fat": 6.9, "ingredients": ["Oats", "Water"]},
            {"id": 7, "name": "Boiled Egg", "category": "Protein", "calories": 155, "carbs": 1.1, "sugar": 1.1, "protein": 13, "fat": 11, "ingredients": ["Egg"]},
            {"id": 8, "name": "Fresh Spinach Salad", "category": "Vegetables", "calories": 23, "carbs": 3.6, "sugar": 0.4, "protein": 2.9, "fat": 0.4, "ingredients": ["Spinach"]}
        ]

        filtered_foods = sample_foods

        # التصفية حسب القسم
        if category and category != "all":
            filtered_foods = [f for f in filtered_foods if f["category"].lower() == category]

        # التصفية حسب كلمة البحث
        if search_query:
            filtered_foods = [f for f in filtered_foods if search_query in f["name"].lower()]

        return jsonify({"status": "success", "foods": filtered_foods}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/foods/categories", methods=["GET"])
def get_food_categories():
    # الأقسام الشاملة للـ Dataset (وجبات جاهزة + مكونات أساسية)
    categories = [
        "Salads",
        "Main Dishes",
        "Beverages",
        "Desserts",
        "Fruits",
        "Grains",
        "Protein",
        "Dairy",
        "Vegetables",
        "Nuts",
        "Snacks"
    ]
    return jsonify({"status": "success", "categories": categories}), 200


# --- 2. APIs الحسابات والمرضى ---
@app.route("/api/register", methods=["POST"])
def register():
    try:
        data = request.get_json() or {}
        email = data.get("email", "").strip().lower()
        password = data.get("password", "").strip()

        if not email or not password:
            return jsonify({"status": "error", "message": "يرجى إدخال البريد الإلكتروني وكلمة السر"}), 400

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()

            return jsonify({
                "status": "success",
                "message": "تم إنشاء الحساب بنجاح",
                "user_id": user_id,
                "redirect": "/setup.html",
            }), 201

        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({"status": "error", "message": "هذا البريد الإلكتروني مُسجل بالفعل!"}), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/login", methods=["POST"])
def login():
    try:
        data = request.get_json() or {}
        email = data.get("email", "").strip().lower()
        password = data.get("password", "").strip()

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        user = cursor.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if not user:
            conn.close()
            return jsonify({
                "status": "error",
                "code": "USER_NOT_FOUND",
                "message": "هذا الحساب غير موجود! يرجى إنشاء حساب جديد.",
            }), 404

        if user["password"] != password:
            conn.close()
            return jsonify({
                "status": "error",
                "code": "WRONG_PASSWORD",
                "message": "كلمة السر غير صحيحة! يرجى التأكد وإعادة المحاولة.",
            }), 401

        user_id = user["id"]
        patient = cursor.execute("SELECT * FROM patients WHERE user_id = ?", (user_id,)).fetchone()
        conn.close()

        return jsonify({
            "status": "success",
            "message": "تم تسجيل الدخول بنجاح",
            "user_id": user_id,
            "patient_id": patient["id"] if patient else None,
            "has_setup": True if patient else False,
            "redirect": "/dashboard.html" if patient else "/setup.html",
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/user/status/<int:user_id>", methods=["GET"])
def check_user_status(user_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        patient = cursor.execute("SELECT id FROM patients WHERE user_id = ?", (user_id,)).fetchone()
        conn.close()

        if patient:
            return jsonify({"has_setup": True, "redirect": "/dashboard.html"})
        else:
            return jsonify({"has_setup": False, "redirect": "/setup.html"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/patient/setup", methods=["POST"])
def save_patient_setup():
    try:
        data = request.get_json() or {}
        user_id = data.get("user_id")

        if not user_id:
            return jsonify({"status": "error", "message": "User ID is required"}), 400

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO patients 
            (user_id, name, age, gender, weight, height, hba1c, medication_type, medications, reading_fasting, reading_postmeal, reading_bedtime)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                user_id,
                data.get("fullName"),
                data.get("age"),
                data.get("gender"),
                data.get("weight"),
                data.get("height"),
                data.get("hba1c"),
                data.get("medicationType"),
                data.get("medications"),
                data.get("reading1"),
                data.get("reading2"),
                data.get("reading3"),
            ),
        )

        conn.commit()
        conn.close()

        return jsonify({
            "status": "success",
            "message": "تم حفظ البيانات بنجاح",
            "redirect": "/dashboard.html",
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/patient/profile/<int:user_id>", methods=["GET"])
def get_patient_profile(user_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        patient = cursor.execute("SELECT * FROM patients WHERE user_id = ?", (user_id,)).fetchone()
        conn.close()

        if not patient:
            return jsonify({"status": "error", "message": "Patient profile not found"}), 404

        p = dict(patient)
        response_data = {
            "fullName": p.get("name"),
            "name": p.get("name"),
            "age": p.get("age"),
            "gender": p.get("gender"),
            "weight": p.get("weight"),
            "height": p.get("height"),
            "hba1c": p.get("hba1c"),
            "medicationType": p.get("medication_type"),
            "medications": p.get("medications"),
            "hypo_unawareness": p.get("hypo_unawareness"),
            "activity_level": p.get("activity_level"),
            "target_guideline": p.get("target_guideline"),
            "image_path": p.get("image_path"),
            "reading_fasting": p.get("reading_fasting"),
            "reading_postmeal": p.get("reading_postmeal"),
            "reading_bedtime": p.get("reading_bedtime"),
        }

        return jsonify({"status": "success", "profile": response_data}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/patient/settings/<int:user_id>", methods=["GET"])
def get_patient_settings(user_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        patient = cursor.execute("SELECT * FROM patients WHERE user_id = ?", (user_id,)).fetchone()
        conn.close()

        if not patient:
            return jsonify({"status": "error", "message": "Settings not found"}), 404

        return jsonify({"status": "success", "patient": dict(patient)}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/patient/update", methods=["POST"])
def update_patient_data():
    try:
        user_id = request.form.get("user_id")
        if not user_id:
            return jsonify({"status": "error", "message": "User ID is required"}), 400

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        current_patient = cursor.execute("SELECT image_path FROM patients WHERE user_id = ?", (user_id,)).fetchone()
        image_path = current_patient[0] if current_patient else None

        if "profileImage" in request.files:
            file = request.files["profileImage"]
            if file and allowed_file(file.filename):
                filename = secure_filename(f"user_{user_id}_{file.filename}")
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                image_path = f"/uploads/{filename}"

        hypo_unawareness = 1 if request.form.get("hypoUnawareness") in ["1", "true", "on"] else 0

        cursor.execute(
            """
            UPDATE patients SET
                name = ?,
                age = ?,
                gender = ?,
                weight = ?,
                height = ?,
                hba1c = ?,
                medication_type = ?,
                medications = ?,
                hypo_unawareness = ?,
                activity_level = ?,
                target_guideline = ?,
                image_path = COALESCE(?, image_path)
            WHERE user_id = ?
        """,
            (
                request.form.get("fullName"),
                request.form.get("age"),
                request.form.get("gender"),
                request.form.get("weight"),
                request.form.get("height"),
                request.form.get("hba1c"),
                request.form.get("medicationType"),
                request.form.get("medications"),
                hypo_unawareness,
                request.form.get("activityLevel"),
                request.form.get("targetGuideline"),
                image_path,
                user_id,
            ),
        )

        conn.commit()
        conn.close()

        return jsonify({"status": "success", "message": "تم تحديث البيانات بنجاح"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)