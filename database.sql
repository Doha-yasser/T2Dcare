-- 1. جدول المستخدمين (Sign In / Sign Up)
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. جدول البيانات الأساسية للمريض (Onboarding Data)
CREATE TABLE patient_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    age INTEGER NOT NULL,
    weight REAL NOT NULL,
    height REAL NOT NULL,
    bmi REAL NOT NULL,
    hba1c REAL NOT NULL,
    medication_type TEXT NOT NULL,
    medications TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 3. جدول قراءات السكر اليومية
CREATE TABLE glucose_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    reading_value INTEGER NOT NULL,
    reading_type TEXT CHECK(reading_type IN ('Fasting', 'Post-Meal', 'Random', 'Bedtime')),
    logged_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 4. جدول الوجبات والكربوهيدرات
CREATE TABLE meal_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    meal_name TEXT NOT NULL,
    carbs_grams REAL DEFAULT 0,
    logged_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);