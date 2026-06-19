import os
import json
import re

from google import genai
from dotenv import load_dotenv
from utils.api_status import record as record_api_error

load_dotenv()

_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def _fallback_activities(weather_data, likes=None):
    summary = weather_data.get("forecast_summary", {})
    risk_flags = set(summary.get("risk_flags", []))
    risky_weather = bool(risk_flags)
    preference_note = ""

    if likes:
        preference_note = f" Matches stated interest in {', '.join(likes[:2])}."

    if risky_weather:
        return [
            {
                "name": "Museum visit",
                "type": "indoor",
                "score": 9,
                "reason": "Indoor option suitable for the detected weather risks." + preference_note,
            },
            {
                "name": "Local food experience",
                "type": "indoor",
                "score": 8,
                "reason": "Low-risk plan that works well during poor outdoor conditions." + preference_note,
            },
            {
                "name": "Cafe work session",
                "type": "relax",
                "score": 8,
                "reason": "Relaxed activity with minimal exposure to weather risk.",
            },
            {
                "name": "Indoor shopping district",
                "type": "indoor",
                "score": 7,
                "reason": "Weather-protected option with flexible timing.",
            },
            {
                "name": "Gallery tour",
                "type": "indoor",
                "score": 7,
                "reason": "Indoor cultural activity that avoids wind and precipitation.",
            },
            {
                "name": "Restaurant reservation",
                "type": "relax",
                "score": 7,
                "reason": "Comfortable evening option when outdoor plans are less reliable.",
            },
        ]

    return [
        {
            "name": "City walking route",
            "type": "outdoor",
            "score": 9,
            "reason": "Outdoor weather looks suitable for a light city route." + preference_note,
        },
        {
            "name": "Park visit",
            "type": "outdoor",
            "score": 8,
            "reason": "Comfortable conditions support outdoor time.",
        },
        {
            "name": "Outdoor cafe",
            "type": "relax",
            "score": 8,
            "reason": "Balanced option that uses good weather without requiring heavy activity.",
        },
        {
            "name": "Photo walk",
            "type": "outdoor",
            "score": 8,
            "reason": "Suitable for mild weather and flexible timing.",
        },
        {
            "name": "Local market visit",
            "type": "outdoor",
            "score": 7,
            "reason": "Good fit when precipitation and wind risks are low.",
        },
        {
            "name": "Museum backup plan",
            "type": "indoor",
            "score": 7,
            "reason": "Keeps the plan resilient if weather changes.",
        },
    ]


def _preference_tokens(values):
    tokens = []

    for value in values or []:
        tokens.extend(
            token.lower()
            for token in re.split(r"[\s,;]+", str(value))
            if len(token.strip()) >= 3
        )

    return set(tokens)


def analyze_weather_conditions(weather_data, likes=None, dislikes=None):
    summary = weather_data.get("forecast_summary", {})
    condition = str(weather_data.get("weather", "")).lower()
    risk_flags = list(summary.get("risk_flags", []))

    temperature = weather_data.get("temperature", 0)
    wind_speed = weather_data.get("wind_speed", 0)
    precipitation_probability = weather_data.get("precipitation_probability", 0)

    if precipitation_probability >= 60 and "precipitation risk" not in risk_flags:
        risk_flags.append("precipitation risk")
    if wind_speed >= 10 and "high wind" not in risk_flags:
        risk_flags.append("high wind")
    if temperature >= 35 and "high temperature" not in risk_flags:
        risk_flags.append("high temperature")
    if temperature <= 0 and "low temperature" not in risk_flags:
        risk_flags.append("low temperature")
    if ("storm" in condition or "thunder" in condition) and "storm risk" not in risk_flags:
        risk_flags.append("storm risk")

    outdoor_risk = any(
        flag in risk_flags
        for flag in [
            "precipitation risk",
            "high wind",
            "high temperature",
            "low temperature",
            "storm risk",
        ]
    )

    if outdoor_risk:
        priority = "indoor and low-risk activities"
    elif 18 <= temperature <= 28 and precipitation_probability < 40 and wind_speed < 8:
        priority = "outdoor activities"
    else:
        priority = "balanced indoor and outdoor activities"

    result = {
        "priority": priority,
        "risk_flags": risk_flags,
        "likes": likes or [],
        "dislikes": dislikes or [],
    }

    daily_forecast = weather_data.get("daily_forecast", [])
    best_day = weather_data.get("best_day")
    if best_day and len(daily_forecast) > 1:
        result["best_outdoor_day"] = best_day.get("day_name", "")
        result["best_day_avg_temp"] = best_day.get("avg_temp")
        result["best_day_rain_chance"] = best_day.get("max_precipitation_probability")

    return result


def _activity_conflicts(activity, dislikes):
    disliked_terms = _preference_tokens(dislikes)
    searchable = f"{activity.get('name', '')} {activity.get('reason', '')}".lower()
    return sorted(term for term in disliked_terms if term in searchable)


def _normalize_activity(activity):
    activity_type = str(activity.get("type", "Relax")).strip().lower()
    if activity_type not in {"indoor", "outdoor", "relax"}:
        activity_type = "relax"

    try:
        score = int(float(activity.get("score", 5)))
    except (TypeError, ValueError):
        score = 5

    score = max(1, min(score, 10))

    return {
        "name": str(activity.get("name", "")).strip(),
        "type": activity_type,
        "score": score,
        "reason": str(activity.get("reason", "")).strip(),
    }


