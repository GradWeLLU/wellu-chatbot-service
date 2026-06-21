# fake_backend.py
# Real integration with Spring Boot microservices

import requests

USER_SERVICE_URL = "http://localhost:8081"
WORKOUT_NUTRITION_SERVICE_URL = "http://localhost:8082"


def _headers(token: str):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


# ─────────────────────────────────────────
# READ FUNCTIONS
# ─────────────────────────────────────────

def get_user_profile(token: str):
    try:
        response = requests.get(f"{USER_SERVICE_URL}/profile/me", headers=_headers(token))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"[BACKEND ERROR] get_user_profile failed: {e}")
        return {}


def get_workout_plan(token: str):
    """
    Fetches the user's workout plans and returns the first one,
    regardless of active/inactive status.
    """
    try:
        response = requests.get(
            f"{WORKOUT_NUTRITION_SERVICE_URL}/workouts/plans",
            headers=_headers(token)
        )
        response.raise_for_status()
        plans = response.json()

        if not plans:
            return {}

        return plans[0]

    except requests.exceptions.RequestException as e:
        print(f"[BACKEND ERROR] get_workout_plan failed: {e}")
        return {}


def get_nutrition_plan(token: str):
    """
    Fetches the user's nutrition plans and returns the first one,
    regardless of active/inactive status.
    """
    try:
        response = requests.get(
            f"{WORKOUT_NUTRITION_SERVICE_URL}/nutrition/plans",
            headers=_headers(token)
        )
        response.raise_for_status()
        plans = response.json()

        if not plans:
            return {}

        return plans[0]

    except requests.exceptions.RequestException as e:
        print(f"[BACKEND ERROR] get_nutrition_plan failed: {e}")
        return {}


def get_progress(token: str):
    try:
        response = requests.get(f"{USER_SERVICE_URL}/progress-entries", headers=_headers(token))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"[BACKEND ERROR] get_progress failed: {e}")
        return {}


# ─────────────────────────────────────────
# HELPER — find or create today's log
# ─────────────────────────────────────────

def _get_or_create_exercise_log(token: str, date: str):
    try:
        response = requests.get(f"{USER_SERVICE_URL}/exerciseLogs", headers=_headers(token))
        response.raise_for_status()
        logs = response.json()

        for log in logs:
            if log.get("workoutDate") == date:
                return log.get("id") or log.get("logId")

        create_response = requests.post(
            f"{USER_SERVICE_URL}/exerciseLogs",
            headers=_headers(token),
            json={"workoutDate": date}
        )
        create_response.raise_for_status()
        new_log = create_response.json()
        return new_log.get("id") or new_log.get("logId")

    except requests.exceptions.RequestException as e:
        print(f"[BACKEND ERROR] _get_or_create_exercise_log failed: {e}")
        return None


def _get_or_create_meal_log(token: str, date: str):
    try:
        response = requests.get(f"{USER_SERVICE_URL}/mealLogs", headers=_headers(token))
        response.raise_for_status()
        logs = response.json()

        for log in logs:
            if log.get("mealDate") == date:
                return log.get("id") 

        create_response = requests.post(
            f"{USER_SERVICE_URL}/mealLogs",
            headers=_headers(token),
            json={"mealDate": date}
        )
        create_response.raise_for_status()
        new_log = create_response.json()
        return new_log.get("id") 

    except requests.exceptions.RequestException as e:
        print(f"[BACKEND ERROR] _get_or_create_meal_log failed: {e}")
        return None


# ─────────────────────────────────────────
# WRITE FUNCTIONS — LOG
# ─────────────────────────────────────────

def log_meal(token: str, meal_data: dict, date: str):
    log_id = _get_or_create_meal_log(token, date)
    if log_id is None:
        return {"status": "error", "message": "Could not create or find meal log for today"}

    try:
        response = requests.post(
            f"{USER_SERVICE_URL}/mealLogs/addEntry/{log_id}",
            headers=_headers(token),
            json=meal_data
        )
        response.raise_for_status()
        return {"status": "success", "message": "Meal logged successfully"}
    except requests.exceptions.RequestException as e:
        print(f"[BACKEND ERROR] log_meal failed: {e}")
        return {"status": "error", "message": str(e)}


def log_workout(token: str, exercise_data: dict, date: str):
    log_id = _get_or_create_exercise_log(token, date)
    if log_id is None:
        return {"status": "error", "message": "Could not create or find workout log for today"}

    try:
        response = requests.post(
            f"{USER_SERVICE_URL}/exerciseLogs/addEntry/{log_id}",
            headers=_headers(token),
            json=exercise_data
        )
        response.raise_for_status()
        return {"status": "success", "message": "Workout logged successfully"}
    except requests.exceptions.RequestException as e:
        print(f"[BACKEND ERROR] log_workout failed: {e}")
        return {"status": "error", "message": str(e)}


# ─────────────────────────────────────────
# WRITE FUNCTIONS — MODIFY PLANS (still pending real endpoints)
# ─────────────────────────────────────────

def update_exercise_in_plan(token: str, **kwargs):
    print(f"[BACKEND] update_exercise_in_plan not yet integrated: {kwargs}")
    return {"status": "error", "message": "Exercise plan modification endpoint not yet confirmed"}


def update_meal_in_plan(token: str, **kwargs):
    print(f"[BACKEND] update_meal_in_plan not yet integrated: {kwargs}")
    return {"status": "error", "message": "Meal plan modification endpoint not yet confirmed"}