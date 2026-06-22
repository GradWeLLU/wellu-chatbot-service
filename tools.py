# tools.py
from langchain_core.tools import tool
from datetime import date as date_module
from fake_backend import (
    get_progress,
    get_workout_plan,
    get_nutrition_plan,
    get_today_meals,
    get_today_workouts,
    search_food_nutrition,
    log_meal as backend_log_meal,
    log_workout as backend_log_workout,
    update_exercise_in_plan as backend_update_exercise,
    update_meal_in_plan as backend_update_meal
)


def build_tools_for_token(token: str):
    """
    Creates a fresh set of tools with the token already 
    baked in. The AI never sees or handles the token directly,
    it only deals with the actual meaningful parameters
    like exercise_name, calories, etc.
    """

    # ─────────────────────────────────────────
    # READ TOOLS
    # ─────────────────────────────────────────

    @tool
    def fetch_progress() -> str:
        """
        Use this when the user asks about their progress,
        stats, calories burnt, weight history, or how 
        they are doing in general. ALWAYS call this fresh,
        never answer from conversation memory.
        """
        progress_entries = get_progress(token)

        if not progress_entries:
            return "You don't have any progress entries logged yet."

        result = "📊 Progress history:\n"
        for entry in progress_entries:
            result += (
                f"- {entry.get('recordedAt', 'Unknown date')}: "
                f"Weight: {entry.get('weight', 'N/A')}kg, "
                f"Calories burnt: {entry.get('caloriesBurnt', 'N/A')}, "
                f"Workout completed: {entry.get('workoutCompleted', 'N/A')}"
            )
            notes = entry.get('notes')
            if notes:
                result += f", Notes: {notes}"
            result += "\n"

        return result

    @tool
    def fetch_workout_plan() -> str:
        """
        Use this when the user asks about their current
        workout plan, what exercises to do, or their
        training schedule. ALWAYS call this fresh, never 
        answer from conversation memory or logged exercises.
        """
        plan = get_workout_plan(token)

        if not plan or "days" not in plan:
            return "You don't have an active workout plan right now. Would you like to discuss creating one?"

        result = f"💪 Workout Plan ({plan.get('weekly_split', 'N/A')}) - Difficulty: {plan.get('difficulty', 'N/A')}\n"

        for day in plan["days"]:
            result += f"\n📅 {day['day']} - {day['focus']}:\n"
            for exercise in day["exercises"]:
                result += (
                    f"  🏋️ {exercise['name']}: "
                    f"{exercise['sets']} sets x {exercise['reps']} reps "
                    f"(rest: {exercise.get('rest_time', 'N/A')}s)\n"
                )

        return result

    @tool
    def fetch_nutrition_plan() -> str:
        """
        Use this when the user asks about their meal plan,
        what to eat, or their nutrition targets. ALWAYS call 
        this fresh, never answer from conversation memory 
        or logged meals.
        """
        plan = get_nutrition_plan(token)

        if not plan or "days" not in plan:
            return "You don't have an active nutrition plan right now. Would you like to discuss creating one?"

        result = f"🍽️ Nutrition Plan - Goal: {plan.get('goal', 'N/A')} | Daily Calories: {plan.get('daily_calories', 'N/A')} kcal\n"

        for day in plan["days"]:
            result += f"\n📅 {day['day']}:\n"
            for meal in day["meals"]:
                result += (
                    f"  🍴 {meal['name']}: {meal['calories']} kcal, "
                    f"{meal['protein']}g protein, {meal['carbs']}g carbs, {meal['fats']}g fats\n"
                    f"    Ingredients: {', '.join(meal.get('ingredients', []))}\n"
                )

        return result

    @tool
    def fetch_todays_meals() -> str:
        """
        Use this when the user asks what they've eaten today,
        or wants to review today's logged meals. ALWAYS call 
        this fresh, never answer from conversation memory.
        """
        entries = get_today_meals(token)

        if not entries:
            return "You haven't logged any meals today yet."

        result = "🍽️ Today's logged meals:\n"
        for entry in entries:
            result += (
                f"- {entry.get('mealType', 'N/A')}: {entry.get('mealName', 'N/A')} "
                f"({entry.get('calories', 'N/A')} kcal, "
                f"{entry.get('protein', 'N/A')}g protein)\n"
            )
        return result

    @tool
    def fetch_todays_workouts() -> str:
        """
        Use this when the user asks what exercises they've 
        done today, or wants to review today's logged workout.
        ALWAYS call this fresh, never answer from conversation 
        memory.
        """
        entries = get_today_workouts(token)

        if not entries:
            return "You haven't logged any workouts today yet."

        result = "💪 Today's logged exercises:\n"
        for entry in entries:
            name = entry.get('exerciseName', 'N/A')
            if entry.get('type') == 'CARDIO':
                result += (
                    f"- 🏃 {name}: {entry.get('durationMinutes', 'N/A')} min, "
                    f"{entry.get('distanceKm', 'N/A')}km, "
                    f"{entry.get('burnedCalories', 'N/A')} kcal burned\n"
                )
            else:
                sets = entry.get('sets', [])
                sets_str = ", ".join(f"{s.get('reps')}x{s.get('weight')}kg" for s in sets)
                result += f"- 🏋️ {name}: {sets_str}\n"
        return result

    @tool
    def lookup_food_nutrition(food_name: str) -> str:
        """
        Use this BEFORE logging a meal, to look up accurate 
        nutritional data for a specific food item from a 
        real nutrition database (USDA FoodData Central).
        This gives more consistent, accurate calorie/macro 
        values than estimating alone.

        Best for common, simple foods (eggs, chicken, rice, 
        banana, milk, bread, etc). For complex Egyptian or 
        Middle Eastern dishes (koshary, molokhia, ta'meya, 
        ful, mahshi, fattah), this will likely find no match, 
        in that case fall back to your own nutritional 
        knowledge to estimate instead.

        Call this once per distinct simple food item before 
        logging, then adjust the returned per-100g values 
        based on the actual quantity/serving size the user 
        mentioned.
        """
        result = search_food_nutrition(food_name)

        if result is None:
            return f"No database match found for '{food_name}'. Estimate based on your own nutritional knowledge instead."

        return (
            f"Nutrition data for {result['name']} (per 100g, USDA database): "
            f"Calories: {result['calories']}, Protein: {result['protein']}g, "
            f"Carbs: {result['carbs']}g, Fats: {result['fats']}g. "
            f"Adjust these values proportionally based on the actual "
            f"serving size/quantity the user mentioned."
        )

    # ─────────────────────────────────────────
    # WRITE TOOLS — LOG MEAL
    # ─────────────────────────────────────────

    @tool
    def log_meal(
        meal_type: str,
        meal_name: str,
        food_items: list,
        calories: int,
        protein: float,
        carbs: float,
        fats: float,
        notes: str = ""
    ) -> str:
        """
        Use this when the user tells you they ate or drank 
        something, including Egyptian dishes like molokhia, 
        koshary, ful medames, ta'meya, mahshi, fattah, kebda, etc.

        Each time the user mentions a NEW food that hasn't 
        been discussed yet, call this as a separate entry. 
        If you're completing a pending question you asked 
        about something already mentioned, that's still ONE 
        call for that one item, not a new separate one.

        You MUST provide calories, protein, carbs, and fats 
        yourself, either from lookup_food_nutrition results 
        (adjusted for serving size) or your own nutritional 
        knowledge. NEVER ask the user for exact nutritional 
        values.

        meal_type must be one of: BREAKFAST, LUNCH, DINNER, SNACK
        food_items should be a list of individual food names, 
        e.g. ["Eggs", "Oats", "Banana"] or ["Koshary"]
        Logs against today's date automatically.
        """
        today = date_module.today().isoformat()

        meal_data = {
            "mealType": meal_type.upper(),
            "mealName": meal_name,
            "foodItems": food_items,
            "calories": calories,
            "protein": protein,
            "carbs": carbs,
            "fats": fats,
            "notes": notes
        }

        result = backend_log_meal(token, meal_data, today)

        if result["status"] == "success":
            return f"Logged {meal_name} ({calories} kcal, {protein}g protein) as {meal_type}. {result['message']}"
        else:
            return f"Could not log meal: {result['message']}"

    # ─────────────────────────────────────────
    # WRITE TOOLS — LOG WORKOUT
    # ─────────────────────────────────────────

    @tool
    def log_strength_exercise(
        exercise_name: str,
        sets: list
    ) -> str:
        """
        Use this when the user tells you they completed a 
        STRENGTH exercise like bench press, squats, deadlifts, etc.

        sets MUST be provided by the user, never guessed. 
        Must be a list of dictionaries, each containing 
        'reps' and 'weight'. 
        Example: [{"reps": 10, "weight": 60}, {"reps": 8, "weight": 65}]

        If sets, reps, or weight are missing from the user's 
        message, ASK them before calling this tool. Do not 
        invent these numbers.

        If the user only mentions one set, still wrap it in a list
        with one item. If weight is bodyweight, use 0.
        """
        today = date_module.today().isoformat()

        exercise_data = {
            "exerciseName": exercise_name,
            "type": "STRENGTH",
            "sets": sets
        }

        result = backend_log_workout(token, exercise_data, today)

        if result["status"] == "success":
            total_sets = len(sets)
            return f"Logged {exercise_name}: {total_sets} sets. {result['message']}"
        else:
            return f"Could not log workout: {result['message']}"

    @tool
    def log_cardio_exercise(
        exercise_name: str,
        duration_minutes: int,
        distance_km: float = 0,
        burned_calories: int = 0
    ) -> str:
        """
        Use this when the user tells you they completed a 
        CARDIO exercise like running, cycling, swimming, etc.

        duration_minutes MUST be provided by the user, never 
        guessed. Ask if missing.

        If distance or calories burned are not mentioned, 
        you may estimate them reasonably based on duration 
        and exercise type.
        """
        today = date_module.today().isoformat()

        exercise_data = {
            "exerciseName": exercise_name,
            "type": "CARDIO",
            "durationMinutes": duration_minutes,
            "distanceKm": distance_km,
            "burnedCalories": burned_calories
        }

        result = backend_log_workout(token, exercise_data, today)

        if result["status"] == "success":
            return f"Logged {exercise_name}: {duration_minutes} minutes. {result['message']}"
        else:
            return f"Could not log workout: {result['message']}"

    # ─────────────────────────────────────────
    # WRITE TOOLS — MODIFY PLANS (pending backend confirmation)
    # ─────────────────────────────────────────

    @tool
    def modify_workout_exercise(**kwargs) -> str:
        """
        Use this ONLY when the user has explicitly confirmed
        they want to replace a specific exercise in their plan.
        NOTE: This feature is pending backend endpoint confirmation.
        """
        result = backend_update_exercise(token, **kwargs)
        return result["message"]

    @tool
    def modify_meal_item(**kwargs) -> str:
        """
        Use this ONLY when the user has explicitly confirmed
        they want to replace a food item in their meal plan.
        NOTE: This feature is pending backend endpoint confirmation.
        """
        result = backend_update_meal(token, **kwargs)
        return result["message"]

    # ─────────────────────────────────────────
    # RETURN ALL TOOLS FOR THIS TOKEN
    # ─────────────────────────────────────────

    return [
        fetch_progress,
        fetch_workout_plan,
        fetch_nutrition_plan,
        fetch_todays_meals,
        fetch_todays_workouts,
        lookup_food_nutrition,
        log_meal,
        log_strength_exercise,
        log_cardio_exercise,
        modify_workout_exercise,
        modify_meal_item
    ]