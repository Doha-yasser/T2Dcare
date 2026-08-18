/* =========================================================
   TYPE 2 DIABETES - MAIN SCRIPT (ENGLISH INTEGRATED VERSION)
   ========================================================= */

document.addEventListener("DOMContentLoaded", () => {
    initHeroSlider();
    initFoodExplorer();
});

/* =========================================================
   1. HERO SLIDER
   ========================================================= */
function initHeroSlider() {
    const slides = document.querySelectorAll(".t2d-hero-slide");
    if (!slides || slides.length <= 1) return;

    let currentIndex = 0;
    const slideInterval = 5000; // Change slide every 5 seconds

    setInterval(() => {
        slides[currentIndex].classList.remove("active");
        currentIndex = (currentIndex + 1) % slides.length;
        slides[currentIndex].classList.add("active");
    }, slideInterval);
}

/* =========================================================
   2. FOOD EXPLORER & SEARCH
   ========================================================= */
function initFoodExplorer() {
    const searchInput = document.getElementById("foodInput") || document.getElementById("foodSearchInput");
    const categorySelect = document.getElementById("categorySelect");
    const resultsContainer = document.getElementById("foodResults");

    // Load categories dynamically from Flask backend on start
    loadCategories();

    if (!resultsContainer) return;

    // Load default meals on initial page load
    loadDefaultMeals(resultsContainer);
}

