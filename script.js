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