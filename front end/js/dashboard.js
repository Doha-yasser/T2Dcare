let predictionChartInstance = null;
let tirChartInstance = null;
let medRingChartInstance = null;
let totalCarbsToday = 0;

document.addEventListener("DOMContentLoaded", () => {
    // 1. قراءة بيانات الداشبورد
    loadPatientDashboardData();
    loadGlucoseStats(); // Time In Range الحقيقي بدل الأرقام الثابتة
    loadMedicationAdherence(); // Medication Adherence الحقيقي بدل initMedRingChart(80)

    // 2. تهيئة المخططات البيانية بالألوان الجديدة
    initPredictionChart([110, 115, 120, 118, 115, 112, 110]);
});

// جلب نسبة الالتزام بالدواء الحقيقية (جرعات مسجلة النهارده / المتوقع) وعرضها في الحلقة
async function loadMedicationAdherence() {
    const userId = localStorage.getItem('user_id');
    if (!userId) {
        initMedRingChart(0);
        return;
    }

    try {
        const response = await fetch(`/api/patient/medication/adherence/${userId}`);
        const data = await response.json();

        if (data.status === 'success') {
            if (!data.applicable) {
                // مريض Diet & Exercise Only — مفيش جرعات نتابعها
                initMedRingChart(0);
                setElementText('dispDosesTaken', 'Diet & Exercise Only — no doses to track');
            } else {
                initMedRingChart(data.adherence_pct);
                setElementText('dispDosesTaken', `${data.taken} / ${data.expected} doses logged today`);
            }
        } else {
            initMedRingChart(0);
        }
    } catch (err) {
        console.error("Failed to load medication adherence:", err);
        initMedRingChart(0);
    }
}

// استدعاء عند الضغط على زرار "Log Dose Taken"
async function logMedicationDose() {
    const userId = localStorage.getItem('user_id');
    if (!userId) {
        alert("❌ Please sign in first.");
        return;
    }

    const btn = document.getElementById('btnLogDose');
    if (btn) {
        btn.disabled = true;
        btn.innerText = 'جاري التسجيل...';
    }

    try {
        const response = await fetch('/api/patient/medication/log', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId })
        });
        const result = await response.json();

        if (response.ok && result.status === 'success') {
            loadMedicationAdherence(); // تحديث الحلقة والنص فورًا
        } else {
            alert(`⚠️ ${result.message || 'فشل تسجيل الجرعة.'}`);
        }
    } catch (err) {
        console.error("Log dose failed:", err);
        alert('❌ تعذر الاتصال بالسيرفر.');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerText = 'Log Dose Taken ✅';
        }
    }
}

// جلب نسب Time In Range الحقيقية من glucose_logs وعرضها في الـ TIR chart
async function loadGlucoseStats() {
    const userId = localStorage.getItem('user_id');
    if (!userId) {
        initTIRChart(0, 0, 0);
        return;
    }

    try {
        const response = await fetch(`/api/patient/glucose-stats/${userId}`);
        const data = await response.json();

        if (data.status === 'success' && data.has_data) {
            initTIRChart(data.in_range_pct, data.high_pct, data.low_pct);
        } else {
            // مفيش قراءات جلوكوز مسجلة لسه لهذا المريض
            initTIRChart(0, 0, 0);
        }
    } catch (err) {
        console.error("Failed to load glucose stats:", err);
        initTIRChart(0, 0, 0);
    }
}

async function loadPatientDashboardData() {
    const userId = localStorage.getItem('user_id');

    if (!userId) {
        window.location.href = 'signin.html';
        return;
    }

    try {
        const response = await fetch(`/api/patient/profile/${userId}`);
        if (!response.ok) throw new Error("API Network error");

        const result = await response.json();
        const p = result.profile || result;

        bindDatabaseDataToUI(p);
    } catch (error) {
        console.error("Failed to load patient data:", error);
    }
}