// Fetch categories from Flask Backend
async function loadCategories() {
    try {
        const response = await fetch('/api/categories');
        const data = await response.json();

        const categorySelect = document.getElementById('categorySelect');
        if (categorySelect && data.categories) {
            categorySelect.innerHTML = '<option value="">All Categories</option>';

            data.categories.forEach(cat => {
                const option = document.createElement('option');
                option.value = cat;
                option.textContent = cat;
                categorySelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error("Error loading categories:", error);
    }
}

// Perform search action triggered by button or Enter key
function searchFood() {
    const searchInput = document.getElementById("foodInput") || document.getElementById("foodSearchInput");
    const categorySelect = document.getElementById("categorySelect");
    const resultsContainer = document.getElementById("foodResults");

    const query = searchInput ? searchInput.value.trim() : "";
    const category = categorySelect ? categorySelect.value : "";

    if (!query && !category) {
        loadDefaultMeals(resultsContainer);
        return;
    }

    fetchFoodData(query, category, resultsContainer);
}

function handleFoodKey(event) {
    if (event.key === "Enter") {
        searchFood();
    }
}

/* =========================================================
   3. DEFAULT MEALS DATA (ENGLISH LABELS)
   ========================================================= */
function loadDefaultMeals(container) {
    const defaultMeals = [
        {
            id: "m1",
            name: "Complete Green Salad Plate",
            category: "Salads",
            image: "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=600&q=80",
            ingredients: ["Cucumber", "Tomatoes", "Lettuce", "Olive Oil", "Lemon"],
            carbs: "8g",
            sugar: "3g",
            protein: "2g",
            fat: "5g",
            calories: "85 kcal"
        },
        {
            id: "m2",
            name: "Avocado Lemon Smoothie with Chia Seeds",
            category: "Beverages",
            image: "https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=600&q=80",
            ingredients: ["Avocado", "Water", "Lemon Juice", "Chia Seeds"],
            carbs: "6g",
            sugar: "1g",
            protein: "2g",
            fat: "14g",
            calories: "160 kcal"
        },
        {
            id: "m3",
            name: "Grilled Chicken Breast with Brown Rice & Cucumber Salad",
            category: "Main Dishes",
            image: "https://images.unsplash.com/photo-1532550907401-a500c9a57435?auto=format&fit=crop&w=600&q=80",
            ingredients: ["Chicken Breast", "Brown Rice", "Olive Oil", "Cucumber", "Yogurt"],
            carbs: "22g",
            sugar: "1g",
            protein: "32g",
            fat: "6g",
            calories: "280 kcal"
        },
        {
            id: "m4",
            name: "Greek Yogurt with Natural Honey & Cinnamon",
            category: "Desserts",
            image: "https://images.unsplash.com/photo-1488477181946-6428a0291777?auto=format&fit=crop&w=600&q=80",
            ingredients: ["Greek Yogurt", "Natural Honey", "Cinnamon", "Nuts"],
            carbs: "12g",
            sugar: "8g",
            protein: "15g",
            fat: "4g",
            calories: "150 kcal"
        }
    ];

    renderFoodCards(defaultMeals, container);
}

/* =========================================================
   4. API FETCH FUNCTION (CONNECTS TO FLASK BACKEND)
   ========================================================= */
async function fetchFoodData(query, category, container) {
    container.innerHTML = `<div class="food-loading">Searching for diabetic-friendly options...</div>`;

    try {
        const response = await fetch(`/api/foods?q=${encodeURIComponent(query)}&category=${encodeURIComponent(category)}`);
        const data = await response.json();

        if (!data.foods || data.foods.length === 0) {
            container.innerHTML = `<div class="food-empty">No foods found matching your criteria. Try another search.</div>`;
            return;
        }

        const formattedMeals = data.foods.map(item => parseBackendMeal(item));
        renderFoodCards(formattedMeals, container);

    } catch (error) {
        console.warn("Backend error, displaying default results.", error);
        loadDefaultMeals(container);
    }
}

// Convert Backend JSON format to standard UI Meal Object
function parseBackendMeal(item) {
    return {
        id: item.id,
        name: item.description,
        category: item.category || "General",
        image: item.image,
        ingredients: item.ingredients || [],
        carbs: item.carbs ? `${item.carbs}g` : "0g",
        sugar: item.sugar ? `${item.sugar}g` : "0g",
        protein: item.protein ? `${item.protein}g` : "0g",
        fat: item.fat ? `${item.fat}g` : "0g",
        calories: item.calories ? `${item.calories} kcal` : "0 kcal",
        backendAdvice: item.advice,
        backendSubstitutions: item.substitutions
    };
}

/* =========================================================
   5. SMART LOGIC: CUSTOMIZATION & ADVICE PER CATEGORY
   ========================================================= */

function isValueValid(val) {
    if (!val) return false;
    const num = parseFloat(val.toString().replace(/[^0-9.]/g, ''));
    return !isNaN(num) && num > 0;
}

function getSmartDiabeticAdvice(meal) {
    // If backend already calculated advice, return it directly formatted
    if (meal.backendAdvice) {
        return {
            advice: [meal.backendAdvice.tip],
            badgeClass: meal.backendAdvice.status || "info",
            badgeText: meal.backendAdvice.badge || "Diabetic Advice"
        };
    }

    const category = (meal.category || "").toLowerCase();
    const ingredients = (meal.ingredients || []).map(i => i.toLowerCase());
    const name = (meal.name || "").toLowerCase();

    let advice = [];
    let badgeClass = "success";
    let badgeText = "Diabetes Friendly";

    const hasCarbs = ingredients.some(i => i.includes("rice") || i.includes("bread") || i.includes("pasta") || i.includes("flour")) ||
        name.includes("rice") || name.includes("bread");
    const isFried = ingredients.some(i => i.includes("fried") || i.includes("oil") || i.includes("butter")) || name.includes("fried");

    if (category.includes("drink") || category.includes("beverage") || name.includes("juice") || name.includes("smoothie")) {
        advice.push("💡 <b>Beverage Tip:</b> Sweeten with a small teaspoon of natural honey or Stevia instead of refined sugar.");
        advice.push("🥗 <b>Healthy Fiber:</b> Add a teaspoon of chia seeds to slow down sugar absorption.");
    }
    else if (category.includes("dessert") || name.includes("sweet") || name.includes("cake")) {
        badgeClass = "warning";
        badgeText = "High Sugar Alert";
        advice.push("🍯 <b>Smart Swap:</b> Replace refined sugar with Stevia or Erythritol.");
        advice.push("🌰 <b>Pro Tip:</b> Add cinnamon or raw nuts to help prevent sudden blood glucose spikes.");
    }
    else {
        if (hasCarbs) {
            badgeClass = "info";
            badgeText = "Carb Portion Notice";
            advice.push("🍚 <b>Portion Control:</b> Limit rice/pasta portions to 4-5 tablespoons max or choose whole grain alternatives.");
            advice.push("🥒 <b>Balanced Combo:</b> Pair with a green salad or yogurt cucumber salad to stabilize blood sugar levels.");
        }

        if (isFried) {
            badgeClass = "warning";
            badgeText = "Modify Cooking Method";
            advice.push("🍳 <b>Cooking Method:</b> Switch deep frying to Air Frying or baking with a light olive oil spray.");
        }

        if (!hasCarbs && !isFried) {
            advice.push("✅ <b>Balanced Meal:</b> High in nutrients and protein with minimal impact on blood sugar.");
        }
    }

    return { advice, badgeClass, badgeText };
}

/* =========================================================
   6. RENDER CARDS TO DOM
   ========================================================= */
function renderFoodCards(meals, container) {
    container.innerHTML = "";

    meals.forEach(meal => {
        const cleanIngredients = (meal.ingredients || []).filter(ing => ing && ing.trim() !== "");

        let nutritionHTML = "";
        if (isValueValid(meal.carbs)) {
            nutritionHTML += `<div class="nutrient"><strong>${meal.carbs}</strong><span>Carbs</span></div>`;
        }
        if (isValueValid(meal.sugar)) {
            nutritionHTML += `<div class="nutrient"><strong>${meal.sugar}</strong><span>Sugar</span></div>`;
        }
        if (isValueValid(meal.protein)) {
            nutritionHTML += `<div class="nutrient"><strong>${meal.protein}</strong><span>Protein</span></div>`;
        }
        if (isValueValid(meal.fat)) {
            nutritionHTML += `<div class="nutrient"><strong>${meal.fat}</strong><span>Fat</span></div>`;
        }
        if (isValueValid(meal.calories)) {
            nutritionHTML += `<div class="nutrient"><strong>${meal.calories}</strong><span>Calories</span></div>`;
        }

        const { advice, badgeClass, badgeText } = getSmartDiabeticAdvice(meal);

        let substitutionsHTML = "";
        if (meal.backendSubstitutions && meal.backendSubstitutions.length > 0) {
            substitutionsHTML = meal.backendSubstitutions.map(sub =>
                `<div class="diabetes-tip">🔄 Replace <b>${sub.ingredient}</b> with <b>${sub.replacement}</b> (${sub.reason})</div>`
            ).join('');
        }

        const card = document.createElement("div");
        card.className = "food-card";

        card.innerHTML = `
            ${meal.image ? `<img src="${meal.image}" alt="${meal.name}" class="food-img" loading="lazy">` : `<div class="food-placeholder">🥗</div>`}
            
            <div class="food-card-content">
                <div style="display: flex; justify-content: space-between; align-items: center; gap: 5px;">
                    <span class="category-tag">${meal.category}</span>
                    <span class="diabetes-badge ${badgeClass}">${badgeText}</span>
                </div>

                <h3>${meal.name}</h3>

                ${cleanIngredients.length > 0 ? `
                    <div style="margin: 4px 0;">
                        <strong style="font-size:0.75rem; color:#62797d;">Ingredients:</strong>
                        <div style="display:flex; flex-wrap:wrap; gap:4px; margin-top:4px;">
                            ${cleanIngredients.map(ing => `<span class="ingredient-badge">${ing}</span>`).join('')}
                        </div>
                    </div>
                ` : ''}

                ${nutritionHTML ? `
                    <div class="nutrition-grid">
                        ${nutritionHTML}
                    </div>
                ` : ''}

                <div class="smart-swaps">
                    ${advice.map(item => `<div class="diabetes-tip">${item}</div>`).join('')}
                    ${substitutionsHTML}
                </div>
            </div>
        `;

        container.appendChild(card);
    });
}