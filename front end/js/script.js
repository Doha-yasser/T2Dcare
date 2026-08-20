/* =========================================================
   THEME TOGGLE (dark / light mode) - runs on every page
   that includes this script and has a #themeToggle button.
   ========================================================= */
document.addEventListener("DOMContentLoaded", () => {
    const toggleBtn = document.getElementById('themeToggle');
    if (toggleBtn) {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        toggleBtn.setAttribute('aria-checked', isDark ? 'true' : 'false');

        toggleBtn.addEventListener('click', () => {
            const nowDark = document.documentElement.getAttribute('data-theme') === 'dark';
            if (nowDark) {
                document.documentElement.removeAttribute('data-theme');
 // 1. التبديل بين تبويبات التسجيل ودخول الحساب
function switchAuthTab(tab) {
    const regForm = document.getElementById('registerForm');
    const loginForm = document.getElementById('loginForm');
    const tabRegister = document.getElementById('tabRegister');
    const tabLogin = document.getElementById('tabLogin');

    if (tab === 'register') {
        regForm.style.display = 'block';
        loginForm.style.display = 'none';
        tabRegister.classList.add('active');
        tabLogin.classList.remove('active');
    } else {
        regForm.style.display = 'none';
        loginForm.style.display = 'block';
        tabLogin.classList.add('active');
        tabRegister.classList.remove('active');
    }
}

// 2. دالة تسجيل حساب جديد (Sign Up) -> توجيه إلى setup.html
// New user has no medical profile yet, so they go fill that in first.
async function handleRegister(event) {
    event.preventDefault();

    const email = document.getElementById('regEmail').value.trim();
    const password = document.getElementById('regPassword').value.trim();

    if (!email || !password) {
        alert("يرجى إدخال البريد الإلكتروني وكلمة السر");
        return;
    }

    try {
        const response = await fetch('/api/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const result = await response.json();

        if (response.ok && result.status === 'success') {
            localStorage.setItem('user_id', result.user_id);
            // مستخدم جديد -> يدخل بياناته الطبية الأول في صفحة الـ Setup
            window.location.href = 'setup.html';
        } else {
            alert(result.message || "حدث خطأ أثناء إنشاء الحساب!");
        }
    } catch (err) {
        console.error("Register Error:", err);
        alert("تعذر الاتصال بالسيرفر! تأكد من أن Flask يعمل.");
    }
}

// 3. دالة تسجيل الدخول (Sign In) -> توجيه إلى index.html (الصفحة الرئيسية)
// Returning user already has a profile, so they land on Home.
async function handleLogin(event) {
    event.preventDefault();

    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value.trim();

    if (!email || !password) {
        alert("يرجى إدخال البريد الإلكتروني وكلمة السر");
        return;
    }

    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const result = await response.json();

        if (response.ok && result.status === 'success') {
            localStorage.setItem('user_id', result.user_id);
            // تسجيل دخول ناجح -> الصفحة الرئيسية
            window.location.href = 'index.html';
        } else {
            alert(result.message || "بيانات الدخول غير صحيحة!");
        }
    } catch (err) {
        console.error("Login Error:", err);
        alert("تعذر الاتصال بالسيرفر!");
    }
}

// 4. تسجيل الخروج -> مسح بيانات المستخدم والرجوع لصفحة الدخول
function logout() {
    localStorage.removeItem('user_id');
    window.location.href = 'signin.html';
}               localStorage.setItem('t2d-theme', 'light');
                toggleBtn.setAttribute('aria-checked', 'false');
            } else {
                document.documentElement.setAttribute('data-theme', 'dark');
                localStorage.setItem('t2d-theme', 'dark');
                toggleBtn.setAttribute('aria-checked', 'true');
            }
        });
    }

    // Settings form: load data and bind submit when on settings page
    const settingsForm = document.getElementById('fullSettingsForm');
    if (settingsForm) {
        loadSettingsData();
        settingsForm.addEventListener('submit', handleSettingsUpdate);
    }
});

/* =========================================================
   9. SETTINGS PAGE (FETCH & UPDATE LOGIC)
   ========================================================= */

