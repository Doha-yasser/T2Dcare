-- 1. جدول المستخدمين (Sign In / Sign Up)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    age INTEGER,
    password_hash TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. جدول البيانات الأساسية للمريض (Onboarding Data)
CREATE TABLE IF NOT EXISTS patient_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    age INTEGER NOT NULL,
    gender TEXT,
    weight REAL NOT NULL,
    height REAL NOT NULL,
    bmi REAL NOT NULL,
    hba1c REAL NOT NULL,
    medication_type TEXT NOT NULL,
    medications TEXT NOT NULL,
    activity_level TEXT,
    target_guideline TEXT,
    hypo_unawareness INTEGER DEFAULT 0,
    image_path TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 3. جدول قراءات السكر اليومية
CREATE TABLE IF NOT EXISTS glucose_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    reading_value INTEGER NOT NULL,
    reading_type TEXT CHECK(reading_type IN ('Fasting', 'Post-Meal', 'Random', 'Bedtime')),
    logged_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 4. جدول الوجبات والكربوهيدرات
CREATE TABLE IF NOT EXISTS meal_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    meal_name TEXT NOT NULL,
    carbs_grams REAL DEFAULT 0,
    logged_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 5. جدول جرعات الدواء المأخوذة (لحساب Medication Adherence الحقيقي)
CREATE TABLE IF NOT EXISTS medication_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    taken_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 6. جدول الأطعمة المصرية (Nutrition Explorer)
CREATE TABLE IF NOT EXISTS foods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    food_name_en TEXT NOT NULL,
    food_name_ar TEXT,
    category TEXT,
    ingredients_en TEXT,
    calories_per_100g REAL DEFAULT 0,
    carbs_per_100g REAL DEFAULT 0,
    protein_per_100g REAL DEFAULT 0,
    fats_per_100g REAL DEFAULT 0,
    image_url TEXT
);