function bindDatabaseDataToUI(p) {
    const rawName = p.fullName || p.name || 'Patient';
    const cleanName = rawName.charAt(0).toUpperCase() + rawName.slice(1);

    setElementText('dispName', cleanName);
    setElementText('dispAgeGender', `Age: ${p.age || '--'} | ${p.gender || 'N/A'}`);

    // 📸 معالجة صورة الملف الشخصي أو إظهار الحرف الأول
    const avatarElem = document.getElementById('userAvatar');
    if (avatarElem) {
        if (p.image_path) {
            avatarElem.innerHTML = `<img src="${p.image_path}" alt="Profile" style="width:100%; height:100%; border-radius:50%; object-fit:cover;">`;
        } else {
            avatarElem.innerText = cleanName.charAt(0).toUpperCase();
        }
    }

    // حساب مؤشر كتلة الجسم (BMI)
    const weight = parseFloat(p.weight) || 0;
    const height = parseFloat(p.height) || 0;

    if (weight > 0 && height > 0) {
        const bmi = (weight / ((height / 100) ** 2)).toFixed(1);
        setElementText('dispBMI', bmi);
        setElementText('dispBMICat', getBMICategory(bmi));
    }

    // بيانات السكر والتراكمي
    if (p.hba1c) {
        setElementText('dispA1c', `${p.hba1c}%`);
        setElementText('dispA1cStatus', parseFloat(p.hba1c) > 7.0 ? 'Above Target' : 'Optimal Control');
        const estimatedEa1c = (parseFloat(p.hba1c) - 0.2).toFixed(1);
        setElementText('dispeA1c', `${estimatedEa1c}%`);
    }

    // الأدوية والحقول الجديدة
    const medType = p.medicationType || p.medication_type || 'Oral Meds';
    setElementText('dispRegime', medType);
    setElementText('dispMedDetails', p.medications || '--');
    setElementText('dispHypoStatus', p.hypo_unawareness ? 'Normal Sense' : 'High Risk');
    setElementText('dispActivity', p.activity_level || '--');
    setElementText('dispTargetGuideline', p.target_guideline || '--');

    const isHypoHigh = medType.toLowerCase().includes('insulin');
    const hypoElem = document.getElementById('dispHypoRisk');
    if (hypoElem) {
        hypoElem.innerText = isHypoHigh ? 'High' : 'Low';
        hypoElem.style.color = isHypoHigh ? '#c62828' : '#2e7d32'; // تم تحديث ألوان حالة الخطر للباليت الوردي والأخضر الخفيف
    }
}

function setInputValue(name, value) {
    const input = document.querySelector(`[name="${name}"]`);
    if (input && value !== null && value !== undefined) {
        input.value = value;
    }
}

// ==========================================
// 🥗 وظائف تحليل الوجبات والمخططات البيانية
// ==========================================
function setElementText(id, value) {
    const el = document.getElementById(id);
    if (el) el.innerText = value;
}

function getBMICategory(bmi) {
    if (bmi < 18.5) return 'Underweight';
    if (bmi < 25) return 'Normal weight';
    if (bmi < 30) return 'Overweight';
    return 'Obesity';
}

async function analyzeMeal() {
    const mealInput = document.getElementById('mealInput');
    if (!mealInput) return;

    const mealText = mealInput.value.trim();
    if (!mealText) return alert("Please type your meal description!");

    const btn = document.getElementById('btnAnalyze');
    if (btn) {
        btn.innerText = "Analyzing...";
        btn.disabled = true;
    }

    try {
        const response = await fetch('/api/nutrition/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ meal: mealText })
        });
        const data = await response.json();
        renderMealAnalysis(data.carbs || 45, data.fiber || 5, data.calories || 400, data.protein || 20, mealText);
    } catch (err) {
        renderMealAnalysis(52, 4, 450, 22, mealText);
    } finally {
        if (btn) {
            btn.innerText = "Analyze Meal 🥗";
            btn.disabled = false;
        }
    }
}

function renderMealAnalysis(carbs, fiber, calories, protein, mealText) {
    const resultsElem = document.getElementById('nutritionResults');
    if (resultsElem) resultsElem.style.display = 'flex';

    setElementText('nutCarbs', `${carbs}g`);
    setElementText('nutFiber', `${fiber}g`);
    setElementText('nutCalories', `${calories} kcal`);
    setElementText('nutProtein', `${protein}g`);

    totalCarbsToday += carbs;
    const carbLimit = 150;
    const carbPercentage = Math.min(100, (totalCarbsToday / carbLimit) * 100);
    setElementText('carbLimitText', `${totalCarbsToday}g / ${carbLimit}g`);

    const pBar = document.getElementById('carbProgressBar');
    if (pBar) {
        pBar.style.width = `${carbPercentage}%`;
        // تغيير لون الشريط ليتوافق مع الباليت (#0d6e6e للوضع الطبيعي و #c62828 للتجاوز)
        pBar.style.background = totalCarbsToday > carbLimit ? '#c62828' : '#0d6e6e';
    }

    updatePredictionCurve(carbs);
    generateAISmartInsight(mealText, carbs);
}

