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

// 2. دالة تسجيل حساب جديد (Sign Up) -> توجيه إلى index.html
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
            // التوجيه المباشر إلى صفحة index.html
            window.location.href = '/index.html';
        } else {
            alert(result.message || "حدث خطأ أثناء إنشاء الحساب!");
        }
    } catch (err) {
        console.error("Register Error:", err);
        alert("تعذر الاتصال بالسيرفر! تأكد من أن Flask يعمل.");
    }
}

// 3. دالة تسجيل الدخول (Sign In) -> توجيه إلى index.html
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
            // التوجيه المباشر إلى صفحة index.html
            window.location.href = '/index.html';
        } else {
            alert(result.message || "بيانات الدخول غير صحيحة!");
        }
    } catch (err) {
        console.error("Login Error:", err);
        alert("تعذر الاتصال بالسيرفر!");
    }
}