def parse_activities(raw_response):
    if isinstance(raw_response, dict):
        return raw_response.get("activities", [])

    if isinstance(raw_response, list):
        return raw_response

    if not raw_response:
        return []

    try:
        payload = json.loads(raw_response)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}|\[.*\]", raw_response, re.DOTALL)
        if not match:
            return []
        payload = json.loads(match.group())

    if isinstance(payload, dict):
        return payload.get("activities", [])

    if isinstance(payload, list):
        return payload

    return []


def generate_activities(weather_data, city, likes=None, dislikes=None, decision_context=None, feedback=None):
    decision_context = decision_context or analyze_weather_conditions(weather_data, likes, dislikes)
    feedback_text = "\n".join(feedback or [])

    best_day = decision_context.get("best_outdoor_day", "")
    best_day_note = ""
    if best_day:
        temp = decision_context.get("best_day_avg_temp", "")
        rain = decision_context.get("best_day_rain_chance", "")
        best_day_note = (
            f"\nBest day for outdoor activities in the forecast window: {best_day} "
            f"(avg {temp}Â°C, {rain}% rain chance). "
            "Mention this day explicitly in the reason field for outdoor activity suggestions."
        )

    prompt = f"""
You are a strict JSON generator for a travel activity system.

City: {city}
Weather: {weather_data}
User likes: {likes or []}
User dislikes: {dislikes or []}
Agent weather decision: {decision_context}{best_day_note}
Revision feedback from previous loop: {feedback_text}

TASK:
Generate 10 activities suitable for the weather and user preferences.
Avoid disliked activities.
If risk flags exist, avoid unsafe outdoor suggestions.

CRITICAL RULES:
- Return ONLY valid JSON as an object
- Do not use emojis
- No explanations
- No markdown
- No text before or after JSON
- No ``` symbols

OUTPUT FORMAT (must follow exactly):

{{
  "activities": [
    {{
      "name": "Activity name",
      "type": "indoor | outdoor | relax",
      "score": 1-10,
      "reason": "Short weather and preference reason"
    }}
  ]
}}
"""

    response = _client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=genai.types.GenerateContentConfig(temperature=0.2),
    )
    return response.text


def filter_activities(activities, weather_data=None, dislikes=None):
    weather_data = weather_data or {}
    dislikes = dislikes or []
    decision_context = analyze_weather_conditions(weather_data, dislikes=dislikes)
    risk_flags = set(decision_context["risk_flags"])
    risky_outdoor = bool(
        risk_flags.intersection(
            {
                "precipitation risk",
                "high wind",
                "high temperature",
                "low temperature",
                "storm risk",
            }
        )
    )

    filtered = []
    removed = []

    for a in activities:
        activity = _normalize_activity(a)

        if not activity["name"]:
            removed.append("Removed activity without a name.")
            continue

        if activity["score"] < 4:
            removed.append(f"Removed low-score activity: {activity['name']}.")
            continue

        name = activity["name"].lower()
        if "unknown" in name or "random" in name:
            removed.append(f"Removed low-quality activity: {activity['name']}.")
            continue

        conflicts = _activity_conflicts(activity, dislikes)
        if conflicts:
            removed.append(
                f"Removed {activity['name']} because it conflicts with dislikes: {', '.join(conflicts)}."
            )
            continue

        if risky_outdoor and activity["type"] == "outdoor":
            activity["score"] = min(activity["score"], 6)
            if not activity["reason"]:
                activity["reason"] = "Outdoor score reduced because of weather risk."

        filtered.append(activity)

    filtered.sort(key=lambda item: item["score"], reverse=True)
    return filtered, removed


def recommend_activities(
    weather_data,
    city,
    likes=None,
    dislikes=None,
    max_iterations=2,
    evaluator_feedback=None,
):
    decision_context = analyze_weather_conditions(weather_data, likes, dislikes)
    decision_steps = [
        f"Checked current weather and forecast. Priority: {decision_context['priority']}.",
    ]

    if decision_context["risk_flags"]:
        decision_steps.append(
            "Detected weather risks: " + ", ".join(decision_context["risk_flags"]) + "."
        )
    else:
        decision_steps.append("No major weather risks detected in the available forecast.")

    feedback = list(evaluator_feedback or [])
    best_activities = []

    if feedback:
        decision_steps.append(
            "Quality feedback was used to revise the recommendation set: "
            + " ".join(feedback[:3])
        )

    for iteration in range(1, max_iterations + 1):
        try:
            raw = generate_activities(
                weather_data,
                city,
                likes=likes,
                dislikes=dislikes,
                decision_context=decision_context,
                feedback=feedback,
            )
        except Exception as e:
            record_api_error("Activity generation", e)
            raw = {"activities": _fallback_activities(weather_data, likes=likes)}
            decision_steps.append("Generation fallback used because the LLM activity call failed.")

        parsed = parse_activities(raw)
        filtered, removed = filter_activities(parsed, weather_data=weather_data, dislikes=dislikes)

        decision_steps.append(
            f"Iteration {iteration}: generated {len(parsed)} activities and kept {len(filtered)} after safety and preference checks."
        )

        if removed:
            decision_steps.append("Revision feedback: " + " ".join(removed[:3]))

        best_activities = filtered

        if len(filtered) >= 6:
            decision_steps.append("Decision loop stopped because enough suitable activities were found.")
            break

        feedback = removed + ["Generate more activities that fit weather risks and user preferences."]
        decision_steps.append("Decision loop requested another generation pass.")

    return {
        "activities": best_activities[:6],
        "decision_context": decision_context,
        "decision_steps": decision_steps,
    }