// 1. Prediction Line Chart (تم التحديث للألوان النعناعية والـ Teal)
function initPredictionChart(dataPoints) {
    const chartElem = document.getElementById('predictionChart');
    if (!chartElem) return;

    const ctx = chartElem.getContext('2d');

    predictionChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Now', '+1h Peak', '+2h', '+4h', '+8h', '+12h', '+24h'],
            datasets: [{
                label: 'Predicted Glucose (mg/dL)',
                data: dataPoints,
                borderColor: '#0d6e6e',                 // Teal الأساسي
                borderWidth: 3,
                backgroundColor: 'rgba(13, 110, 110, 0.1)', // خلفية شفافة باليت Teal
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#0d6e6e'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { min: 60, max: 240, grid: { color: '#d8eae7' } },
                x: { grid: { display: false } }
            }
        }
    });
}

// 2. Time In Range (TIR) Stacked Bar Chart
// 2. Time In Range (TIR) Stacked Bar Chart
function initTIRChart(inRange, high, low) {
    const chartElem = document.getElementById('tirChart');
    if (!chartElem) return;

    // إلغاء الرسم القديم إذا كان موجوداً لمنع تداخل الألوان
    if (tirChartInstance) {
        tirChartInstance.destroy();
    }

    tirChartInstance = new Chart(chartElem, {
        type: 'bar',
        data: {
            labels: ['Last 7 Days'],
            datasets: [
                {
                    label: 'In Range (70-180)',
                    data: [inRange],
                    backgroundColor: '#0d6e6e', // Teal ناعم وهادئ
                    borderRadius: { topLeft: 8, bottomLeft: 8 }
                },
                {
                    label: 'High (>180)',
                    data: [high],
                    backgroundColor: '#f59e0b' // أصفر باستيل دافئ
                },
                {
                    label: 'Low (<70)',
                    data: [low],
                    backgroundColor: '#ef4444', // أحمر ناعم
                    borderRadius: { topRight: 8, bottomRight: 8 }
                }
            ]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    stacked: true,
                    max: 100,
                    grid: { color: '#eef7f6' }
                },
                y: {
                    stacked: true,
                    display: false
                }
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        boxWidth: 12,
                        padding: 15,
                        font: { size: 11, family: 'Segoe UI' },
                        color: '#375253'
                    }
                }
            }
        }
    });
}

// 3. Medication Progress Ring (تم التحديث للون #0d6e6e والـ Mint)
function initMedRingChart(percentage) {
    const chartElem = document.getElementById('medRingChart');
    if (!chartElem) return;

    // بيتنادى تاني بعد كل "Log Dose Taken"، فلازم نلغي الرسم القديم الأول
    if (medRingChartInstance) {
        medRingChartInstance.destroy();
    }

    medRingChartInstance = new Chart(chartElem, {
        type: 'doughnut',
        data: {
            labels: ['Taken', 'Pending'],
            datasets: [{
                data: [percentage, 100 - percentage],
                backgroundColor: ['#0d6e6e', '#e2f2ef'], // Teal غامق مع Mint فاتح
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '75%',
            plugins: { legend: { display: false } }
        }
    });
}

function updatePredictionCurve(carbs) {
    if (!predictionChartInstance) return;
    const peakSpike = Math.min(230, 110 + (carbs * 1.6));
    predictionChartInstance.data.datasets[0].data = [110, peakSpike, peakSpike - 25, 132, 118, 112, 110];
    predictionChartInstance.update();
}

function generateAISmartInsight(meal, carbs) {
    const adviceBox = document.getElementById('llmAdviceBox');
    if (!adviceBox) return;

    if (carbs > 50) {
        adviceBox.innerHTML = `<p>⚠️ <strong>High Carb Load Detected (${carbs}g Carbs):</strong> Predicted glucose spike ~<strong>${Math.round(110 + carbs * 1.6)} mg/dL</strong> at 1h. Consider a 15-min walk.</p>`;
    } else {
        adviceBox.innerHTML = `<p>✅ <strong>Glycemically Balanced Meal (${carbs}g Carbs):</strong> Glucose trajectory within target safety range (70-180 mg/dL).</p>`;
    }
}

function logout() {
    localStorage.clear();
    window.location.href = 'signin.html';
}