// 1. دالة لتعبئة بيانات الـ Setup السابقة داخل صفحة Settings عند فتحها
async function loadSettingsData() {
    const userId = localStorage.getItem('user_id');
    if (!userId) return;

    try {
        const response = await fetch(`/api/patient/settings/${userId}`);
        const data = await response.json();

        if (data.status === 'success') {
            const p = data.patient;

            // تعبئة بيانات الشخصية
            const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.value = val || ''; };

            setVal('fullName', p.name);
            setVal('age', p.age);
            setVal('gender', p.gender);
            setVal('weight', p.weight);
            setVal('height', p.height);
            setVal('hba1c', p.hba1c);

            // تعبئة الخطة العلاجية والنمط
            setVal('medicationType', p.medication_type);
            setVal('medications', p.medications);
            setVal('activityLevel', p.activity_level);
            setVal('targetGuideline', p.target_guideline);

            const hypoElem = document.getElementById('hypoUnawareness');
            if (hypoElem) hypoElem.checked = (p.hypo_unawareness == 1);

            // المعاينة المباشرة للصورة
            const previewBox = document.getElementById('previewBox');
            if (previewBox) {
                if (p.image_path) {
                    previewBox.innerHTML = `<img src="${p.image_path}" style="width:100%; height:100%; border-radius:50%; object-fit:cover;">`;
                } else if (p.name) {
                    previewBox.innerText = p.name.charAt(0).toUpperCase();
                }
            }

            // تحديث الشريط الجانبي أيضاً
            bindDatabaseDataToUI(p);
        }
    } catch (err) {
        console.error("Error fetching settings data:", err);
    }
}

// 2. دالة إرسال التحديثات وقراءة FormData بدعم رفع الصورة
async function handleSettingsUpdate(event) {
    if (event) event.preventDefault();

    const userId = localStorage.getItem('user_id');
    if (!userId) {
        alert("❌ User session not found!");
        return;
    }

    const form = document.getElementById('fullSettingsForm');
    if (!form) return;

    const formData = new FormData(form);
    formData.append('user_id', userId);

    try {
        const response = await fetch('/api/patient/update', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();

        if (response.ok && result.status === 'success') {
            alert('✅ تم تحديث بيانات الـ Setup والصورة بنجاح!');
            window.location.href = 'dashboard.html';
        } else {
            alert(`⚠️ Error: ${result.message}`);
        }
    } catch (err) {
        console.error("Update failed:", err);
        alert('❌ Failed to connect to server.');
    }
}

/* =========================================================
   10. SETUP PAGE (FIRST-TIME PATIENT PROFILE SUBMISSION)
   ========================================================= */
async function savePatientProfile(event) {
    // لازم يبقى أول سطر، عشان أي خطأ بعد كده ميرجعش الفورم لسلوكه الافتراضي (Refresh)
    if (event) event.preventDefault();

    const userId = localStorage.getItem('user_id');
    if (!userId) {
        alert("❌ لم يتم العثور على جلسة المستخدم. الرجاء تسجيل الدخول أولاً.");
        window.location.href = 'signin.html';
        return;
    }

    const getVal = (id) => {
        const el = document.getElementById(id);
        return el ? el.value : '';
    };

    const formData = new FormData();
    formData.append('user_id', userId);
    formData.append('fullName', getVal('fullName'));
    formData.append('age', getVal('age'));
    formData.append('weight', getVal('weight'));
    formData.append('height', getVal('height'));
    formData.append('hba1c', getVal('hba1c'));
    formData.append('medicationType', getVal('medicationType'));
    formData.append('medications', getVal('medications'));
    formData.append('reading1', getVal('reading1'));
    formData.append('reading2', getVal('reading2'));
    formData.append('reading3', getVal('reading3'));

    const submitBtn = document.querySelector('#patientSetupForm .btn-submit');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'جاري الحفظ...';
    }

    try {
        const response = await fetch('/api/patient/update', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();

        if (response.ok && result.status === 'success') {
            window.location.href = 'dashboard.html';
        } else {
            alert(`⚠️ Error: ${result.message || 'حدث خطأ غير متوقع'}`);
        }
    } catch (err) {
        console.error("Setup save failed:", err);
        alert('❌ فشل الاتصال بالسيرفر. تأكد إن الـ backend شغال على بورت 5000.');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Generate My Dashboard 📊 →';
        }
    }
}

// معاينة الصورة عند اختيارها فوراً
function previewSelectedImage() {
    const fileElem = document.getElementById('profileImage');
    const previewBox = document.getElementById('previewBox');

    if (fileElem && fileElem.files[0] && previewBox) {
        const reader = new FileReader();
        reader.onload = function (e) {
            previewBox.innerHTML = `<img src="${e.target.result}" style="width:100%; height:100%; border-radius:50%; object-fit:cover;">`;
        };
        reader.readAsDataURL(fileElem.files[0]);
    }
}
function handleGetStarted(e) {
    if (e) e.preventDefault(); // منع الريفرش تماماً

    const userId = localStorage.getItem('user_id');

    if (!userId) {
        window.location.href = 'signin.html';
    } else {
        window.location.href = 'dashboard.html';
    }
}