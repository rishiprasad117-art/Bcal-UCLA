import streamlit as st
import json
import os
from datetime import datetime
from meal_core.planner import plan_day as core_plan_day
import csv

# Page configuration
st.set_page_config(
    page_title="BCal — UCLA AI Nutrition Coach", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS for better UX
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #1f77b4, #ff7f0e);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 1rem;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .meal-section {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 2rem;
        border-radius: 1rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .food-item {
        background: rgba(255,255,255,0.9);
        color: #2c3e50;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .recommendation-card {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 1rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .success-message {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 1rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .warning-message {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 1rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 0.5rem;
        padding: 0.5rem 2rem;
        font-weight: bold;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 8px rgba(0,0,0,0.15);
    }
</style>
""", unsafe_allow_html=True)

def tdee_estimate(weight_lbs: float, height_in: float, age: int, sex: str, activity: str) -> int:
    """Compute TDEE using Mifflin-St Jeor. Returns rounded kcal."""
    weight_kg = weight_lbs * 0.453592
    height_cm = height_in * 2.54
    s = 5 if sex == "male" else -161
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + s
    af = {"sedentary": 1.20, "light": 1.375, "moderate": 1.55, "active": 1.725, "athlete": 1.90}.get(activity, 1.55)
    return round(bmr * af)


def smart_macro_targets(weight_lbs: float, target_calories: float, goal: str, user_preferences: dict):
    """Return (protein_g, carbs_g, fat_g) given a calorie target and preferences."""
    protein_per_lb = 1.1 if goal == "cut" else 0.9
    if user_preferences.get("high_protein"):
        protein_per_lb = max(protein_per_lb, 1.2)
    protein_g = round(weight_lbs * protein_per_lb)
    fat_g = max(round(weight_lbs * 0.35), round(target_calories * 0.20 / 9))
    carbs_g = max(0, round((target_calories - protein_g * 4 - fat_g * 9) / 4))
    return protein_g, carbs_g, fat_g


def main():
    # Enhanced header with animation
    st.markdown('<h1 class="main-header">🍽️ BCal - UCLA Smart Nutrition Planner</h1>', unsafe_allow_html=True)
    st.markdown("### Your intelligent meal planning assistant with personalized recommendations")
    
    # Initialize session state
    if 'user_profile' not in st.session_state:
        st.session_state.user_profile = {}
    if 'meal_plan' not in st.session_state:
        st.session_state.meal_plan = None
    if 'plan_summary' not in st.session_state:
        st.session_state.plan_summary = None
    if 'recommendations' not in st.session_state:
        st.session_state.recommendations = []

    # Enhanced sidebar with better organization
    with st.sidebar:
        st.header("🎯 Your Profile")
        
        # Basic Information Section
        with st.expander("📊 Basic Information", expanded=True):
            weight_lbs = st.number_input("Weight (lbs)", min_value=80, max_value=400, value=150, step=1, help="Your current weight")
            height_ft = st.number_input("Height (feet)", min_value=4, max_value=7, value=5, step=1)
            height_in = st.number_input("Height (inches)", min_value=0, max_value=11, value=8, step=1)
            age = st.number_input("Age", min_value=16, max_value=80, value=20, step=1)
            sex = st.selectbox("Sex", ["male", "female"])
        
        # Activity & Goals Section
        with st.expander("🏃 Activity & Goals", expanded=True):
            activity = st.selectbox(
                "Activity Level",
                ["sedentary", "light", "moderate", "active", "athlete"],
                index=2,
                help="sedentary: Little to no exercise\nlight: Light exercise 1-3 days/week\nmoderate: Moderate exercise 3-5 days/week\nactive: Heavy exercise 6-7 days/week\nathlete: Very heavy exercise, physical job"
            )
            
            goal = st.selectbox(
                "Primary Goal",
                ["maintain", "cut", "bulk"],
                help="maintain: Stay at current weight\ncut: Lose weight (calorie deficit)\nbulk: Gain weight (calorie surplus)"
            )
            
            # Smart calorie adjustment based on goal
            if goal == "cut":
                deficit = st.slider("Calorie Deficit (kcal/day)", 200, 800, 500, 50, help="Recommended: 300-500 for sustainable weight loss")
                calorie_adjustment = -deficit
            elif goal == "bulk":
                surplus = st.slider("Calorie Surplus (kcal/day)", 200, 800, 400, 50, help="Recommended: 300-500 for lean muscle gain")
                calorie_adjustment = surplus
            else:
                calorie_adjustment = 0
        
        # Enhanced Preferences Section
        with st.expander("🥗 Dietary Preferences", expanded=True):
            dietary_restrictions = st.multiselect(
                "Dietary Restrictions",
                ["vegan", "vegetarian", "pescatarian", "halal", "gluten-free", "dairy-free", "nut-free"],
                help="Select any dietary restrictions you follow"
            )
            
            # Smart preference options
            prefer_healthy = st.checkbox("Prioritize Healthy Options", value=True, help="Focus on nutrient-dense foods")
            high_protein = st.checkbox("High Protein Preference", value=False, help="Emphasize protein-rich foods")
            low_carb = st.checkbox("Low Carb Preference", value=False, help="Reduce carbohydrate intake")
            low_fat = st.checkbox("Low Fat Preference", value=False, help="Reduce fat intake")
            
            # Cooking method preferences
            cooking_preferences = st.multiselect(
                "Preferred Cooking Methods",
                ["grilled", "baked", "raw", "fried", "sautéed", "boiled"],
                help="Select cooking methods you prefer"
            )
            
            # Cuisine style preferences
            cuisine_preferences = st.multiselect(
                "Preferred Cuisine Styles",
                ["american", "italian", "asian", "mediterranean", "mexican"],
                help="Select cuisine styles you enjoy"
            )
        
        # Food Preferences Section
        with st.expander("🍎 Food Preferences", expanded=True):
            food_likes = st.text_area(
                "Foods you love (comma-separated)",
                placeholder="e.g., chicken, rice, broccoli, eggs, salmon",
                help="List foods you enjoy to prioritize in your meal plan"
            )
            food_dislikes = st.text_area(
                "Foods to avoid (comma-separated)",
                placeholder="e.g., mushrooms, spicy food, seafood, dairy",
                help="List foods you'd prefer to avoid"
            )
        
        # Dining Hall Preferences
        with st.expander("🏫 Dining Hall Preferences", expanded=True):
            dining_halls = st.multiselect(
                "Preferred Dining Halls",
                ["DeNeve", "BruinPlate", "Rendezvous", "BCafe"],
                default=["DeNeve", "BruinPlate"],
                help="Select which dining halls you'd like to eat at"
            )
        
        # Generate button with enhanced styling
        if st.button("🎯 Generate My Smart Meal Plan", type="primary", use_container_width=True):
            # Calculate TDEE
            total_height_in = height_ft * 12 + height_in
            tdee = tdee_estimate(weight_lbs, total_height_in, age, sex, activity)
            target_calories = tdee + calorie_adjustment
            
            # Calculate smart macro targets
            user_preferences = {
                "high_protein": high_protein,
                "low_carb": low_carb,
                "low_fat": low_fat,
                "prefer_healthy": prefer_healthy
            }
            protein_target, carbs_target, fat_target = smart_macro_targets(weight_lbs, target_calories, goal, user_preferences)
            
            # Store enhanced user profile with intelligent preferences
            st.session_state.user_profile = {
                'weight_lbs': weight_lbs,
                'height_ft': height_ft,
                'height_in': height_in,
                'age': age,
                'sex': sex,
                'activity': activity,
                'goal': goal,
                'calorie_adjustment': calorie_adjustment,
                'tdee': tdee,
                'target_calories': target_calories,
                'protein_target': protein_target,
                'carbs_target': carbs_target,
                'fat_target': fat_target,
                'dietary_restrictions': dietary_restrictions,
                'dining_halls': dining_halls,
                'food_likes': [f.strip() for f in food_likes.split(',') if f.strip()],
                'food_dislikes': [f.strip() for f in food_dislikes.split(',') if f.strip()],
                'prefer_healthy': prefer_healthy,
                'high_protein': high_protein,
                'low_carb': low_carb,
                'low_fat': low_fat,
                'cooking_preferences': cooking_preferences,
                'cuisine_preferences': cuisine_preferences
            }
            
            # Generate intelligent meal plan
            generate_smart_meal_plan()

    # Main content area
    if st.session_state.user_profile:
        display_user_profile()
        
        # Check for either new or old meal plan format
        if st.session_state.get('new_meal_plan') or st.session_state.get('meal_plan'):
            display_smart_meal_plan()
            
            if st.session_state.recommendations:
                display_smart_recommendations()
    else:
        display_enhanced_welcome_message()

def _infer_station(category: str) -> str:
    c = (category or "").lower()
    if any(k in c for k in ("salad","market","freshly","greens","fruit")): return "SaladBar"
    if any(k in c for k in ("deli","sandwich","wrap")): return "Deli"
    if any(k in c for k in ("grill","kitchen","stone","harvest")): return "Grill"
    if any(k in c for k in ("breakfast","waffle","egg")): return "Breakfast"
    return "Unknown"

def _load_menu_files() -> list:
    menu: list = []
    for path in ["de_neve_menu_composed.csv", "bruin_plate_menu_composed.csv"]:
        try:
            with open(path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get('Food Item') or row.get('name') or ''
                    station = _infer_station(row.get('Category',''))
                    calories = float(row.get('Calories (kcal)', row.get('calories', 0)) or 0)
                    protein = float(row.get('Protein (g)', row.get('protein', 0)) or 0)
                    carbs = float(row.get('Total Carbohydrate (g)', row.get('carbs', 0)) or 0)
                    fat = float(row.get('Total Fat (g)', row.get('fat', 0)) or 0)
                    menu.append({
                        'name': name,
                        'station': station,
                        'calories': calories,
                        'protein': protein,
                        'carbs': carbs,
                        'fat': fat,
                    })
        except FileNotFoundError:
            continue
    return menu

def generate_smart_meal_plan():
    """Generate intelligent meal plan with new efficient planner"""
    profile = st.session_state.user_profile
    
    # Load menu from composed CSVs
    inventory = _load_menu_files()
    
    # Convert profile to new planner format
    # Calculate total height in inches first
    total_height_in = profile.get("height_ft", 5) * 12 + profile.get("height_in", 8)
    
    act_map = {"active": "very"}
    planner_profile = {
        "sex": profile.get("sex", "male"),
        "age": profile.get("age", 25),
        "height_cm": total_height_in * 2.54,
        "weight_kg": profile.get("weight_lbs", 150) * 0.453592,
        "activity": act_map.get(profile.get("activity", "moderate"), profile.get("activity", "moderate")),
        "goal": profile.get("goal", "maintain"),
        "avoid": profile.get("food_dislikes", []),
        "prefer": profile.get("food_likes", [])
    }
    
    # Generate meal plan using core planner
    result = core_plan_day(inventory, planner_profile)
    
    # Store the new format
    st.session_state.new_meal_plan = result
    
    # Generate summary for compatibility
    meals = result['meals']
    st.session_state.plan_summary = {
        'calories': meals['breakfast'].get('calories',0) + meals['lunch'].get('calories',0) + meals['dinner'].get('calories',0),
        'protein': meals['breakfast'].get('protein',0) + meals['lunch'].get('protein',0) + meals['dinner'].get('protein',0),
        'carbs': meals['breakfast'].get('carbs',0) + meals['lunch'].get('carbs',0) + meals['dinner'].get('carbs',0),
        'fat': meals['breakfast'].get('fat',0) + meals['lunch'].get('fat',0) + meals['dinner'].get('fat',0),
        'potassium': 0.0,
        'iron': 0.0,
    }
    
    # Generate recommendations
    recommendations = []
    if result['notes']:
        recommendations.extend(result['notes'])
    st.session_state.recommendations = recommendations

def get_menu_last_updated():
    """Get the last modification time of menu CSV files"""
    csv_files = ["de_neve_menu_composed.csv", "bruin_plate_menu_composed.csv"]
    latest_time = None
    
    for csv_file in csv_files:
        if os.path.exists(csv_file):
            file_time = os.path.getmtime(csv_file)
            if latest_time is None or file_time > latest_time:
                latest_time = file_time
    
    if latest_time:
        return datetime.fromtimestamp(latest_time)
    return None

def display_user_profile():
    """Display enhanced user profile"""
    profile = st.session_state.user_profile
    
    st.markdown('<h2 class="sub-header">📊 Your Smart Nutrition Profile</h2>', unsafe_allow_html=True)
    
    # Show menu data freshness
    last_updated = get_menu_last_updated()
    if last_updated:
        hours_ago = (datetime.now() - last_updated).total_seconds() / 3600
        if hours_ago < 24:
            freshness = f"🟢 {hours_ago:.0f}h ago"
        elif hours_ago < 48:
            freshness = f"🟡 {hours_ago:.0f}h ago"
        else:
            freshness = f"🔴 {hours_ago/24:.1f} days ago"
        
        st.info(f"📅 Menu data last updated: {last_updated.strftime('%Y-%m-%d %H:%M')} ({freshness})")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("TDEE", f"{profile['tdee']:,} kcal")
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Target Calories", f"{profile['target_calories']:,} kcal")
        st.markdown('</div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Protein Target", f"{profile['protein_target']}g")
        st.markdown('</div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Goal", profile['goal'].title())
        st.markdown('</div>', unsafe_allow_html=True)

def display_smart_meal_plan():
    """Display intelligent meal plan with enhanced UI"""
    # Use new meal plan if available, fallback to old format
    if 'new_meal_plan' in st.session_state:
        _display_new_meal_plan()
    else:
        _display_old_meal_plan()

def _display_new_meal_plan():
    """Display new efficient meal plan"""
    result = st.session_state.new_meal_plan
    summary = st.session_state.plan_summary
    profile = st.session_state.user_profile
    
    st.markdown('<h2 class="sub-header">🍽️ Your Intelligent Meal Plan</h2>', unsafe_allow_html=True)
    
    # Show target info
    t = result["targets"]
    st.markdown(f'**Daily Targets:** {t["calories"]:.0f} kcal, {t["protein_g"]:.1f}g protein, {t["fat_g"]:.1f}g fat, {t["carbs_g"]:.1f}g carbs')
    
    meals = result['meals']
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="meal-section">', unsafe_allow_html=True)
        meal = meals['breakfast']
        st.markdown(f"### 🌅 Breakfast ({meal.get('station','')})")
        st.markdown(f"**{meal.get('name','Breakfast')}**")
        st.markdown(f"📊 {meal.get('calories',0)} cal, {meal.get('protein',0):.1f}g protein")
        st.markdown("**Components:**")
        for component in meal.get('components', []):
            st.markdown(f"• {component.get('name','')}")
        st.markdown(f"💡 {meal.get('rationale','')}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="meal-section">', unsafe_allow_html=True)
        meal = meals['lunch']
        st.markdown(f"### ☀️ Lunch ({meal.get('station','')})")
        st.markdown(f"**{meal.get('name','Lunch')}**")
        st.markdown(f"📊 {meal.get('calories',0)} cal, {meal.get('protein',0):.1f}g protein")
        st.markdown("**Components:**")
        for component in meal.get('components', []):
            st.markdown(f"• {component.get('name','')}")
        st.markdown(f"💡 {meal.get('rationale','')}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="meal-section">', unsafe_allow_html=True)
        meal = meals['dinner']
        st.markdown(f"### 🌙 Dinner ({meal.get('station','')})")
        st.markdown(f"**{meal.get('name','Dinner')}**")
        st.markdown(f"📊 {meal.get('calories',0)} cal, {meal.get('protein',0):.1f}g protein")
        st.markdown("**Components:**")
        for component in meal.get('components', []):
            st.markdown(f"• {component.get('name','')}")
        st.markdown(f"💡 {meal.get('rationale','')}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Show nutrition summary
    st.markdown('<h2 class="sub-header">📈 Nutrition Summary</h2>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Calories", f"{summary['calories']:.0f}", f"{t['calories']:.0f} target")
    with col2:
        st.metric("Protein", f"{summary['protein']:.1f}g", f"{t['protein_g']:.1f}g target")
    with col3:
        st.metric("Fat", f"{summary['fat']:.1f}g", f"{t['fat_g']:.1f}g target")
    with col4:
        st.metric("Carbs", f"{summary['carbs']:.1f}g", f"{t['carbs_g']:.1f}g target")

def _display_old_meal_plan():
    """Display old meal plan format (fallback)"""
    meal_plan = st.session_state.get('meal_plan', {})
    summary = st.session_state.plan_summary
    profile = st.session_state.user_profile
    
    st.markdown('<h2 class="sub-header">🍽️ Your Intelligent Meal Plan</h2>', unsafe_allow_html=True)
    
    # Goal-specific messaging with enhanced styling
    if profile['goal'] == 'cut':
        st.markdown('<div class="success-message">💪 <strong>Smart Cutting Plan:</strong> This plan is intelligently designed to help you lose weight while keeping you satisfied and energized! Our algorithm prioritized protein and fiber to help you feel full longer.</div>', unsafe_allow_html=True)
    elif profile['goal'] == 'bulk':
        st.markdown('<div class="success-message">🔥 <strong>Smart Bulking Plan:</strong> This plan will fuel your gains with intelligent calorie distribution and protein timing! Our algorithm selected nutrient-dense foods to support muscle growth.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="success-message">⚖️ <strong>Smart Maintenance Plan:</strong> This balanced plan will help you maintain your current weight while meeting all your nutritional needs! Our algorithm optimized for long-term sustainability.</div>', unsafe_allow_html=True)
    
    # Show intelligent customizations with enhanced reasoning
    customizations = []
    if profile['dietary_restrictions']:
        customizations.append(f"{', '.join(profile['dietary_restrictions'])} friendly")
    if profile['food_likes']:
        customizations.append(f"featuring your favorites: {', '.join(profile['food_likes'][:2])}")
    if profile['food_dislikes']:
        customizations.append(f"avoiding {', '.join(profile['food_dislikes'][:2])}")
    if profile['prefer_healthy']:
        customizations.append("prioritizing healthy options")
    if profile['cooking_preferences']:
        customizations.append(f"preferring {', '.join(profile['cooking_preferences'][:2])} cooking")
    if profile['cuisine_preferences']:
        customizations.append(f"favoring {', '.join(profile['cuisine_preferences'][:2])} cuisine")
    
    if customizations:
        st.markdown(f'<div class="recommendation-card">✨ <strong>Intelligently Customized:</strong> {", ".join(customizations)}</div>', unsafe_allow_html=True)
    
    # Display meals with enhanced styling
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="meal-section">', unsafe_allow_html=True)
        # Show dining hall for breakfast
        breakfast_dining_hall = meal_plan['Breakfast'][0].dining_hall if meal_plan['Breakfast'] else "Any"
        st.markdown(f"### 🌅 Breakfast ({breakfast_dining_hall})")
        if meal_plan['Breakfast']:
            for food in meal_plan['Breakfast']:
                # Show intelligent food information
                food_info = f"• <strong>{food.name}</strong><br>"
                food_info += f"📊 {food.calories} cal, {food.protein}g protein<br>"
                food_info += f"🏥 Health Score: {food.health_score:.1f}/1.0<br>"
                food_info += f"🍳 {food.cooking_method.title()} • {food.cuisine_style.title()} • {food.food_type.title()}<br>"
                if food.ingredients:
                    food_info += f"🥘 Contains: {', '.join(food.ingredients[:3])}"
                st.markdown(f'<div class="food-item">{food_info}</div>', unsafe_allow_html=True)
        else:
            st.markdown("No breakfast items found")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="meal-section">', unsafe_allow_html=True)
        # Show dining hall for lunch
        lunch_dining_hall = meal_plan['Lunch'][0].dining_hall if meal_plan['Lunch'] else "Any"
        st.markdown(f"### ☀️ Lunch ({lunch_dining_hall})")
        if meal_plan['Lunch']:
            for food in meal_plan['Lunch']:
                # Show intelligent food information
                food_info = f"• <strong>{food.name}</strong><br>"
                food_info += f"📊 {food.calories} cal, {food.protein}g protein<br>"
                food_info += f"🏥 Health Score: {food.health_score:.1f}/1.0<br>"
                food_info += f"🍳 {food.cooking_method.title()} • {food.cuisine_style.title()} • {food.food_type.title()}<br>"
                if food.ingredients:
                    food_info += f"🥘 Contains: {', '.join(food.ingredients[:3])}"
                st.markdown(f'<div class="food-item">{food_info}</div>', unsafe_allow_html=True)
        else:
            st.markdown("No lunch items found")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="meal-section">', unsafe_allow_html=True)
        # Show dining hall for dinner
        dinner_dining_hall = meal_plan['Dinner'][0].dining_hall if meal_plan['Dinner'] else "Any"
        st.markdown(f"### 🌙 Dinner ({dinner_dining_hall})")
        if meal_plan['Dinner']:
            for food in meal_plan['Dinner']:
                # Show intelligent food information
                food_info = f"• <strong>{food.name}</strong><br>"
                food_info += f"📊 {food.calories} cal, {food.protein}g protein<br>"
                food_info += f"🏥 Health Score: {food.health_score:.1f}/1.0<br>"
                food_info += f"🍳 {food.cooking_method.title()} • {food.cuisine_style.title()} • {food.food_type.title()}<br>"
                if food.ingredients:
                    food_info += f"🥘 Contains: {', '.join(food.ingredients[:3])}"
                st.markdown(f'<div class="food-item">{food_info}</div>', unsafe_allow_html=True)
        else:
            st.markdown("No dinner items found")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Enhanced nutrition summary
    st.markdown('<h3 class="sub-header">📈 Smart Nutrition Analysis</h3>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        cal_status = "✅" if abs(summary['calories'] - profile['target_calories']) <= profile['target_calories'] * 0.1 else "⚠️"
        st.metric("Calories", f"{int(summary['calories'])} {cal_status}", f"{profile['target_calories']} target")
    
    with col2:
        prot_status = "✅" if summary['protein'] >= profile['protein_target'] else "⚠️"
        st.metric("Protein", f"{summary['protein']:.1f}g {prot_status}", f"{profile['protein_target']}g target")
    
    with col3:
        st.metric("Carbs", f"{summary['carbs']:.1f}g")
    
    with col4:
        st.metric("Fat", f"{summary['fat']:.1f}g")
    
    # Additional nutrients
    st.markdown("### 🧪 Micronutrient Analysis")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Potassium", f"{summary['potassium']:.1f}mg")
    with col2:
        st.metric("Iron", f"{summary['iron']:.1f}mg")

def display_smart_recommendations():
    """Display intelligent recommendations"""
    recommendations = st.session_state.recommendations
    
    if recommendations:
        st.markdown('<h3 class="sub-header">🧠 Smart Recommendations</h3>', unsafe_allow_html=True)
        
        for i, rec in enumerate(recommendations, 1):
            st.markdown(f'<div class="recommendation-card">{rec}</div>', unsafe_allow_html=True)

def display_enhanced_welcome_message():
    """Display enhanced welcome message"""
    st.markdown("""
    ## Welcome to BCal! 🎉
    
    **BCal** is your intelligent nutrition planning assistant for UCLA dining halls. 
    We use advanced algorithms to create personalized meal plans that fit your goals, preferences, and lifestyle.
    
    ### 🧠 How Our Intelligence Works:
    1. **Smart Analysis** - We analyze your profile to understand your unique needs
    2. **Intelligent Filtering** - Our algorithm considers your preferences, restrictions, and goals
    3. **Realistic Recommendations** - We provide actionable advice based on your plan
    4. **Continuous Learning** - The system gets smarter with each interaction
    
    ### 🎯 What Makes Us Different:
    - ✅ **Intelligent meal selection** based on nutrition density and your preferences
    - 📊 **Smart macro distribution** optimized for your goals
    - 🏥 **Health scoring** to prioritize nutrient-dense foods
    - 🎨 **Personalized recommendations** that actually make sense
    - 🧠 **Context-aware suggestions** for your specific situation
    
    ### 🚀 Ready to Get Started?
    Use the sidebar to input your information and generate your intelligent meal plan!
    
    **Pro Tip:** The more specific you are about your preferences, the better our algorithm can serve you! 🎯
    """)

if __name__ == "__main__":
    main()